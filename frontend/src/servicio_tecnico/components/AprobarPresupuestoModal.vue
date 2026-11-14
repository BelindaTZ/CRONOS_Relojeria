<script setup>
import { reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import { aprobarPresupuesto } from '@/servicio_tecnico/services/servicioTecnicoApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  ot: { type: Object, required: true },
  presupuesto: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'hecho'])

const f = reactive({ confirmado_por: '', medio_confirmacion: 'whatsapp', fecha_estimada_entrega: '', preferencias: {} })
const guardando = ref(false)
const error = ref('')
const dinero = (n) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: 2 }))

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    error.value = ''
    f.confirmado_por = ''
    f.fecha_estimada_entrega = ''
    f.preferencias = {}
    for (const l of props.presupuesto?.lineas || []) f.preferencias[l.id] = l.preferencia_cliente || 'original'
  },
)

async function guardar() {
  error.value = ''
  if (f.confirmado_por.trim().length < 2) return (error.value = 'Indica quién confirmó el presupuesto.')
  if (!f.fecha_estimada_entrega) return (error.value = 'Registra la fecha estimada de entrega.')
  guardando.value = true
  try {
    await aprobarPresupuesto(props.ot.id, {
      confirmado_por: f.confirmado_por.trim(),
      medio_confirmacion: f.medio_confirmacion,
      fecha_estimada_entrega: f.fecha_estimada_entrega,
      preferencias: Object.entries(f.preferencias).map(([linea_id, preferencia]) => ({ linea_id: Number(linea_id), preferencia })),
    })
    toast.success('Presupuesto aprobado · OT en reparación')
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
    titulo="Registrar aprobación del cliente"
    subtitulo="El cliente aprueba por un medio externo (WhatsApp, correo). Aquí se registra el resultado; al guardar se fija la fecha estimada y la OT pasa a «en reparación»."
    :guardando="guardando"
    ancho="max-w-2xl"
    :sucio="!!f.confirmado_por"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Confirmado por" required helper="Nombre de quien aprobó (el cliente, un familiar…).">
      <input v-model="f.confirmado_por" class="cr-input" />
    </FormField>
    <FormField label="Medio de confirmación">
      <select v-model="f.medio_confirmacion" class="cr-input">
        <option value="whatsapp">WhatsApp</option>
        <option value="correo">Correo</option>
        <option value="telefono">Teléfono</option>
        <option value="presencial">Presencial</option>
      </select>
    </FormField>
    <FormField label="Fecha estimada de entrega" wide required>
      <input v-model="f.fecha_estimada_entrega" type="date" class="cr-input" />
    </FormField>

    <div v-if="presupuesto?.lineas?.length" class="sm:col-span-2">
      <p class="mb-1 text-sm font-medium text-ink">Preferencia de piezas del cliente</p>
      <p class="mb-2 text-xs text-ink-3">Por cada pieza: original o no original — nunca ambas a la vez.</p>
      <div v-for="l in presupuesto.lineas" :key="l.id" class="mb-1.5 flex flex-wrap items-center gap-3 rounded-md bg-surface-sunk px-3 py-2 text-sm">
        <span class="flex-1 text-ink-2">
          {{ l.pieza_original }} <span class="text-ink-3">×{{ l.cantidad }}</span>
          <span v-if="l.pieza_no_original" class="text-ink-3"> / {{ l.pieza_no_original }}</span>
        </span>
        <label class="flex items-center gap-1"><input v-model="f.preferencias[l.id]" type="radio" value="original" /> Original · {{ dinero(l.precio_original) }}</label>
        <label v-if="l.pieza_no_original_id" class="flex items-center gap-1">
          <input v-model="f.preferencias[l.id]" type="radio" value="no_original" /> No original · {{ dinero(l.precio_no_original) }}
        </label>
      </div>
    </div>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
