<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { listarPiezas } from '@/piezas'
import { crearPresupuesto } from '@/servicio_tecnico/services/servicioTecnicoApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  ot: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'hecho'])

const f = reactive({ precio_servicio: null, lineas: [] })
const piezas = ref([])
const guardando = ref(false)
const error = ref('')

onMounted(async () => {
  piezas.value = await listarPiezas({ page: 1, size: 100 })
    .then((r) => r.items.map((p) => ({ ...p, _label: `${p.codigo} · ${p.descripcion}` })))
    .catch(() => [])
})
watch(
  () => props.modelValue,
  (v) => { if (v) { f.precio_servicio = props.ot.precio_cobrado ?? null; f.lineas = []; error.value = '' } },
)

const agregar = () => f.lineas.push({ pieza_original_id: null, pieza_no_original_id: null, precio_original: null, precio_no_original: null, cantidad: 1 })
const quitar = (i) => f.lineas.splice(i, 1)

// El precio lo fija el catálogo (`precio_venta_suelta`), nunca se inventa uno para
// el cliente (feedback del usuario, 2026-09-11: "las piezas van a estar sin
// precio... no nos vamos a inventar uno") — al elegir la pieza se autorrellena
// con su precio real; el técnico puede editarlo después si negocia otro.
function autollenarPrecio(linea, campo, piezaId) {
  const p = piezas.value.find((x) => x.id === piezaId)
  linea[campo] = p?.precio_venta_suelta != null ? Number(p.precio_venta_suelta) : null
}
function sinPrecioCatalogo(piezaId) {
  if (!piezaId) return false
  const p = piezas.value.find((x) => x.id === piezaId)
  return !!p && p.precio_venta_suelta == null
}

async function guardar() {
  error.value = ''
  if (f.precio_servicio == null || Number(f.precio_servicio) < 0) return (error.value = 'Indica el precio del servicio.')
  if (f.lineas.some((l) => !l.pieza_original_id)) return (error.value = 'Cada línea necesita la pieza original.')
  if (f.lineas.some((l) => l.precio_original == null)) return (error.value = 'Falta el precio de una pieza — no se le puede cobrar al cliente sin un precio real.')
  if (f.lineas.some((l) => l.pieza_no_original_id && l.precio_no_original == null)) return (error.value = 'Falta el precio de una pieza no original.')
  guardando.value = true
  try {
    await crearPresupuesto(props.ot.id, {
      precio_servicio: Number(f.precio_servicio),
      lineas: f.lineas.map((l) => ({
        pieza_original_id: l.pieza_original_id,
        pieza_no_original_id: l.pieza_no_original_id || null,
        precio_original: l.precio_original != null ? Number(l.precio_original) : null,
        precio_no_original: l.precio_no_original != null ? Number(l.precio_no_original) : null,
        cantidad: Number(l.cantidad) || 1,
      })),
    })
    toast.success('Presupuesto creado')
    emit('hecho')
    emit('update:modelValue', false)
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    titulo="Armar presupuesto"
    subtitulo="Precio del servicio y detalle de piezas con opción original / no original de calidad equivalente. La aprobación del cliente se registra por separado."
    :guardando="guardando"
    ancho="max-w-3xl"
    :sucio="f.precio_servicio != null"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Precio del servicio (mano de obra)" required>
      <input v-model="f.precio_servicio" type="number" step="0.01" min="0" class="cr-input tabular-nums" />
    </FormField>

    <div class="sm:col-span-2">
      <div class="mb-2 flex items-center justify-between">
        <span class="text-sm font-medium text-ink">Piezas del presupuesto</span>
        <button type="button" class="cr-btn cr-btn-ghost text-xs" @click="agregar"><CrIcon name="plus" :size="13" /> Añadir pieza</button>
      </div>
      <p v-if="!f.lineas.length" class="rounded-md bg-surface-sunk px-3 py-2 text-xs text-ink-3">Sin piezas: el presupuesto es solo mano de obra.</p>
      <div v-for="(l, i) in f.lineas" :key="i" class="mb-2 rounded-lg border border-hairline p-3">
        <div class="grid gap-2 sm:grid-cols-2">
          <FormField label="Pieza original" required>
            <ComboBox
              v-model="l.pieza_original_id" :opciones="piezas" opcion-label="_label" opcion-value="id"
              placeholder="Buscar…" @update:model-value="(v) => autollenarPrecio(l, 'precio_original', v)"
            />
          </FormField>
          <FormField label="Pieza no original (opcional)">
            <ComboBox
              v-model="l.pieza_no_original_id" :opciones="piezas" opcion-label="_label" opcion-value="id"
              placeholder="Equivalente…" @update:model-value="(v) => autollenarPrecio(l, 'precio_no_original', v)"
            />
          </FormField>
          <FormField
            label="Precio original" required
            :helper="sinPrecioCatalogo(l.pieza_original_id) ? 'Esta pieza no tiene precio en el catálogo — indícalo aquí o cárgalo en Piezas.' : 'Precio de catálogo; edítalo si negocias otro.'"
          >
            <input v-model="l.precio_original" type="number" step="0.01" min="0" class="cr-input tabular-nums" placeholder="Sin precio de catálogo" />
          </FormField>
          <FormField
            label="Precio no original"
            :helper="l.pieza_no_original_id && sinPrecioCatalogo(l.pieza_no_original_id) ? 'Esta pieza no tiene precio en el catálogo — indícalo aquí o cárgalo en Piezas.' : ''"
          >
            <input v-model="l.precio_no_original" type="number" step="0.01" min="0" class="cr-input tabular-nums" placeholder="Sin precio de catálogo" />
          </FormField>
          <FormField label="Cantidad">
            <input v-model="l.cantidad" type="number" min="1" class="cr-input tabular-nums" />
          </FormField>
        </div>
        <button type="button" class="mt-1 text-xs text-bad" @click="quitar(i)">Quitar línea</button>
      </div>
    </div>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
