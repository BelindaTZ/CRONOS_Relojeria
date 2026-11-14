<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import { crearOrden, listarProveedores } from '@/proveedores/services/proveedoresApi'
import LineasPedidoEditor from './LineasPedidoEditor.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  prellenado: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'creada'])

const proveedores = ref([])
const sucursales = ref([])
const guardando = ref(false)
const error = ref('')
const editor = ref(null)

const f = reactive({ proveedor_id: null, sucursal_destino_id: null, fecha_pactada: '', urgente: false })
const inicial = ref(null)

onMounted(async () => {
  const [pv, sc] = await Promise.all([
    listarProveedores({ estado: 'activo', page: 1 }),
    listarSucursales(),
  ])
  proveedores.value = pv.items
  sucursales.value = sc.items
  aplicarPrellenado()
})

function aplicarPrellenado() {
  error.value = ''
  if (!props.prellenado) {
    f.proveedor_id = null
    f.sucursal_destino_id = null
    f.fecha_pactada = ''
    f.urgente = false
    inicial.value = null
    return
  }
  f.proveedor_id = props.prellenado.proveedor_id ?? null
  f.urgente = !!props.prellenado.urgente
  inicial.value = props.prellenado.lineas?.length ? props.prellenado.lineas : null
}
watch(() => props.prellenado, aplicarPrellenado, { deep: true })
watch(() => props.modelValue, (v) => { if (v) aplicarPrellenado() })

async function guardar() {
  error.value = ''
  if (!f.proveedor_id || !f.sucursal_destino_id) return (error.value = 'Elige proveedor y sucursal destino.')
  let lineas
  try {
    lineas = editor.value.construirLineas()
  } catch (e) {
    return (error.value = e.message)
  }
  guardando.value = true
  try {
    await crearOrden({
      proveedor_id: f.proveedor_id,
      sucursal_destino_id: f.sucursal_destino_id,
      fecha_pactada: f.fecha_pactada || null,
      urgente: f.urgente,
      lineas,
    })
    toast.success('Orden creada en borrador — emítela para enviarla al proveedor')
    emit('update:modelValue', false)
    emit('creada')
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
    titulo="Nueva orden de compra"
    subtitulo="Pides modelo y cantidad. El costo lo confirma el proveedor: si no lo sabes, déjalo vacío y lo registras al recibir la factura."
    :guardando="guardando"
    ancho="max-w-3xl"
    :sucio="editor?.hayContenido?.() || false"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Proveedor" required>
      <ComboBox v-model="f.proveedor_id" :opciones="proveedores" opcion-label="razon_social" opcion-value="id" placeholder="Elegir proveedor…" />
    </FormField>
    <FormField label="Sucursal destino" required>
      <ComboBox v-model="f.sucursal_destino_id" :opciones="sucursales" opcion-label="nombre" opcion-value="id" placeholder="Elegir sucursal…" />
    </FormField>
    <FormField label="Fecha de entrega pactada" helper="Opcional; habilita la regla de cancelación">
      <input v-model="f.fecha_pactada" type="date" class="cr-input" />
    </FormField>
    <label class="flex items-center gap-2 pt-6 text-sm">
      <input v-model="f.urgente" type="checkbox" /> Urgente
      <span class="text-xs text-ink-3">(p. ej. pieza faltante que detuvo una reparación)</span>
    </label>

    <LineasPedidoEditor v-if="modelValue" ref="editor" :inicial="inicial" />

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
