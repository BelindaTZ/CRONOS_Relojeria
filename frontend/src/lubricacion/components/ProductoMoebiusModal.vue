<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { toast } from '@/shared/ui/toast'
import { listarPiezas } from '@/piezas'
import { crearProductoMoebius } from '@/lubricacion/services/lubricacionApi'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'guardado'])

const f = reactive({ codigo: '', uso_recomendado: '', pieza_id: null })
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
  (v) => { if (v) { Object.assign(f, { codigo: '', uso_recomendado: '', pieza_id: null }); error.value = '' } },
)

async function guardar() {
  error.value = ''
  if (!f.codigo.trim()) return (error.value = 'El código es obligatorio.')
  guardando.value = true
  try {
    await crearProductoMoebius({
      codigo: f.codigo.trim(),
      uso_recomendado: f.uso_recomendado.trim() || null,
      pieza_id: f.pieza_id || null,
    })
    toast.success('Producto Moebius añadido')
    emit('update:modelValue', false)
    emit('guardado')
  } catch (e) {
    error.value = e.status === 403 ? 'Requiere Técnico Jefe o Gerencia General.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    titulo="Nuevo producto Moebius"
    subtitulo="El código es la referencia real del lubricante. Vincúlalo a la pieza-insumo perecedera en stock si quieres que la lubricación descuente consumo."
    :guardando="guardando"
    ancho="max-w-xl"
    :sucio="!!f.codigo"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Código" required>
      <input v-model="f.codigo" class="cr-input" placeholder="Ej. 9020, D5…" />
    </FormField>
    <FormField label="Uso recomendado" wide>
      <input v-model="f.uso_recomendado" class="cr-input" placeholder="Pivotes de baja carga, paletas del áncora…" />
    </FormField>
    <FormField label="Pieza-insumo en stock" wide helper="Opcional. La pieza debe existir como repuesto perecedero (003).">
      <ComboBox v-model="f.pieza_id" :opciones="piezas" opcion-label="_label" opcion-value="id" placeholder="Sin vincular" />
    </FormField>
    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
