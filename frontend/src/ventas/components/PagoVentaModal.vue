<script setup>
import { reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import { registrarPagoVenta } from '@/ventas/services/ventasApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  venta: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'hecho'])

const f = reactive({ medio_pago: 'efectivo', monto: null, referencia: '' })
const guardando = ref(false)
const error = ref('')
const saldo = ref(null)

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    error.value = ''
    saldo.value = null
    f.medio_pago = 'efectivo'
    f.monto = props.venta.saldo != null ? Number(props.venta.saldo) : null
    f.referencia = ''
  },
)

async function guardar() {
  error.value = ''
  if (!f.monto || Number(f.monto) <= 0) return (error.value = 'Indica el monto.')
  guardando.value = true
  try {
    const r = await registrarPagoVenta(props.venta.id, {
      medio_pago: f.medio_pago, monto: Number(f.monto), referencia: f.referencia.trim() || null,
    })
    saldo.value = r.saldo
    toast.success(`Pago registrado · saldo ${r.saldo}`)
    emit('hecho')
    if (Number(r.saldo) <= 0) emit('update:modelValue', false)
    else f.monto = Number(r.saldo)
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
    titulo="Registrar pago"
    subtitulo="Pagos multimedios (efectivo, transferencia, cheque, tarjeta). Sin pasarela en línea. La venta no se confirma con saldo pendiente salvo crédito autorizado."
    :guardando="guardando"
    ancho="max-w-lg"
    :sucio="true"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Medio de pago" required>
      <select v-model="f.medio_pago" class="cr-input">
        <option value="efectivo">Efectivo</option>
        <option value="transferencia">Transferencia</option>
        <option value="cheque">Cheque</option>
        <option value="tarjeta">Tarjeta</option>
      </select>
    </FormField>
    <FormField label="Monto" required>
      <input v-model="f.monto" type="number" step="0.01" min="0.01" class="cr-input tabular-nums" />
    </FormField>
    <FormField label="Referencia" wide helper="N.º de comprobante / cheque / últimos dígitos de tarjeta.">
      <input v-model="f.referencia" class="cr-input" />
    </FormField>
    <p v-if="saldo != null" class="text-sm text-ink-2 sm:col-span-2">Saldo pendiente: <strong class="tabular-nums">{{ saldo }}</strong></p>
    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
