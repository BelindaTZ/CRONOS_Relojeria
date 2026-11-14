<script setup>
import { computed, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { registrarRecepcion } from '@/proveedores/services/proveedoresApi'
import {
  crearColor,
  crearMarcaReloj,
  crearMaterial,
  listarColores,
  listarMarcasReloj,
  listarMateriales,
} from '@/configuracion'
import { crearCalibre, crearReloj, listarCalibres } from '@/inventario'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  orden: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'recibida'])

const CRISTALES = ['zafiro', 'mineral', 'acrilico', 'otro']
const paso = ref(1)
const guardando = ref(false)
const error = ref('')
const estado = reactive({ fecha_real: '', numero_factura: '', numero_guia: '', lineas: [] })
const unidades = ref([]) // fichas de reloj a registrar tras la recepción

const marcas = ref([])
const materiales = ref([])
const colores = ref([])
const calibres = ref([])

const relojesARecibir = computed(() =>
  estado.lineas.filter((l) => l.item_tipo === 'reloj' && Number(l.cantidad_recibida) > 0),
)
const totalRelojes = computed(() =>
  relojesARecibir.value.reduce((s, l) => s + Number(l.cantidad_recibida || 0), 0),
)

watch(
  () => props.modelValue,
  async (v) => {
    if (!v || !props.orden) return
    paso.value = 1
    error.value = ''
    estado.fecha_real = new Date().toISOString().slice(0, 10)
    estado.numero_factura = ''
    estado.numero_guia = ''
    estado.lineas = props.orden.lineas
      .map((l) => ({
        linea_orden_compra_id: l.id,
        item_tipo: l.item_tipo,
        item_ref: l.item_ref,
        marca: l.marca,
        calibre_codigo: l.calibre_codigo,
        anio: l.anio,
        numero_serie: l.numero_serie,
        descripcion: l.descripcion,
        es_perecedero: l.es_perecedero,
        pendiente: l.cantidad - l.cantidad_recibida,
        cantidad_recibida: Math.max(l.cantidad - l.cantidad_recibida, 0),
        costo_unitario: l.costo_unitario_real ?? l.costo_unitario ?? null,
        lote: '',
        fecha_caducidad: '',
      }))
      .filter((l) => l.pendiente > 0)
    unidades.value = []
    if (!marcas.value.length) {
      ;[marcas.value, materiales.value, colores.value, calibres.value] = await Promise.all([
        listarMarcasReloj(true).catch(() => []),
        listarMateriales(true).catch(() => []),
        listarColores(true).catch(() => []),
        listarCalibres().catch(() => []),
      ])
    }
  },
)

function fichaVacia(l) {
  return {
    linea_orden_compra_id: l.linea_orden_compra_id,
    numero_serie: '',
    marca_id: marcas.value.find((m) => m.nombre === l.marca)?.id ?? null,
    referencia: l.item_ref,
    calibre_id: calibres.value.find((c) => c.codigo === l.calibre_codigo)?.id ?? null,
    anio_fabricacion: l.anio ?? null,
    material_caja_id: null,
    material_brazalete_id: null,
    color_esfera_id: null,
    tipo_cristal: '',
    resistencia_agua: '',
    precio_venta: null,
    full_set: false,
    full_set_detalle: '',
    _label: l.item_ref,
  }
}

async function nuevaMarca(t) { try { const m = await crearMarcaReloj({ nombre: t }); marcas.value.push(m); return m } catch { return null } }
async function nuevoMaterial(t) { try { const m = await crearMaterial(t); materiales.value.push(m); return m } catch { return null } }
async function nuevoColor(t) { try { const c = await crearColor({ nombre: t }); colores.value.push(c); return c } catch { return null } }
async function nuevoCalibre(t) { try { const c = await crearCalibre({ codigo: t }); calibres.value.push(c); return c } catch { return null } }

function validarPaso1() {
  const conCant = estado.lineas.filter((l) => Number(l.cantidad_recibida) > 0)
  if (!conCant.length) return 'Indica al menos una cantidad recibida.'
  for (const l of conCant) {
    if (l.es_perecedero && (!l.lote || !l.fecha_caducidad)) return `«${l.item_ref}» es perecedero: falta lote o caducidad.`
  }
  return ''
}

