<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { listarClientes } from '@/clientes'
import { listarSucursales } from '@/sucursales'
import { listarTecnicos } from '@/tecnicos'
import { crearOrdenTrabajo, relojesElegiblesOt, tecnicoSugerido } from '@/servicio_tecnico/services/servicioTecnicoApi'

const emit = defineEmits(['update:modelValue', 'guardado'])
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // Llegada desde "Atender cita" (007): cliente y cita ya resueltos.
  prefill: { type: Object, default: null },
})

function vacio() {
  return {
    numero_serie: '', cliente_id: props.prefill?.cliente_id ?? null, motivo: '', tipo_reparacion: '',
    sucursal_id: null, tecnico_id: null, override: '',
  }
}
const f = reactive(vacio())
const citaId = ref(props.prefill?.cita_id ?? null)

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      Object.assign(f, vacio())
      citaId.value = props.prefill?.cita_id ?? null
      tecnicoTocado.value = false
      sinTecnicoDisponible.value = false
      relojesOpciones.value = []
      ultimaSeleccionReloj = null
    }
  },
)
const guardando = ref(false)
const error = ref('')
const pideOverride = ref(false)
const clientes = ref([])
const sucursales = ref([])
const tecnicos = ref([])
const tecnicoTocado = ref(false)
const buscandoTecnico = ref(false)
const sinTecnicoDisponible = ref(false)

function etiquetaReloj(r) {
  const base = `${r.marca} ${r.referencia || ''}`.trim() + ` · ${r.numero_serie}`
  return r.cliente_nombre ? `${base} · ${r.cliente_nombre}` : `${base} · sin venta registrada`
}

// Búsqueda remota de la unidad (feedback del usuario, 2026-09-11: "el número de
// serie es texto libre, debería tener la información de todos los relojes
// vendidos" — con cientos de unidades, cargar una lista fija una sola vez las
// deja fuera más allá del corte; se busca en el servidor en cada tecleo, así
// cubre de verdad TODAS, no solo las primeras N).
const relojesOpciones = ref([])
const buscandoReloj = ref(false)
let ultimaSeleccionReloj = null // sobrevive a búsquedas posteriores para que el ComboBox no pierda la etiqueta
let tBuscarReloj
function buscarReloj(q) {
  clearTimeout(tBuscarReloj)
  buscandoReloj.value = true
  tBuscarReloj = setTimeout(async () => {
    try {
      const r = await relojesElegiblesOt(q || undefined)
      const opciones = r.map((x) => ({ ...x, _label: etiquetaReloj(x) }))
      if (ultimaSeleccionReloj && !opciones.some((x) => x.numero_serie === ultimaSeleccionReloj.numero_serie)) {
        opciones.unshift(ultimaSeleccionReloj)
      }
      relojesOpciones.value = opciones
    } catch {
      relojesOpciones.value = ultimaSeleccionReloj ? [ultimaSeleccionReloj] : []
    } finally {
      buscandoReloj.value = false
    }
  }, 250)
}

onMounted(async () => {
  ;[clientes.value, sucursales.value, tecnicos.value] = await Promise.all([
    listarClientes({ page: 1, size: 100 }).then((r) => r.items.map((c) => ({ ...c, _label: `${c.nombre} · ${c.numero_afiliado}` }))).catch(() => []),
    listarSucursales().then((r) => r.items).catch(() => []),
    listarTecnicos({ page: 1, size: 100 }).then((r) => r.items.filter((t) => t.estado === 'activo')).catch(() => []),
  ])
})

// Elegir una unidad real (nunca escribir la serie a mano, Ppio XI) autorrellena el
// cliente cuando la unidad tiene una venta confirmada — feedback del usuario
// (2026-09-11): "debería autollenarse el cliente dueño del reloj comprado".
function onElegirReloj(serie) {
  f.numero_serie = serie || ''
  const r = relojesOpciones.value.find((x) => x.numero_serie === serie) || null
  ultimaSeleccionReloj = r
  if (r?.cliente_id) f.cliente_id = r.cliente_id
}
const clienteAutoDetectado = computed(() => {
  const r = relojesOpciones.value.find((x) => x.numero_serie === f.numero_serie)
  return !!(r?.cliente_id && r.cliente_id === f.cliente_id)
})

watch(
  () => f.numero_serie,
  () => { pideOverride.value = false; f.override = '' },
)

// Sugerencia automática de técnico (marca/calibre + sucursal) al escribir la
// serie — el vendedor puede confirmarla o cambiarla, pero nunca queda oculta:
// una OT no debe quedar sin técnico sin que quien la abre lo sepa.
let tTecnico
watch([() => f.numero_serie, () => f.sucursal_id], () => {
  clearTimeout(tTecnico)
  if (tecnicoTocado.value) return
  const serie = f.numero_serie.trim()
  if (!serie) { f.tecnico_id = null; sinTecnicoDisponible.value = false; return }
  tTecnico = setTimeout(async () => {
    buscandoTecnico.value = true
    try {
      const r = await tecnicoSugerido(serie, f.sucursal_id || undefined)
      if (!tecnicoTocado.value) {
        f.tecnico_id = r.tecnico_id
        sinTecnicoDisponible.value = !r.tecnico_id
      }
    } catch {
      // serie aún no válida u otro error de lectura: no bloquea la escritura
    } finally {
      buscandoTecnico.value = false
    }
  }, 400)
})

