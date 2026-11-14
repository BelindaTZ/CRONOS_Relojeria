<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { listarPiezas } from '@/piezas'
import { agregarPieza, solicitarCompraUrgente } from '@/servicio_tecnico/services/servicioTecnicoApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  ot: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'hecho'])

const f = reactive({ pieza_id: null, tipo_elegido: 'original', cantidad: 1 })
const piezas = ref([])
const guardando = ref(false)
const error = ref('')
const sinStock = ref(false) // el último intento falló por 409 (stock insuficiente)

// Piezas ya presupuestadas y aprobadas por el cliente (con su preferencia
// original/no-original) — accesos rápidos, para que el técnico consuma
// exactamente lo que el cliente aceptó en vez de elegir a ciegas.
const lineasPresupuesto = computed(() => {
  const p = props.ot?.presupuesto
  if (!p || p.estado !== 'aprobado') return []
  return p.lineas.map((l) => {
    const noOriginal = l.preferencia_cliente === 'no_original'
    return {
      linea_id: l.id,
      etiqueta: noOriginal ? l.pieza_no_original : l.pieza_original,
      preferencia: l.preferencia_cliente || 'original',
      pieza_id: noOriginal ? l.pieza_no_original_id : l.pieza_original_id,
      cantidad: l.cantidad,
    }
  }).filter((l) => l.pieza_id)
})

function usarLineaPresupuesto(l) {
  f.pieza_id = l.pieza_id
  f.tipo_elegido = l.preferencia === 'no_original' ? 'no_original' : 'original'
  f.cantidad = l.cantidad
  sinStock.value = false
}

onMounted(async () => {
  piezas.value = await listarPiezas({ page: 1, size: 100 })
    .then((r) => r.items.map((p) => ({ ...p, _label: `${p.codigo} · ${p.descripcion}` })))
    .catch(() => [])
})
watch(
  () => props.modelValue,
  (v) => { if (v) { Object.assign(f, { pieza_id: null, tipo_elegido: 'original', cantidad: 1 }); error.value = ''; sinStock.value = false } },
)

async function guardar() {
  error.value = ''
  sinStock.value = false
  if (!f.pieza_id) return (error.value = 'Selecciona la pieza.')
  guardando.value = true
  try {
    await agregarPieza(props.ot.id, { pieza_id: f.pieza_id, tipo_elegido: f.tipo_elegido, cantidad: Number(f.cantidad) || 1 })
    toast.success('Pieza registrada · stock descontado')
    emit('hecho')
    emit('update:modelValue', false)
  } catch (e) {
    if (e.status === 409) {
      error.value = 'Stock insuficiente para esa pieza en esta sucursal.'
      sinStock.value = true
    } else {
      error.value = e.message
    }
  } finally {
    guardando.value = false
  }
}

const pidiendoCompra = ref(false)
async function pedirCompraUrgente() {
  if (!f.pieza_id) return
  pidiendoCompra.value = true
  try {
    await solicitarCompraUrgente(props.ot.id, { pieza_id: f.pieza_id, cantidad: Number(f.cantidad) || 1 })
    toast.success('Se avisó al encargado de compras')
    sinStock.value = false
  } catch (e) {
    toast.error(e.message)
  } finally {
    pidiendoCompra.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    titulo="Registrar pieza usada"
    subtitulo="Descuenta stock (003) al confirmarla; los perecederos salen por FEFO. El stock nunca queda negativo."
    :guardando="guardando"
    ancho="max-w-xl"
    :sucio="!!f.pieza_id"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <div v-if="lineasPresupuesto.length" class="sm:col-span-2">
      <p class="cr-label mb-1.5">Piezas aprobadas en el presupuesto</p>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="l in lineasPresupuesto" :key="l.linea_id" type="button"
          class="cr-btn cr-btn-ghost text-xs"
          :class="{ 'border-gold-strong text-gold-strong': f.pieza_id === l.pieza_id }"
          @click="usarLineaPresupuesto(l)"
        >
          {{ l.etiqueta }} <span class="text-ink-3">· {{ l.preferencia === 'no_original' ? 'no original' : 'original' }} ×{{ l.cantidad }}</span>
        </button>
      </div>
    </div>

    <FormField label="Pieza" wide required helper="También puedes buscar cualquier otra pieza fuera del presupuesto.">
      <ComboBox v-model="f.pieza_id" :opciones="piezas" opcion-label="_label" opcion-value="id" placeholder="Buscar pieza…" />
    </FormField>
    <FormField label="Tipo elegido">
      <select v-model="f.tipo_elegido" class="cr-input">
        <option value="original">Original</option>
        <option value="no_original">No original de calidad equivalente</option>
      </select>
    </FormField>
    <FormField label="Cantidad">
      <input v-model="f.cantidad" type="number" min="1" class="cr-input tabular-nums" />
    </FormField>
    <div v-if="error" class="sm:col-span-2">
      <p class="text-sm text-bad" role="alert">{{ error }}</p>
      <button v-if="sinStock" type="button" class="cr-btn cr-btn-ghost mt-1.5 text-xs" :disabled="pidiendoCompra" @click="pedirCompraUrgente">
        <CrIcon name="send" :size="13" /> {{ pidiendoCompra ? 'Avisando…' : 'Solicitar compra urgente al encargado' }}
      </button>
    </div>
  </FormModal>
</template>
