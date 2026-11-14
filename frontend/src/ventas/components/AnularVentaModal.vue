<script setup>
import { ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import { anularVenta } from '@/ventas/services/ventasApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  venta: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'hecho'])

const motivo = ref('')
const guardando = ref(false)
const error = ref('')

watch(() => props.modelValue, (v) => { if (v) { motivo.value = ''; error.value = '' } })

async function guardar() {
  error.value = ''
  if (motivo.value.trim().length < 3) return (error.value = 'El motivo es obligatorio.')
  guardando.value = true
  try {
    await anularVenta(props.venta.id, motivo.value.trim())
    toast.success('Venta anulada · stock reingresado')
    emit('update:modelValue', false)
    emit('hecho')
  } catch (e) {
    error.value = e.status === 409 ? 'La unidad tiene una orden de trabajo abierta; resuélvela antes de anular.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    titulo="Anular la venta"
    subtitulo="Reingresa el stock, revierte el margen y el nivel de fidelización, marca la cuenta por cobrar como anulada y deja constancia."
    :guardando="guardando"
    ancho="max-w-lg"
    :sucio="!!motivo"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Motivo de la anulación" wide required>
      <textarea v-model="motivo" rows="3" class="cr-input"></textarea>
    </FormField>
    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
