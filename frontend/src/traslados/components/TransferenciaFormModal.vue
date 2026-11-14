<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import {
  crearTransferencia,
  itemsDisponiblesTraslado,
  sucursalesActivasTraslado,
} from '@/traslados/services/trasladosApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // Precarga desde otro flujo (p. ej. venta: el vendedor localizó el reloj en otra
  // sucursal vía búsqueda global y quiere iniciar el traslado ya con esos datos):
  // { sucursal_origen_id, sucursal_destino_id, reloj: {id, etiqueta, detalle}, motivo }
  prefill: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'creada'])

const sucursales = ref([])
const guardando = ref(false)
const error = ref('')

const f = reactive({
  sucursal_origen_id: null,
  sucursal_destino_id: null,
  motivo: '',
  enviar_ahora: false,
  relojes: [], // [{id, etiqueta, detalle}]
  piezas: [], // [{id, etiqueta, detalle, stock, cantidad}]
})

const catalogoRelojes = ref([])
const catalogoPiezas = ref([])
const buscarReloj = ref('')
const buscarPieza = ref('')

const destinos = computed(() => sucursales.value.filter((s) => s.id !== f.sucursal_origen_id))
const relojIds = computed(() => new Set(f.relojes.map((r) => r.id)))
const piezaIds = computed(() => new Set(f.piezas.map((p) => p.id)))

// Evita que el watcher de "sucursal_origen_id" (más abajo) limpie las líneas
// precargadas justo después de que reset() las coloca.
let aplicandoPrefill = false

function reset() {
  aplicandoPrefill = true
  Object.assign(f, {
    sucursal_origen_id: props.prefill?.sucursal_origen_id ?? sucursales.value[0]?.id ?? null,
    sucursal_destino_id: props.prefill?.sucursal_destino_id ?? null,
    motivo: props.prefill?.motivo ?? '',
    enviar_ahora: false,
    relojes: props.prefill?.reloj ? [{ ...props.prefill.reloj }] : [],
    piezas: [],
  })
  catalogoRelojes.value = []
  catalogoPiezas.value = []
  error.value = ''
  if (f.sucursal_origen_id) recargarCatalogos()
  nextTick(() => {
    aplicandoPrefill = false
  })
}

onMounted(async () => {
  sucursales.value = await sucursalesActivasTraslado().catch(() => [])
  reset()
})
watch(
  () => props.modelValue,
  (v) => {
    if (v) reset()
  },
)

// Al cambiar el origen, recarga los ítems disponibles ahí.
watch(
  () => f.sucursal_origen_id,
  async () => {
    if (aplicandoPrefill) return
    f.relojes = []
    f.piezas = []
    if (f.sucursal_destino_id === f.sucursal_origen_id) f.sucursal_destino_id = null
    await recargarCatalogos()
  },
)

let tr
watch(buscarReloj, () => {
  clearTimeout(tr)
  tr = setTimeout(() => recargarCatalogos('reloj'), 250)
})
let tp
watch(buscarPieza, () => {
  clearTimeout(tp)
  tp = setTimeout(() => recargarCatalogos('pieza'), 250)
})

async function recargarCatalogos(solo) {
  if (!f.sucursal_origen_id) return
  if (!solo || solo === 'reloj')
    catalogoRelojes.value = await itemsDisponiblesTraslado(f.sucursal_origen_id, 'reloj', buscarReloj.value).catch(() => [])
  if (!solo || solo === 'pieza')
    catalogoPiezas.value = await itemsDisponiblesTraslado(f.sucursal_origen_id, 'pieza', buscarPieza.value).catch(() => [])
}

function toggleReloj(r) {
  if (relojIds.value.has(r.id)) f.relojes = f.relojes.filter((x) => x.id !== r.id)
  else f.relojes.push({ ...r })
}
function agregarPieza(p) {
  if (piezaIds.value.has(p.id)) return
  f.piezas.push({ ...p, cantidad: 1 })
}
function quitarPieza(id) {
  f.piezas = f.piezas.filter((p) => p.id !== id)
}

