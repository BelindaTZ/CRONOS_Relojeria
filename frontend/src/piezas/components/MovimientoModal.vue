<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import { registrarMovimiento } from '@/piezas/services/piezasApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  pieza: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'registrado'])

// tipos que un operador registra a mano; el resto llega de OT / ventas / traslados
const TIPOS = [
  { v: 'ingreso', l: 'Ingreso a stock' },
  { v: 'ajuste', l: 'Ajuste manual (con signo)' },
  { v: 'merma', l: 'Merma / baja' },
]

function vacio() {
  return { sucursal_id: null, tipo: 'ingreso', cantidad: 1, lote: '', fecha_caducidad: '', nota: '' }
}
const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')
const sucursales = ref([])

const pideLote = computed(() => props.pieza?.perecedera && f.tipo === 'ingreso')

onMounted(async () => {
  sucursales.value = (await listarSucursales().catch(() => ({ items: [] }))).items
})
watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      Object.assign(f, vacio())
      error.value = ''
    }
  },
)

async function guardar() {
  error.value = ''
  if (!f.sucursal_id) return (error.value = 'Elige la sucursal.')
  if (f.tipo !== 'ajuste' && Number(f.cantidad) <= 0) return (error.value = 'La cantidad debe ser mayor que cero.')
  if (f.tipo === 'ajuste' && Number(f.cantidad) === 0) return (error.value = 'El ajuste no puede ser cero.')
  if (pideLote.value && (!f.lote.trim() || !f.fecha_caducidad)) return (error.value = 'Pieza perecedera: indica lote y fecha de caducidad.')

  if (f.tipo === 'ajuste' || f.tipo === 'merma') {
    const ok = await confirm({
      title: f.tipo === 'merma' ? 'Registrar merma' : 'Ajuste manual de stock',
      message: 'Quedará registrado en el libro de movimientos y en la auditoría. ¿Continuar?',
      confirmLabel: 'Registrar',
      tone: 'danger',
    })
    if (!ok) return
  }

  guardando.value = true
  try {
    const mv = await registrarMovimiento(props.pieza.id, {
      sucursal_id: f.sucursal_id,
      tipo: f.tipo,
      cantidad: Number(f.cantidad),
      lote: pideLote.value ? f.lote.trim() : null,
      fecha_caducidad: pideLote.value ? f.fecha_caducidad : null,
      nota: f.nota.trim() || null,
    })
    toast.success(`Movimiento registrado${mv.nota && mv.nota.includes('vencido') ? ' · ⚠ lote vencido' : ''}`)
    emit('update:modelValue', false)
    emit('registrado')
  } catch (e) {
    error.value =
      e.code === 'stock_insuficiente' ? e.message :
      e.status === 422 ? e.message : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="`Movimiento de stock · ${pieza?.codigo}`"
    subtitulo="El stock nunca queda negativo. Los movimientos no se editan ni se borran."
    :guardando="guardando"
    ancho="max-w-lg"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Sucursal" required>
      <ComboBox v-model="f.sucursal_id" :opciones="sucursales" opcion-label="nombre" opcion-value="id" placeholder="Elegir sucursal…" />
    </FormField>
    <FormField label="Tipo de movimiento">
      <select v-model="f.tipo" class="cr-input">
        <option v-for="t in TIPOS" :key="t.v" :value="t.v">{{ t.l }}</option>
      </select>
    </FormField>

    <FormField
      label="Cantidad"
      required
      :helper="f.tipo === 'ajuste' ? 'Positivo suma, negativo resta.' : ''"
    >
      <input v-model="f.cantidad" type="number" :min="f.tipo === 'ajuste' ? undefined : 1" class="cr-input" required />
    </FormField>

    <FormField v-if="pideLote" label="Lote" required><input v-model="f.lote" class="cr-input" required /></FormField>
    <FormField v-if="pideLote" label="Fecha de caducidad" required>
      <input v-model="f.fecha_caducidad" type="date" class="cr-input" required />
    </FormField>

    <FormField label="Nota" wide><input v-model="f.nota" class="cr-input" placeholder="Referencia u observación (opcional)" /></FormField>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
