<script setup>
import { onMounted, reactive, ref } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { toast } from '@/shared/ui/toast'
import { listarProveedores } from '@/proveedores'
import { crearReclamoMerma } from '@/mermas/services/mermasApi'

const props = defineProps({ modelValue: { type: Boolean, default: false }, mermaId: { type: Number, required: true } })
const emit = defineEmits(['update:modelValue', 'guardado'])

const f = reactive({ destino: 'proveedor', proveedor_id: null, aseguradora: '' })
const guardando = ref(false)
const error = ref('')
const proveedores = ref([])

onMounted(async () => {
  proveedores.value = await listarProveedores({ size: 100 }).then((r) => r.items).catch(() => [])
})

async function guardar() {
  if (f.destino === 'proveedor' && !f.proveedor_id) return (error.value = 'Elige el proveedor.')
  if (f.destino === 'seguro' && !f.aseguradora.trim()) return (error.value = 'Indica la aseguradora.')
  error.value = ''
  guardando.value = true
  try {
    const m = await crearReclamoMerma(props.mermaId, {
      destino: f.destino, proveedor_id: f.destino === 'proveedor' ? f.proveedor_id : null,
      aseguradora: f.destino === 'seguro' ? f.aseguradora.trim() : null,
    })
    toast.success('Reclamo registrado')
    Object.assign(f, { destino: 'proveedor', proveedor_id: null, aseguradora: '' })
    emit('update:modelValue', false)
    emit('guardado', m)
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue" titulo="Registrar reclamo" :guardando="guardando" ancho="max-w-md" :sucio="true"
    @update:model-value="$emit('update:modelValue', $event)" @guardar="guardar"
  >
    <p v-if="error" class="text-sm text-bad" role="alert">{{ error }}</p>
    <FormField label="Destino" required>
      <select v-model="f.destino" class="cr-input">
        <option value="proveedor">Proveedor (defecto de fábrica)</option>
        <option value="seguro">Aseguradora</option>
      </select>
    </FormField>
    <FormField v-if="f.destino === 'proveedor'" label="Proveedor" required>
      <ComboBox v-model="f.proveedor_id" :opciones="proveedores" opcion-label="razon_social" opcion-value="id" placeholder="Buscar proveedor…" />
    </FormField>
    <FormField v-else label="Aseguradora" required>
      <input v-model="f.aseguradora" class="cr-input" />
    </FormField>
  </FormModal>
</template>
