<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { toast } from '@/shared/ui/toast'
import { crearBeneficiario, listarBeneficiarios, confirmarGasto } from '@/contabilidad/services/contabilidadApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  gasto: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'guardado'])

const f = reactive({ monto: null, estado_pago: 'pagado', medio_pago: 'efectivo', beneficiario_id: null })
const beneficiarios = ref([])
const guardando = ref(false)
const error = ref('')

onMounted(async () => {
  beneficiarios.value = await listarBeneficiarios().catch(() => [])
})
watch(() => props.modelValue, (v) => {
  if (v) { f.monto = props.gasto.monto; f.estado_pago = 'pagado'; f.medio_pago = 'efectivo'; f.beneficiario_id = props.gasto.beneficiario_id; error.value = '' }
})

async function nuevoBeneficiario(nombre) {
  try {
    const b = await crearBeneficiario({ nombre, identificacion: null, tipo_servicio: null })
    beneficiarios.value.push(b)
    return b
  } catch (e) {
    toast.error(e.message)
    return null
  }
}

async function guardar() {
  error.value = ''
  if (!f.monto || Number(f.monto) <= 0) return (error.value = 'Indica el monto real.')
  if (f.estado_pago === 'por_pagar' && !f.beneficiario_id) return (error.value = 'Elige el beneficiario o proveedor.')
  guardando.value = true
  try {
    await confirmarGasto(props.gasto.id, {
      monto: Number(f.monto), estado_pago: f.estado_pago,
      medio_pago: f.estado_pago === 'pagado' ? f.medio_pago : null,
      beneficiario_id: f.estado_pago === 'por_pagar' ? f.beneficiario_id : null,
    })
    toast.success('Gasto confirmado')
    emit('update:modelValue', false)
    emit('guardado')
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
    :titulo="`Confirmar gasto — ${gasto.categoria_nombre}`"
    subtitulo="Generado automáticamente por un gasto recurrente. Ajusta el monto real y elige cómo se paga."
    :guardando="guardando"
    ancho="max-w-xl"
    :sucio="true"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Monto real" required>
      <input v-model="f.monto" type="number" step="0.01" min="0.01" class="cr-input tabular-nums" />
    </FormField>
    <FormField label="¿Cómo se paga?" wide>
      <div class="flex gap-4 text-sm">
        <label class="flex items-center gap-1"><input v-model="f.estado_pago" type="radio" value="pagado" /> Pagado ahora</label>
        <label class="flex items-center gap-1"><input v-model="f.estado_pago" type="radio" value="por_pagar" /> Por pagar</label>
      </div>
    </FormField>
    <FormField v-if="f.estado_pago === 'pagado'" label="Medio de pago" required>
      <select v-model="f.medio_pago" class="cr-input">
        <option value="efectivo">Efectivo</option>
        <option value="transferencia">Transferencia</option>
        <option value="cheque">Cheque</option>
        <option value="tarjeta">Tarjeta</option>
      </select>
    </FormField>
    <FormField v-else label="Beneficiario / proveedor" required>
      <ComboBox v-model="f.beneficiario_id" :opciones="beneficiarios" opcion-label="nombre" opcion-value="id"
               placeholder="Buscar o crear…" :crear="nuevoBeneficiario" crear-label="Crear beneficiario" />
    </FormField>
    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