async function guardar() {
  error.value = ''
  if (!f.numero_serie.trim()) return (error.value = 'Indica el número de serie de la unidad.')
  if (!f.cliente_id) return (error.value = 'Selecciona el cliente.')
  if (f.motivo.trim().length < 3) return (error.value = 'Describe el motivo del servicio.')
  if (f.tipo_reparacion.trim().length < 2) return (error.value = 'Indica el tipo de reparación.')
  guardando.value = true
  try {
    const { id } = await crearOrdenTrabajo({
      numero_serie: f.numero_serie.trim(),
      cliente_id: f.cliente_id,
      cita_id: citaId.value || undefined,
      motivo: f.motivo.trim(),
      tipo_reparacion: f.tipo_reparacion.trim(),
      sucursal_id: f.sucursal_id || undefined,
      tecnico_id: f.tecnico_id || undefined,
      override_adquisicion_motivo: f.override.trim() || undefined,
    })
    toast.success('Orden de trabajo abierta')
    Object.assign(f, vacio())
    emit('update:modelValue', false)
    emit('guardado', id)
  } catch (e) {
    if (e.status === 422 && /adquiri|tienda/i.test(e.message)) {
      pideOverride.value = true
      error.value = 'No consta que la unidad se haya comprado en la tienda. Escribe el motivo de la autorización para continuar.'
    } else {
      error.value = e.message
    }
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    titulo="Nueva orden de trabajo"
    subtitulo="Elige la unidad del inventario — si tiene una venta registrada, el cliente se autocompleta. La fecha estimada de entrega se registra recién tras el diagnóstico."
    :guardando="guardando"
    ancho="max-w-2xl"
    :sucio="!!f.numero_serie || !!f.motivo"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <p v-if="citaId" class="sm:col-span-2 flex items-center gap-2 rounded-lg border border-hairline bg-surface-sunk px-3 py-2 text-xs text-ink-2">
      <CrIcon name="check" :size="13" /> Orden iniciada desde la cita atendida — quedará vinculada a ella.
    </p>
    <FormField label="Unidad" required helper="Solo unidades reales del inventario — busca por serie, marca o referencia.">
      <ComboBox
        :model-value="f.numero_serie || null"
        :opciones="relojesOpciones" opcion-label="_label" opcion-value="numero_serie"
        placeholder="Buscar por serie, marca o referencia…"
        remoto :buscando="buscandoReloj"
        @update:model-value="onElegirReloj"
        @buscar="buscarReloj"
      />
    </FormField>
    <FormField label="Cliente" required :helper="clienteAutoDetectado ? 'Detectado por la venta de esta unidad — puedes cambiarlo.' : ''">
      <ComboBox v-model="f.cliente_id" :opciones="clientes" opcion-label="_label" opcion-value="id" placeholder="Buscar cliente…" />
    </FormField>

    <FormField label="Motivo del servicio" wide required helper="Lo que reporta el cliente (no da cuerda, se adelanta, cristal rayado…).">
      <textarea v-model="f.motivo" rows="2" class="cr-input"></textarea>
    </FormField>

    <FormField label="Tipo de reparación" required helper="Define el tiempo estimado, el margen objetivo y la garantía.">
      <input v-model="f.tipo_reparacion" class="cr-input" placeholder="servicio_completo, cambio_cristal, lubricacion…" required />
    </FormField>
    <FormField label="Sucursal" helper="Por defecto, la sucursal donde está la unidad.">
      <select v-model="f.sucursal_id" class="cr-input">
        <option :value="null">Automática</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
    </FormField>

    <FormField
      label="Técnico asignado"
      required
      :helper="buscandoTecnico ? 'Buscando el técnico especialista…' : 'Sugerido automáticamente por marca/calibre; puedes cambiarlo.'"
    >
      <select v-model="f.tecnico_id" class="cr-input" @change="tecnicoTocado = true">
        <option :value="null">— sin asignar —</option>
        <option v-for="t in tecnicos" :key="t.id" :value="t.id">{{ t.nombre }}</option>
      </select>
    </FormField>
    <p v-if="sinTecnicoDisponible && !f.tecnico_id" class="sm:col-span-2 flex items-start gap-2 text-xs text-warn">
      <CrIcon name="info" :size="13" class="mt-0.5" />
      No hay ningún técnico activo en esa sucursal/especialidad. Elige uno manualmente o abre la OT sin asignar y complétalo después desde la ficha — no debería quedarse sin técnico por mucho tiempo.
    </p>

    <FormField v-if="pideOverride" label="Autorización — unidad sin venta registrada" wide required>
      <input v-model="f.override" class="cr-input" placeholder="Ej. vendida antes del sistema, verificada con factura N.º…" />
    </FormField>

    <p v-if="error" class="text-sm sm:col-span-2" :class="pideOverride ? 'text-warn' : 'text-bad'" role="alert">{{ error }}</p>
  </FormModal>
</template>
