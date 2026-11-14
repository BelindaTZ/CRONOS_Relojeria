<script setup>
import { computed, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { recibirTransferencia } from '@/traslados/services/trasladosApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  transferencia: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'recibida'])

const guardando = ref(false)
const error = ref('')
const lineas = reactive([])

watch(
  () => props.modelValue,
  (v) => {
    if (!v || !props.transferencia) return
    error.value = ''
    lineas.splice(0, lineas.length)
    for (const l of props.transferencia.lineas) {
      if (l.cantidad_recibida != null) continue // ya recibida en una parcial previa
      lineas.push({
        linea_transferencia_id: l.id,
        etiqueta: l.etiqueta,
        item_tipo: l.item_tipo,
        cantidad_enviada: l.cantidad_enviada,
        cantidad_recibida: l.cantidad_enviada,
        recibido: true,
      })
    }
  },
)

const hayDiscrepancia = computed(() =>
  lineas.some((l) =>
    l.item_tipo === 'reloj' ? !l.recibido : Number(l.cantidad_recibida) < l.cantidad_enviada,
  ),
)

async function guardar() {
  error.value = ''
  guardando.value = true
  try {
    const r = await recibirTransferencia(props.transferencia.id, {
      lineas: lineas.map((l) => ({
        linea_transferencia_id: l.linea_transferencia_id,
        cantidad_recibida: l.item_tipo === 'reloj' ? (l.recibido ? 1 : 0) : Number(l.cantidad_recibida),
      })),
    })
    toast.success(r.estado === 'parcial' ? `Transferencia #${r.id} recibida con discrepancias` : `Transferencia #${r.id} recibida`)
    emit('update:modelValue', false)
    emit('recibida')
  } catch (e) {
    error.value = e.status === 409 ? 'La transferencia ya fue recibida.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="`Confirmar recepción · transferencia #${transferencia?.id}`"
    subtitulo="Al confirmar, el inventario se actualiza automáticamente en ambas sucursales."
    :guardando="guardando"
    ancho="max-w-xl"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <div class="sm:col-span-2">
      <ul class="divide-y divide-hairline-soft rounded-xl border border-hairline">
        <li v-for="l in lineas" :key="l.linea_transferencia_id" class="flex items-center gap-3 px-3 py-2.5 text-sm">
          <span class="flex-1">{{ l.etiqueta }}</span>
          <template v-if="l.item_tipo === 'reloj'">
            <label class="flex items-center gap-1.5 text-xs">
              <input v-model="l.recibido" type="checkbox" /> recibido
            </label>
          </template>
          <template v-else>
            <input v-model.number="l.cantidad_recibida" type="number" min="0" :max="l.cantidad_enviada" class="cr-input w-20 py-1 text-center" />
            <span class="text-xs text-ink-3">/ {{ l.cantidad_enviada }}</span>
          </template>
        </li>
        <li v-if="!lineas.length" class="px-3 py-3 text-sm text-ink-3">No hay líneas pendientes de recepción.</li>
      </ul>
      <p v-if="hayDiscrepancia" class="mt-3 flex items-start gap-2 rounded-lg bg-warn-bg px-3 py-2 text-xs text-warn">
        <CrIcon name="alert-triangle" :size="14" class="mt-px shrink-0" />
        Algunas cantidades no coinciden con lo enviado. Se registrará una discrepancia que podrás derivar a merma (Mermas · feature 011).
      </p>
    </div>
    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
