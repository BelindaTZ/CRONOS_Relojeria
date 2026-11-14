<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import { getParametro } from '@/configuracion'
import { fijarCosto } from '@/tecnicos/services/tecnicosApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  tecnico: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'guardado'])

const f = reactive({ sueldo_mensual: null, vigente_desde: new Date().toISOString().slice(0, 10) })
const guardando = ref(false)
const error = ref('')
const horasEstandar = ref(160)

onMounted(async () => {
  try {
    const p = await getParametro('horas_productivas_estandar_mes')
    if (p?.valor != null) horasEstandar.value = Number(p.valor)
  } catch {
    /* usa el valor por defecto */
  }
})

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    error.value = ''
    f.sueldo_mensual = props.tecnico.costo_vigente?.sueldo_mensual ?? null
    f.vigente_desde = new Date().toISOString().slice(0, 10)
  },
)

const tarifaPreview = computed(() => {
  const s = Number(f.sueldo_mensual)
  if (!s || !horasEstandar.value) return null
  return (s / horasEstandar.value).toFixed(2)
})

async function guardar() {
  error.value = ''
  if (!f.sueldo_mensual || Number(f.sueldo_mensual) < 0) return (error.value = 'Indica el sueldo mensual.')
  guardando.value = true
  try {
    const r = await fijarCosto(props.tecnico.id, {
      sueldo_mensual: Number(f.sueldo_mensual),
      vigente_desde: f.vigente_desde,
    })
    toast.success(`Costo fijado · tarifa ${Number(r.tarifa_hora).toLocaleString()} / h`)
    emit('update:modelValue', false)
    emit('guardado')
  } catch (e) {
    error.value = e.status === 403 ? 'El costo interno solo lo fija el Técnico Jefe o Gerencia General.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="`Costo interno · ${tecnico.nombre}`"
    subtitulo="Sueldo fijo mensual. La tarifa horaria (base del costo de mano de obra de cada orden de trabajo) se deriva de él."
    :guardando="guardando"
    ancho="max-w-lg"
    :sucio="!!f.sueldo_mensual"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Sueldo mensual" required helper="Solo visible para roles administrativos.">
      <input v-model="f.sueldo_mensual" type="number" min="0" step="0.01" class="cr-input" required />
    </FormField>
    <FormField label="Vigente desde" required helper="Cada cambio se guarda como un registro nuevo (historial).">
      <input v-model="f.vigente_desde" type="date" class="cr-input" required />
    </FormField>

    <div class="sm:col-span-2 rounded-xl border border-gold/40 bg-gold-pale px-4 py-3">
      <p class="cr-label mb-0.5">Tarifa horaria derivada</p>
      <p class="serif text-2xl text-gold-strong tabular-nums">
        <span v-if="tarifaPreview">$ {{ Number(tarifaPreview).toLocaleString() }}</span>
        <span v-else class="text-ink-3 text-base">—</span>
        <span class="ml-1 text-sm font-normal text-ink-2">/ hora</span>
      </p>
      <p class="mt-1 text-xs text-ink-2">
        sueldo ÷ {{ horasEstandar }} h productivas estándar al mes (parámetro configurable en Sistema · Parámetros).
      </p>
    </div>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