async function avanzar() {
  error.value = ''
  if (paso.value === 1) {
    const e = validarPaso1()
    if (e) return (error.value = e)
    // arma una ficha por unidad de reloj recibida
    unidades.value = []
    for (const l of relojesARecibir.value) {
      for (let k = 0; k < Number(l.cantidad_recibida); k++) {
        const ficha = fichaVacia(l)
        if (k === 0 && l.numero_serie) ficha.numero_serie = l.numero_serie // ya se conocía al pedir
        unidades.value.push(ficha)
      }
    }
    if (unidades.value.length) {
      paso.value = 2
      return
    }
    return enviar() // sin relojes: recepción directa
  }
  // paso 2: valida series
  for (const u of unidades.value) {
    if (!u.numero_serie.trim()) return (error.value = 'Cada unidad de reloj necesita su número de serie.')
    if (!u.marca_id) return (error.value = `Elige la marca de «${u._label}».`)
  }
  return enviar()
}

async function enviar() {
  guardando.value = true
  try {
    const lineas = estado.lineas.filter((l) => Number(l.cantidad_recibida) > 0)
    const res = await registrarRecepcion(props.orden.id, {
      fecha_real: estado.fecha_real,
      numero_factura: estado.numero_factura.trim() || null,
      numero_guia: estado.numero_guia.trim() || null,
      lineas: lineas.map((l) => ({
        linea_orden_compra_id: l.linea_orden_compra_id,
        cantidad_recibida: Number(l.cantidad_recibida),
        costo_unitario: l.costo_unitario === null || l.costo_unitario === '' ? null : Number(l.costo_unitario),
        lote: l.lote || null,
        fecha_caducidad: l.fecha_caducidad || null,
      })),
    })

    let fichados = 0
    for (const u of unidades.value) {
      try {
        await crearReloj({
          recepcion_linea_id: u.linea_orden_compra_id,
          numero_serie: u.numero_serie.trim(),
          marca_id: u.marca_id,
          referencia: u.referencia,
          calibre_id: u.calibre_id,
          anio_fabricacion: u.anio_fabricacion ? Number(u.anio_fabricacion) : null,
          material_caja_id: u.material_caja_id,
          material_brazalete_id: u.material_brazalete_id,
          color_esfera_id: u.color_esfera_id,
          tipo_cristal: u.tipo_cristal || null,
          resistencia_agua: u.resistencia_agua || null,
          precio_venta: u.precio_venta === null || u.precio_venta === '' ? null : Number(u.precio_venta),
          full_set: u.full_set,
          full_set_detalle: u.full_set ? u.full_set_detalle : null,
          estado_producto: 'nuevo',
        })
        fichados++
      } catch (e) {
        toast.error(`No se pudo fichar ${u.numero_serie}: ${e.message}`)
      }
    }

    const piezas = estado.lineas.filter((l) => l.item_tipo === 'pieza' && Number(l.cantidad_recibida) > 0)
      .reduce((s, l) => s + Number(l.cantidad_recibida), 0)
    const partes = []
    if (fichados) partes.push(`${fichados} reloj(es) fichados`)
    if (piezas) partes.push(`${piezas} pieza(s) ingresadas`)
    toast.success(
      `Orden #${props.orden.id} ${res.estado === 'recibida' ? 'recibida' : 'recibida (parcial)'}` +
        (partes.length ? ` · ${partes.join(' · ')}` : ''),
    )
    emit('update:modelValue', false)
    emit('recibida')
  } catch (e) {
    error.value = e.status === 422 ? e.message : e.message
    paso.value = 1
  } finally {
    guardando.value = false
  }
}

