<script setup>
/**
 * Horario de atención por sucursal (7 días). Se usa para armar el correo
 * "servicio_listo_retiro" con el horario real de la sucursal (flujo principal, paso 7).
 */
import { reactive, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import { toast } from '@/shared/ui/toast'
import { getHorarioSucursal, setHorarioSucursal } from '@/sucursales/services/sucursalesApi'

const props = defineProps({ modelValue: { type: Boolean, default: false }, sucursal: { type: Object, default: null } })
const emit = defineEmits(['update:modelValue'])

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const estado = reactive({ cargando: false, guardando: false, error: '', dias: [] })

function base() {
  return DIAS.map((_, i) => ({ dia_semana: i, cerrado: false, hora_apertura: '09:00', hora_cierre: '18:00' }))
}

async function cargar() {
  if (!props.sucursal) return
  estado.cargando = true
  estado.error = ''
  try {
    const actual = await getHorarioSucursal(props.sucursal.id)
    const dias = base()
    for (const d of actual) {
      dias[d.dia_semana] = {
        dia_semana: d.dia_semana,
        cerrado: d.cerrado,
        hora_apertura: d.hora_apertura || '09:00',
        hora_cierre: d.hora_cierre || '18:00',
      }
    }
    estado.dias = dias
  } catch (e) {
    estado.error = e.message
    estado.dias = base()
  } finally {
    estado.cargando = false
  }
}

watch(
  () => [props.modelValue, props.sucursal],
  ([abierto]) => {
    if (abierto) cargar()
  },
)

async function guardar() {
  estado.error = ''
  estado.guardando = true
  try {
    await setHorarioSucursal(
      props.sucursal.id,
      estado.dias.map((d) => ({
        dia_semana: d.dia_semana,
        cerrado: d.cerrado,
        hora_apertura: d.cerrado ? null : d.hora_apertura,
        hora_cierre: d.cerrado ? null : d.hora_cierre,
      })),
    )
    toast.success('Horario actualizado')
    emit('update:modelValue', false)
  } catch (e) {
    estado.error = e.status === 422 ? 'Revisa las horas: apertura y cierre son obligatorias salvo que el día esté marcado como cerrado.' : e.message
  } finally {
    estado.guardando = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="`Horario · ${sucursal?.nombre || ''}`"
    subtitulo="Se usa para avisar al cliente cuándo puede pasar a retirar su reloj."
    ancho="max-w-lg"
    :guardando="estado.guardando"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @guardar="guardar"
  >
    <div class="sm:col-span-2">
      <p v-if="estado.cargando" class="text-sm text-ink-3">Cargando…</p>
      <div v-else class="grid gap-2">
        <div v-for="d in estado.dias" :key="d.dia_semana" class="grid grid-cols-[7rem_1fr_auto_1fr] items-center gap-2 rounded-lg border border-hairline px-3 py-2">
          <span class="text-sm text-ink">{{ DIAS[d.dia_semana] }}</span>
          <input v-if="!d.cerrado" v-model="d.hora_apertura" type="time" class="cr-input tabular-nums" />
          <span v-else class="text-xs text-ink-3">—</span>
          <span v-if="!d.cerrado" class="text-xs text-ink-3">a</span>
          <input v-if="!d.cerrado" v-model="d.hora_cierre" type="time" class="cr-input tabular-nums" />
          <label v-if="d.cerrado" class="col-span-3 flex items-center gap-2 text-xs text-ink-3">
            <input v-model="d.cerrado" type="checkbox" /> Cerrado
          </label>
          <label v-else class="col-start-4 justify-self-end text-xs text-ink-3">
            <input v-model="d.cerrado" type="checkbox" /> Cerrado
          </label>
        </div>
      </div>
      <p v-if="estado.error" class="mt-2 text-sm text-bad" role="alert">{{ estado.error }}</p>
    </div>
  </FormModal>
</template>
