<script setup>
import { reactive, ref } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import { autorizarBaja } from '@/mermas/services/mermasApi'

const props = defineProps({ modelValue: { type: Boolean, default: false }, mermaId: { type: Number, required: true } })
const emit = defineEmits(['update:modelValue', 'autorizado'])

const f = reactive({ observacion: '' })
const guardando = ref(false)
const error = ref('')

async function guardar() {
  guardando.value = true
  error.value = ''
  try {
    const m = await autorizarBaja(props.mermaId, { observacion: f.observacion.trim() || null })
    toast.success('Baja autorizada')
    f.observacion = ''
    emit('update:modelValue', false)
    emit('autorizado', m)
  } catch (e) {
    error.value = e.status === 403 ? 'Solo Gerencia General autoriza la baja.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue" titulo="Autorizar baja" :guardando="guardando" ancho="max-w-md" :sucio="true"
    @update:model-value="$emit('update:modelValue', $event)" @guardar="guardar"
  >
    <p v-if="error" class="text-sm text-bad" role="alert">{{ error }}</p>
    <FormField label="Observación" wide helper="Ej. acta revisada, denuncia adjunta, decisión del propietario.">
      <textarea v-model="f.observacion" rows="3" class="cr-input" maxlength="255" />
    </FormField>
  </FormModal>
</template>