const totalRecibir = computed(() => estado.lineas.reduce((s, l) => s + Number(l.cantidad_recibida || 0), 0))
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="orden ? `Recibir orden #${orden.id}` : 'Recibir'"
    :subtitulo="paso === 1
      ? 'Confirma cantidades y el costo real que informó el proveedor.'
      : 'Ficha cada unidad de reloj recibida con su número de serie.'"
    :guardando="guardando"
    ancho="max-w-3xl"
    :sucio="totalRecibir > 0"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="avanzar"
  >
    <!-- paso -->
    <div class="sm:col-span-2 flex items-center gap-2 text-xs">
      <span class="flex items-center gap-1.5" :class="paso === 1 ? 'text-ink' : 'text-ink-3'">
        <span class="grid h-5 w-5 place-items-center rounded-full border" :class="paso === 1 ? 'border-good bg-good-bg text-good' : 'border-hairline'">1</span>
        Cantidades
      </span>
      <CrIcon name="chevron-right" :size="12" class="text-ink-3" />
      <span class="flex items-center gap-1.5" :class="paso === 2 ? 'text-ink' : 'text-ink-3'">
        <span class="grid h-5 w-5 place-items-center rounded-full border" :class="paso === 2 ? 'border-good bg-good-bg text-good' : 'border-hairline'">2</span>
        Fichar relojes
      </span>
    </div>

    <!-- PASO 1 -->
    <template v-if="paso === 1">
      <FormField label="Fecha real de recepción" required>
        <input v-model="estado.fecha_real" type="date" class="cr-input" required />
      </FormField>
      <FormField label="N.º de factura del proveedor" helper="Queda ligada a esta recepción">
        <input v-model="estado.numero_factura" class="cr-input" placeholder="p. ej. 001-002-000012345" />
      </FormField>
      <FormField label="N.º de guía / remito" helper="Opcional">
        <input v-model="estado.numero_guia" class="cr-input" />
      </FormField>

      <div
        v-if="relojesARecibir.length"
        class="sm:col-span-2 rounded-xl border border-gold/40 bg-gold-pale px-3 py-2 text-sm text-ink-2"
      >
        <CrIcon name="watch" :size="14" class="mr-1 inline text-gold-strong" />
        Esta orden incluye <strong class="text-ink">{{ totalRelojes }} reloj(es)</strong>. Al continuar
        pasas al <strong class="text-ink">paso 2</strong> y fichas cada unidad con su N.º de serie —
        la recepción no se registra hasta terminar ese paso.
      </div>
      <p
        v-else-if="estado.lineas.length"
        class="sm:col-span-2 text-sm text-ink-3"
      >
        Esta orden es solo de piezas / consumibles: al registrar, el stock se actualiza directamente (sin paso 2).
      </p>

      <div class="sm:col-span-2">
        <p class="cr-label mb-2">Líneas por recibir</p>
        <div class="space-y-2">
          <div v-for="l in estado.lineas" :key="l.linea_orden_compra_id" class="rounded-xl border border-hairline p-3">
            <div class="flex items-baseline justify-between">
              <span class="font-medium text-ink">
                <template v-if="l.item_tipo === 'reloj'">{{ l.marca }} {{ l.item_ref }}</template>
                <template v-else>{{ l.item_ref }}</template>
                <span class="ml-1 text-xs font-normal text-ink-3">{{ l.item_tipo }}</span>
              </span>
              <span class="text-xs text-ink-3">pendiente: {{ l.pendiente }}</span>
            </div>
            <p v-if="l.descripcion" class="text-xs text-ink-3">{{ l.descripcion }}</p>
            <div class="mt-2 grid gap-2 sm:grid-cols-3">
              <label class="space-y-1">
                <span class="cr-label">Cantidad recibida</span>
                <input v-model.number="l.cantidad_recibida" type="number" min="0" class="cr-input" />
              </label>
              <label class="space-y-1">
                <span class="cr-label">Costo unitario real</span>
                <input v-model="l.costo_unitario" type="number" min="0" step="0.01" class="cr-input" placeholder="Según el proveedor" />
              </label>
              <label v-if="l.es_perecedero" class="space-y-1">
                <span class="cr-label">Lote</span>
                <input v-model="l.lote" class="cr-input" />
              </label>
              <label v-if="l.es_perecedero" class="space-y-1">
                <span class="cr-label">Caducidad</span>
                <input v-model="l.fecha_caducidad" type="date" class="cr-input" />
              </label>
            </div>
            <p v-if="l.cantidad_recibida > l.pendiente" class="mt-1 text-xs text-warn">
              Sobre-entrega: recibes más de lo pendiente. Se marcará para revisión.
            </p>
          </div>
          <p v-if="!estado.lineas.length" class="text-sm text-ink-3">Esta orden ya no tiene líneas pendientes.</p>
        </div>
      </div>
    </template>

    <!-- PASO 2 -->
    <template v-else>
      <div v-for="(u, i) in unidades" :key="i" class="sm:col-span-2 rounded-xl border border-hairline p-3">
        <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-3">
          Unidad {{ i + 1 }} de {{ unidades.length }} · {{ u._label }}
        </p>
        <div class="grid gap-2 sm:grid-cols-2">
          <label class="space-y-1"><span class="cr-label">N.º de serie *</span><input v-model="u.numero_serie" class="cr-input" required /></label>
          <label class="space-y-1"><span class="cr-label">Referencia / modelo</span><input v-model="u.referencia" class="cr-input" /></label>
          <div class="space-y-1"><span class="cr-label">Marca *</span>
            <ComboBox v-model="u.marca_id" :opciones="marcas" opcion-label="nombre" opcion-value="id" placeholder="Marca…" :crear="nuevaMarca" crear-label="Crear marca" />
          </div>
          <div class="space-y-1"><span class="cr-label">Calibre</span>
            <ComboBox v-model="u.calibre_id" :opciones="calibres" opcion-label="codigo" opcion-value="id" placeholder="Calibre…" :crear="nuevoCalibre" crear-label="Crear calibre" />
          </div>
          <label class="space-y-1"><span class="cr-label">Año</span><input v-model="u.anio_fabricacion" type="number" min="1900" max="2100" class="cr-input" /></label>
          <div class="space-y-1"><span class="cr-label">Color de esfera</span>
            <ComboBox v-model="u.color_esfera_id" :opciones="colores" opcion-label="nombre" opcion-value="id" placeholder="Color…" :crear="nuevoColor" crear-label="Crear color" />
          </div>
          <div class="space-y-1"><span class="cr-label">Material de caja</span>
            <ComboBox v-model="u.material_caja_id" :opciones="materiales" opcion-label="nombre" opcion-value="id" placeholder="Material…" :crear="nuevoMaterial" crear-label="Crear material" />
          </div>
          <div class="space-y-1"><span class="cr-label">Material de brazalete</span>
            <ComboBox v-model="u.material_brazalete_id" :opciones="materiales" opcion-label="nombre" opcion-value="id" placeholder="Material…" :crear="nuevoMaterial" crear-label="Crear material" />
          </div>
          <label class="space-y-1"><span class="cr-label">Tipo de cristal</span>
            <select v-model="u.tipo_cristal" class="cr-input"><option value="">—</option><option v-for="c in CRISTALES" :key="c" :value="c">{{ c }}</option></select>
          </label>
          <label class="space-y-1"><span class="cr-label">Resistencia al agua</span><input v-model="u.resistencia_agua" class="cr-input" placeholder="p. ej. 300 m" /></label>
          <label class="space-y-1"><span class="cr-label">Precio de venta</span><input v-model="u.precio_venta" type="number" min="0" step="0.01" class="cr-input" /></label>
        </div>
        <label class="mt-2 flex items-center gap-2 text-sm">
          <input v-model="u.full_set" type="checkbox" /> Full Set
        </label>
        <input v-if="u.full_set" v-model="u.full_set_detalle" class="cr-input mt-1" placeholder="Detalle del Full Set" />
      </div>
    </template>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>

    <template #footer>
      <button v-if="paso === 2" type="button" class="cr-btn cr-btn-ghost" :disabled="guardando" @click="paso = 1">Atrás</button>
      <button v-else type="button" class="cr-btn cr-btn-ghost" @click="emit('update:modelValue', false)">Cancelar</button>
      <button type="submit" class="cr-btn cr-btn-primary min-w-[9rem]" :disabled="guardando">
        <span v-if="guardando" class="inline-flex items-center gap-2"><CrIcon name="refresh-cw" :size="15" class="animate-spin" /> Guardando…</span>
        <span v-else-if="paso === 1 && relojesARecibir.length">Siguiente: fichar relojes</span>
        <span v-else>Registrar recepción</span>
      </button>
    </template>
  </FormModal>
</template>