async function guardar() {
  error.value = ''
  if (!f.sucursal_origen_id || !f.sucursal_destino_id) return (error.value = 'Elige sucursal de origen y destino.')
  if (f.sucursal_origen_id === f.sucursal_destino_id) return (error.value = 'El origen y el destino deben ser distintos.')
  if (f.motivo.trim().length < 3) return (error.value = 'Indica el motivo de la transferencia.')
  if (!f.relojes.length && !f.piezas.length) return (error.value = 'Agrega al menos un reloj o una pieza.')
  for (const p of f.piezas) {
    if (p.cantidad < 1 || p.cantidad > p.stock) return (error.value = `Cantidad inválida para «${p.etiqueta}» (stock ${p.stock}).`)
  }
  guardando.value = true
  try {
    const t = await crearTransferencia({
      sucursal_origen_id: f.sucursal_origen_id,
      sucursal_destino_id: f.sucursal_destino_id,
      motivo: f.motivo.trim(),
      enviar_ahora: f.enviar_ahora,
      lineas: [
        ...f.relojes.map((r) => ({ item_tipo: 'reloj', reloj_id: r.id })),
        ...f.piezas.map((p) => ({ item_tipo: 'pieza', pieza_id: p.id, cantidad_enviada: Number(p.cantidad) })),
      ],
    })
    toast.success(f.enviar_ahora ? `Transferencia #${t.id} enviada` : `Transferencia #${t.id} en preparación`)
    emit('update:modelValue', false)
    emit('creada')
  } catch (e) {
    error.value =
      e.status === 422 ? e.message :
      e.status === 409 ? e.message : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    titulo="Nueva transferencia"
    subtitulo="Mueve relojes y piezas entre sucursales. Los ítems quedan en tránsito hasta que el destino confirme la recepción."
    :guardando="guardando"
    ancho="max-w-3xl"
    :sucio="!!f.motivo || f.relojes.length > 0 || f.piezas.length > 0"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Sucursal de origen" required>
      <ComboBox v-model="f.sucursal_origen_id" :opciones="sucursales" opcion-label="nombre" opcion-value="id" placeholder="Elegir origen…" />
    </FormField>
    <FormField label="Sucursal de destino" required :helper="destinos.length ? '' : 'No hay otra sucursal activa como destino.'">
      <ComboBox v-model="f.sucursal_destino_id" :opciones="destinos" opcion-label="nombre" opcion-value="id" placeholder="Elegir destino…" />
    </FormField>

    <FormField label="Motivo" required wide helper="p. ej. balanceo de stock, exhibición, reparación en otra sede">
      <input v-model="f.motivo" class="cr-input" required />
    </FormField>

    <p class="sm:col-span-2 -mb-1 text-xs text-ink-3">
      Los relojes se trasladan <strong>por unidad</strong> (cada uno con su N.º de serie); las piezas, <strong>por cantidad</strong>.
    </p>

    <!-- relojes -->
    <div class="sm:col-span-2">
      <p class="cr-label mb-2">Relojes (unidades disponibles en el origen)</p>
      <div v-if="f.relojes.length" class="mb-2 flex flex-wrap gap-1.5">
        <span v-for="r in f.relojes" :key="r.id" class="inline-flex items-center gap-1 rounded-full bg-surface-sunk px-2.5 py-1 text-xs">
          {{ r.etiqueta }} · {{ r.detalle }}
          <button type="button" class="text-ink-3 hover:text-bad" @click="toggleReloj(r)"><CrIcon name="x" :size="12" /></button>
        </span>
      </div>
      <input v-model="buscarReloj" class="cr-input mb-1" placeholder="Buscar por serie, marca o referencia…" />
      <ul class="max-h-40 overflow-y-auto rounded-xl border border-hairline">
        <li
          v-for="r in catalogoRelojes"
          :key="r.id"
          class="flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-surface-sunk"
          :class="{ 'text-ink-3': relojIds.has(r.id) }"
          @click="toggleReloj(r)"
        >
          <span>{{ r.etiqueta }} <span class="text-ink-3">· {{ r.detalle }}</span></span>
          <CrIcon v-if="relojIds.has(r.id)" name="check" :size="15" class="text-good" />
        </li>
        <li v-if="!catalogoRelojes.length" class="px-3 py-2 text-sm text-ink-3">Sin relojes disponibles en esta sucursal.</li>
      </ul>
    </div>

    <!-- piezas -->
    <div class="sm:col-span-2">
      <p class="cr-label mb-2">Piezas (con stock en el origen)</p>
      <div v-if="f.piezas.length" class="mb-2 space-y-1.5">
        <div v-for="p in f.piezas" :key="p.id" class="flex items-center gap-2 rounded-lg border border-hairline bg-surface-sunk/40 px-3 py-2 text-sm">
          <span class="flex-1">{{ p.etiqueta }} <span class="text-ink-3">· {{ p.detalle }}</span></span>
          <input v-model.number="p.cantidad" type="number" min="1" :max="p.stock" class="cr-input w-20 py-1 text-center" />
          <span class="text-xs text-ink-3">/ {{ p.stock }}</span>
          <button type="button" class="text-ink-3 hover:text-bad" @click="quitarPieza(p.id)"><CrIcon name="x" :size="14" /></button>
        </div>
      </div>
      <input v-model="buscarPieza" class="cr-input mb-1" placeholder="Buscar pieza por código o descripción…" />
      <ul class="max-h-36 overflow-y-auto rounded-xl border border-hairline">
        <li
          v-for="p in catalogoPiezas"
          :key="p.id"
          class="flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-surface-sunk"
          :class="{ 'text-ink-3': piezaIds.has(p.id) }"
          @click="agregarPieza(p)"
        >
          <span>{{ p.etiqueta }} <span class="text-ink-3">· {{ p.detalle }}</span></span>
          <span class="text-xs text-ink-3">stock {{ p.stock }}</span>
        </li>
        <li v-if="!catalogoPiezas.length" class="px-3 py-2 text-sm text-ink-3">Sin piezas con stock en esta sucursal.</li>
      </ul>
    </div>

    <label class="flex items-center gap-2 text-sm sm:col-span-2">
      <input v-model="f.enviar_ahora" type="checkbox" /> Enviar ahora (marca los ítems en tránsito de inmediato)
    </label>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
