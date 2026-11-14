<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { atenderCita } from '@/citas/services/citasApi'

const router = useRouter()

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  cita: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'atendida'])

const f = reactive({ tiene_tx: 'no', venta_id: '', orden_trabajo_id: '' })
const guardando = ref(false)
const error = ref('')

const esCompra = () => props.cita.motivo === 'compra'
const tipoTx = () => (esCompra() ? 'venta' : 'orden de trabajo')

watch(
  () => props.modelValue,
  (v) => { if (v) { Object.assign(f, { tiene_tx: 'no', venta_id: '', orden_trabajo_id: '' }); error.value = '' } },
)

async function atender() {
  error.value = ''
  const datos = {}
  if (f.tiene_tx === 'si') {
    if (esCompra()) {
      if (!f.venta_id) return (error.value = 'Indica el N.º de la venta.')
      datos.venta_id = Number(f.venta_id)
    } else {
      if (!f.orden_trabajo_id) return (error.value = 'Indica el N.º de la orden de trabajo.')
      datos.orden_trabajo_id = Number(f.orden_trabajo_id)
    }
  }
  guardando.value = true
  try {
    const r = await atenderCita(props.cita.id, datos)
    emit('update:modelValue', false)
    emit('atendida')
    if (r.accion?.tipo === 'crear_venta') {
      toast.success('Cita atendida. Abriendo la venta con el cliente ya cargado…')
      router.push({ name: 'venta-nueva', query: { cliente_id: r.accion.cliente_id, cita_id: r.accion.cita_id } })
    } else if (r.accion?.tipo === 'crear_ot') {
      toast.success('Cita atendida. Abriendo la orden de trabajo con el cliente ya cargado…')
      router.push({
        name: 'ordenes-trabajo',
        query: { nueva: '1', cliente_id: r.accion.cliente_id, cita_id: r.accion.cita_id },
      })
    } else {
      toast.success('Cita atendida y vinculada.')
    }
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
    :titulo="`Atender la cita de ${cita.cliente_nombre}`"
    :subtitulo="`Motivo: ${cita.motivo === 'compra' ? 'compra' : cita.motivo === 'consulta' ? 'consulta' : 'servicio técnico'}`"
    :guardando="guardando"
    guardar-label="Marcar como atendida"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="atender"
  >
    <template v-if="cita.motivo === 'consulta'">
      <p class="sm:col-span-2 text-sm text-ink-2">
        Una consulta no genera venta ni orden de trabajo. Al confirmar, la cita queda como <strong>atendida</strong>.
      </p>
    </template>
    <template v-else>
      <div class="sm:col-span-2 space-y-2">
        <label class="flex items-center gap-2 text-sm">
          <input v-model="f.tiene_tx" type="radio" value="no" />
          Todavía no hay {{ tipoTx() }} — se creará después (la cita queda vinculable)
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="f.tiene_tx" type="radio" value="si" />
          Ya existe la {{ tipoTx() }} generada
        </label>
      </div>
      <FormField v-if="f.tiene_tx === 'si' && cita.motivo === 'compra'" label="N.º de venta" wide>
        <input v-model="f.venta_id" type="number" min="1" class="cr-input" />
      </FormField>
      <FormField v-else-if="f.tiene_tx === 'si'" label="N.º de orden de trabajo" wide>
        <input v-model="f.orden_trabajo_id" type="number" min="1" class="cr-input" />
      </FormField>
      <p v-if="f.tiene_tx === 'no'" class="sm:col-span-2 flex items-start gap-2 text-xs text-ink-3">
        <CrIcon name="info" :size="13" class="mt-0.5" />
        Al confirmar se abrirá directamente {{ esCompra() ? 'la nueva venta' : 'la nueva orden de trabajo' }} con el cliente ya cargado, lista para completar.
      </p>
    </template>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
