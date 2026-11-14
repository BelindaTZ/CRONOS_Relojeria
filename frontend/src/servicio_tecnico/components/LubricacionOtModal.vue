<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import { listarProductosMoebius } from '@/lubricacion'
import { registrarLubricacion } from '@/servicio_tecnico/services/servicioTecnicoApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  ot: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'hecho'])

const f = reactive({ punto_nombre: '', producto_usado_codigo: '' })
const productos = ref([])
const guardando = ref(false)
const error = ref('')

onMounted(async () => {
  productos.value = await listarProductosMoebius().catch(() => [])
})
watch(
  () => props.modelValue,
  (v) => { if (v) { f.punto_nombre = ''; f.producto_usado_codigo = ''; error.value = '' } },
)

async function guardar() {
  error.value = ''
  if (!f.punto_nombre.trim()) return (error.value = 'Indica el punto de lubricación.')
  if (!f.producto_usado_codigo) return (error.value = 'Elige el producto Moebius usado.')
  guardando.value = true
  try {
    const r = await registrarLubricacion(props.ot.id, {
      punto_nombre: f.punto_nombre.trim(),
      producto_usado_codigo: f.producto_usado_codigo,
    })
    toast.success(r.desviacion ? 'Registrado · ⚠ desvío del recomendado' : 'Punto de lubricación registrado')
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
    titulo="Registrar lubricación por punto"
    subtitulo="Se compara contra el producto recomendado en la ficha del calibre. Un producto distinto se registra como desviación, sin bloquear."
    :guardando="guardando"
    ancho="max-w-xl"
    :sucio="!!f.punto_nombre"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Punto de lubricación" wide required helper="Debe coincidir con un punto de la ficha del calibre para comparar con el recomendado.">
      <input v-model="f.punto_nombre" class="cr-input" placeholder="Ej. Rubí de escape, Barrilete…" />
    </FormField>
    <FormField label="Producto Moebius usado" wide required>
      <select v-model="f.producto_usado_codigo" class="cr-input">
        <option value="">Elige…</option>
        <option v-for="p in productos" :key="p.id" :value="p.codigo">{{ p.codigo }} — {{ p.uso_recomendado }}</option>
      </select>
    </FormField>
    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
