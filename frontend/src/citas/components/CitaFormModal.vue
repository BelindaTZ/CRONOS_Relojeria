<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { toast } from '@/shared/ui/toast'
import { listarClientes } from '@/clientes'
import { listarCanalesCita } from '@/configuracion'
import { listarSucursales } from '@/sucursales'
import { actualizarCita, crearCita } from '@/citas/services/citasApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  cita: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'guardado'])

const MOTIVOS = [
  { value: 'servicio_tecnico', label: 'Servicio técnico' },
  { value: 'compra', label: 'Compra' },
  { value: 'consulta', label: 'Consulta' },
]

function vacio() {
  return { cliente_id: null, sucursal_id: null, canal_cita_id: null, motivo: 'servicio_tecnico', fecha_preferida: '', observaciones: '' }
}
const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')
const clientes = ref([])
const canales = ref([])
const sucursales = ref([])

onMounted(async () => {
  const [cl, ca, su] = await Promise.all([
    listarClientes({ page: 1, size: 100 }).catch(() => ({ items: [] })),
    listarCanalesCita().catch(() => []),
    listarSucursales().catch(() => ({ items: [] })),
  ])
  clientes.value = cl.items.map((x) => ({ ...x, _label: `${x.nombre} · ${x.numero_afiliado}` }))
  canales.value = ca
  sucursales.value = su.items
})

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    error.value = ''
    if (props.cita) {
      Object.assign(f, {
        cliente_id: props.cita.cliente_id,
        sucursal_id: props.cita.sucursal_id,
        canal_cita_id: props.cita.canal_cita_id,
        motivo: props.cita.motivo,
        fecha_preferida: props.cita.fecha_preferida ? props.cita.fecha_preferida.slice(0, 16) : '',
        observaciones: props.cita.observaciones ?? '',
      })
    } else {
      Object.assign(f, vacio())
    }
  },
)

async function guardar() {
  error.value = ''
  if (!props.cita && !f.cliente_id) return (error.value = 'Elige el cliente (debe tener ficha registrada).')
  if (!props.cita && !f.sucursal_id) return (error.value = 'Elige la sucursal.')
  if (!f.canal_cita_id) return (error.value = 'Elige el canal de origen.')
  if (!f.fecha_preferida) return (error.value = 'Indica la fecha y hora preferida.')
  guardando.value = true
  try {
    const payload = {
      canal_cita_id: f.canal_cita_id,
      motivo: f.motivo,
      fecha_preferida: new Date(f.fecha_preferida).toISOString(),
      observaciones: f.observaciones.trim() || null,
    }
    if (props.cita) {
      await actualizarCita(props.cita.id, payload)
      toast.success('Cita actualizada')
    } else {
      await crearCita({ ...payload, cliente_id: f.cliente_id, sucursal_id: f.sucursal_id })
      toast.success('Cita registrada en estado pendiente')
    }
    emit('update:modelValue', false)
    emit('guardado')
  } catch (e) {
    error.value = e.field === 'cliente_id' && e.status === 422
      ? 'El cliente no tiene ficha registrada. Créala primero en Clientes.'
      : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="cita ? 'Editar cita' : 'Nueva cita'"
    subtitulo="El sistema no lee correos: registra aquí la solicitud recibida indicando el canal."
    :guardando="guardando"
    ancho="max-w-2xl"
    :sucio="!!f.canal_cita_id"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Cliente" required :helper="cita ? 'El cliente no se cambia en la edición.' : 'Debe tener ficha en Clientes.'">
      <ComboBox v-if="!cita" v-model="f.cliente_id" :opciones="clientes" opcion-label="_label" opcion-value="id" placeholder="Buscar cliente…" />
      <input v-else class="cr-input" :value="cita.cliente_nombre" disabled />
    </FormField>
    <FormField label="Sucursal" required>
      <ComboBox v-if="!cita" v-model="f.sucursal_id" :opciones="sucursales" opcion-label="nombre" opcion-value="id" placeholder="Elegir sucursal…" />
      <input v-else class="cr-input" :value="cita.sucursal_nombre" disabled />
    </FormField>

    <FormField label="Motivo" required>
      <select v-model="f.motivo" class="cr-input">
        <option v-for="m in MOTIVOS" :key="m.value" :value="m.value">{{ m.label }}</option>
      </select>
    </FormField>
    <FormField label="Canal de origen" required>
      <select v-model="f.canal_cita_id" class="cr-input">
        <option :value="null">— elegir —</option>
        <option v-for="c in canales" :key="c.id" :value="c.id">{{ c.nombre }}</option>
      </select>
    </FormField>

    <FormField label="Fecha y hora preferida" required wide>
      <input v-model="f.fecha_preferida" type="datetime-local" class="cr-input" required />
    </FormField>

    <FormField label="Observaciones" wide>
      <textarea v-model="f.observaciones" rows="2" class="cr-input"></textarea>
    </FormField>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
