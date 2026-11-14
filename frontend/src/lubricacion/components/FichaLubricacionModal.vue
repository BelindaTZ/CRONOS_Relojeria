<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { listarProductosMoebius, setFichaLubricacion } from '@/lubricacion/services/lubricacionApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  calibre: { type: Object, required: true },
  ficha: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'guardado'])

const f = reactive({ notas_generales: '', puntos: [] })
const productos = ref([])
const guardando = ref(false)
const error = ref('')

onMounted(async () => {
  productos.value = await listarProductosMoebius().catch(() => [])
})
watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    error.value = ''
    f.notas_generales = props.ficha?.notas_generales || ''
    f.puntos = (props.ficha?.puntos || []).map((p) => ({
      nombre: p.nombre, producto_moebius_codigo: p.producto_recomendado || '', notas: p.notas || '',
    }))
  },
)

const agregar = () => f.puntos.push({ nombre: '', producto_moebius_codigo: '', notas: '' })
const quitar = (i) => f.puntos.splice(i, 1)

async function guardar() {
  error.value = ''
  if (f.puntos.some((p) => !p.nombre.trim())) return (error.value = 'Cada punto necesita un nombre.')
  guardando.value = true
  try {
    await setFichaLubricacion(props.calibre.id, {
      notas_generales: f.notas_generales.trim() || null,
      puntos: f.puntos.map((p) => ({
        nombre: p.nombre.trim(),
        producto_moebius_codigo: p.producto_moebius_codigo || null,
        notas: p.notas.trim() || null,
      })),
    })
    toast.success(`Ficha de ${props.calibre.codigo} guardada`)
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
    :titulo="`Ficha de lubricación · ${calibre.codigo}`"
    subtitulo="Los puntos y el producto recomendado se ofrecen al técnico cuando registra la lubricación en una OT de este calibre."
    :guardando="guardando"
    ancho="max-w-3xl"
    :sucio="true"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Notas generales" wide>
      <textarea v-model="f.notas_generales" rows="2" class="cr-input"></textarea>
    </FormField>

    <div class="sm:col-span-2">
      <div class="mb-2 flex items-center justify-between">
        <span class="text-sm font-medium text-ink">Puntos de lubricación</span>
        <button type="button" class="cr-btn cr-btn-ghost text-xs" @click="agregar"><CrIcon name="plus" :size="13" /> Añadir punto</button>
      </div>
      <p v-if="!f.puntos.length" class="rounded-md bg-surface-sunk px-3 py-2 text-xs text-ink-3">Aún sin puntos.</p>
      <div v-for="(p, i) in f.puntos" :key="i" class="mb-2 grid gap-2 rounded-lg border border-hairline p-3 sm:grid-cols-3">
        <FormField label="Nombre del punto" required>
          <input v-model="p.nombre" class="cr-input" placeholder="Rubí de escape…" />
        </FormField>
        <FormField label="Producto recomendado">
          <select v-model="p.producto_moebius_codigo" class="cr-input">
            <option value="">Sin recomendar</option>
            <option v-for="pr in productos" :key="pr.id" :value="pr.codigo">{{ pr.codigo }}</option>
          </select>
        </FormField>
        <FormField label="Notas">
          <input v-model="p.notas" class="cr-input" />
        </FormField>
        <button type="button" class="text-xs text-bad sm:col-span-3" @click="quitar(i)">Quitar punto</button>
      </div>
    </div>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
