<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm, prompt } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import {
  cancelarTransferencia,
  enviarTransferencia,
  listarDiscrepancias,
  listarTransferencias,
} from '@/traslados/services/trasladosApi'
import TransferenciaFormModal from './TransferenciaFormModal.vue'
import RecepcionTransferenciaModal from './RecepcionTransferenciaModal.vue'
import { MermaFormModal } from '@/mermas'

const session = useSessionStore()

const ESTADO_TONO = {
  en_preparacion: 'neutral',
  en_transito: 'warn',
  recibida: 'good',
  parcial: 'warn',
  cancelada: 'bad',
}
const ESTADO_LABEL = {
  en_preparacion: 'en preparación',
  en_transito: 'en tránsito',
  recibida: 'recibida',
  parcial: 'parcial',
  cancelada: 'cancelada',
}

const columns = [
  { key: 'id', label: 'Transf.' },
  { key: 'ruta', label: 'Origen → Destino' },
  { key: 'lineas', label: 'Ítems' },
  { key: 'estado', label: 'Estado' },
  { key: 'fecha_envio', label: 'Enviada' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const filtroEstado = ref('')
const filtroSucursal = ref('')
const page = ref(1)
const sucursales = ref([])

const modalCrear = ref(false)
const recepcion = ref({ abierto: false, transferencia: null })
const detalle = ref(null)
const discrepancias = ref([])
const modalMerma = ref({ abierto: false, prefill: null, discrepanciaId: null })

function abrirMermaDesdeDiscrepancia(d) {
  modalMerma.value = {
    abierto: true, discrepanciaId: d.id,
    prefill: { ...d.accion_merma, transferencia_id: detalle.value?.id, sucursal_id: detalle.value?.sucursal_destino_id },
  }
}

const sucursalNombre = (id) => sucursales.value.find((s) => s.id === id)?.nombre ?? `#${id}`

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarTransferencias({
      estado: filtroEstado.value || undefined,
      sucursal_id: filtroSucursal.value || undefined,
      numero_serie: q.value || undefined,
      page: page.value,
    })
    rows.value = res.items
    total.value = res.total
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  sucursales.value = (await listarSucursales().catch(() => ({ items: [] }))).items
  cargar()
})
let t
watch([q], () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 300)
})
watch([filtroEstado, filtroSucursal], () => {
  page.value = 1
  cargar()
})
watch(page, cargar)

const kpis = computed(() => {
  const c = (e) => rows.value.filter((r) => r.estado === e).length
  return [
    { label: 'En preparación', value: String(c('en_preparacion')) },
    { label: 'En tránsito', value: String(c('en_transito')) },
    { label: 'Con discrepancia', value: String(c('parcial')) },
    { label: 'Recibidas (página)', value: String(c('recibida')), gold: true },
  ]
})

function resumenLineas(r) {
  const relojes = r.lineas.filter((l) => l.item_tipo === 'reloj').length
  const piezas = r.lineas.filter((l) => l.item_tipo === 'pieza')
  const partes = []
  if (relojes) partes.push(`${relojes} reloj${relojes > 1 ? 'es' : ''}`)
  if (piezas.length) partes.push(`${piezas.reduce((s, l) => s + l.cantidad_enviada, 0)}× pieza`)
  return partes.join(' · ') || '—'
}

async function enviar(r) {
  if (!(await confirm({
    title: `Enviar transferencia #${r.id}`,
    message: 'Los relojes pasan a «en tránsito» y las piezas salen del stock de la sucursal origen. Se registra la fecha y el responsable.',
    confirmLabel: 'Enviar',
  }))) return
  try {
    await enviarTransferencia(r.id)
    toast.success(`Transferencia #${r.id} enviada`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}
async function cancelar(r) {
  const motivo = await prompt({
    title: `Cancelar transferencia #${r.id}`,
    message: 'Los ítems vuelven a estar disponibles en la sucursal origen. Queda auditado.',
    label: 'Motivo de la cancelación',
  })
  if (!motivo) return
  try {
    await cancelarTransferencia(r.id, motivo)
    toast.success(`Transferencia #${r.id} cancelada`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}
function recibir(r) {
  recepcion.value = { abierto: true, transferencia: r }
}
async function verDetalle(r) {
  detalle.value = r
  discrepancias.value = r.tiene_discrepancias ? await listarDiscrepancias(r.id).catch(() => []) : []
}

// Enviar/recibir/cancelar mueven inventario físico (multisucursal:editar) —
// un Vendedor solo puede levantar la solicitud (crear) y ver el estado
// (consultar); la ejecución sigue siendo del Gerente de Sucursal.
const puedeEjecutar = computed(() => session.puede('multisucursal', 'editar'))

const acciones = (r) => [
  { label: 'Ver detalle', icon: 'chevron-right', onClick: () => verDetalle(r) },
  { label: 'Enviar', icon: 'send', hidden: !puedeEjecutar.value || r.estado !== 'en_preparacion', onClick: () => enviar(r) },
  { label: 'Confirmar recepción', icon: 'package-check', hidden: !puedeEjecutar.value || !['en_transito', 'parcial'].includes(r.estado), onClick: () => recibir(r) },
  { label: 'Cancelar', icon: 'ban', danger: true, hidden: !puedeEjecutar.value || !['en_preparacion', 'en_transito'].includes(r.estado), onClick: () => cancelar(r) },
]

const PASOS = ['en_preparacion', 'en_transito', 'recibida']
const pasoIndice = (estado) => (estado === 'cancelada' ? -1 : estado === 'parcial' ? 2 : PASOS.indexOf(estado))
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Multisucursal"
      titulo="Traslados de inventario"
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Número de serie de un reloj incluido…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay transferencias"
      empty-hint="Mueve relojes y piezas entre sucursales. Necesitas al menos dos sucursales activas."
      empty-icon="truck"
      @retry="cargar"
      @row-click="verDetalle"
    >
      <template #actions>
        <button v-if="!session.esGerencia" class="cr-btn cr-btn-primary" @click="modalCrear = true">Nueva transferencia</button>
      </template>
      <template #toolbar>
        <select v-model="filtroEstado" class="cr-input max-w-[12rem]">
          <option value="">Todos los estados</option>
          <option value="en_preparacion">En preparación</option>
          <option value="en_transito">En tránsito</option>
          <option value="recibida">Recibida</option>
          <option value="parcial">Parcial</option>
          <option value="cancelada">Cancelada</option>
        </select>
        <select v-model="filtroSucursal" class="cr-input max-w-[12rem]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </template>

      <template #cell-id="{ row }"><span class="font-medium text-ink">#{{ row.id }}</span></template>
      <template #cell-ruta="{ row }">
        {{ sucursalNombre(row.sucursal_origen_id) }}
        <CrIcon name="chevron-right" :size="13" class="mx-0.5 inline text-ink-3" />
        {{ sucursalNombre(row.sucursal_destino_id) }}
      </template>
      <template #cell-lineas="{ row }"><span class="text-ink-2">{{ resumenLineas(row) }}</span></template>
      <template #cell-estado="{ row }">
        <Pill :tone="ESTADO_TONO[row.estado] || 'neutral'" :label="ESTADO_LABEL[row.estado] || row.estado" />
      </template>
      <template #cell-fecha_envio="{ row }">{{ row.fecha_envio ? new Date(row.fecha_envio).toLocaleDateString() : '—' }}</template>
    </WorkPanel>

    <TransferenciaFormModal v-model="modalCrear" @creada="cargar" />
    <RecepcionTransferenciaModal
      v-if="recepcion.transferencia"
      v-model="recepcion.abierto"
      :transferencia="recepcion.transferencia"
      @recibida="cargar"
    />
    <MermaFormModal
      v-model="modalMerma.abierto" :prefill="modalMerma.prefill" :discrepancia-id="modalMerma.discrepanciaId"
      @guardado="() => { toast.success('Discrepancia derivada a merma'); if (detalle) verDetalle(detalle) }"
    />

    <!-- detalle -->
    <div
      v-if="detalle"
      class="fixed inset-0 z-50 flex min-h-full items-center justify-center overflow-y-auto bg-primary-950/60 p-4 py-10"
      @click.self="detalle = null"
    >
      <div class="w-full max-w-xl rounded-2xl border border-hairline bg-surface shadow-md">
        <header class="flex items-center justify-between border-b border-hairline px-6 py-4">
          <h2 class="serif text-xl text-ink">Transferencia #{{ detalle.id }}</h2>
          <button class="rounded-lg p-1.5 text-ink-3 hover:bg-surface-sunk" @click="detalle = null"><CrIcon name="x" :size="18" /></button>
        </header>
        <div class="space-y-4 px-6 py-5 text-sm">
          <div class="flex items-center gap-3">
            <Pill :tone="ESTADO_TONO[detalle.estado]" :label="ESTADO_LABEL[detalle.estado]" />
            <span class="text-ink-2">{{ sucursalNombre(detalle.sucursal_origen_id) }} → {{ sucursalNombre(detalle.sucursal_destino_id) }}</span>
          </div>
          <p><span class="text-ink-3">Motivo:</span> {{ detalle.motivo }}</p>

          <!-- pasos -->
          <ol v-if="detalle.estado !== 'cancelada'" class="flex items-center gap-2 text-xs">
            <li
              v-for="(p, i) in ['Preparación', 'En tránsito', 'Recibida']"
              :key="p"
              class="flex items-center gap-2"
            >
              <span
                class="grid h-6 w-6 place-items-center rounded-full border text-[0.7rem]"
                :class="i <= pasoIndice(detalle.estado) ? 'border-good bg-good-bg text-good' : 'border-hairline text-ink-3'"
              >{{ i + 1 }}</span>
              <span :class="i <= pasoIndice(detalle.estado) ? 'text-ink' : 'text-ink-3'">{{ p }}</span>
              <CrIcon v-if="i < 2" name="chevron-right" :size="12" class="text-ink-3" />
            </li>
          </ol>
          <p v-else class="text-xs text-bad">Cancelada — {{ detalle.motivo_cancelacion }}</p>

          <div class="text-xs text-ink-3">
            <p v-if="detalle.fecha_envio">Enviada {{ new Date(detalle.fecha_envio).toLocaleString() }}</p>
            <p v-if="detalle.fecha_recepcion">Recibida {{ new Date(detalle.fecha_recepcion).toLocaleString() }}</p>
          </div>

          <table class="w-full">
            <thead>
              <tr class="border-b-2 border-table-head-border bg-surface-head text-left text-[0.7rem] uppercase text-ink-2">
                <th class="px-3 py-2">Ítem</th><th class="px-3 py-2 text-right">Enviada</th><th class="px-3 py-2 text-right">Recibida</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-hairline-soft">
              <tr v-for="l in detalle.lineas" :key="l.id">
                <td class="px-3 py-2">{{ l.etiqueta }}</td>
                <td class="px-3 py-2 text-right tabular-nums">{{ l.cantidad_enviada }}</td>
                <td class="px-3 py-2 text-right tabular-nums" :class="{ 'text-bad': l.cantidad_recibida != null && l.cantidad_recibida < l.cantidad_enviada }">
                  {{ l.cantidad_recibida ?? '—' }}
                </td>
              </tr>
            </tbody>
          </table>

          <div v-if="discrepancias.length" class="rounded-lg bg-warn-bg px-3 py-2 text-xs text-warn">
            <p class="font-semibold">Discrepancias</p>
            <p v-for="d in discrepancias" :key="d.id" class="mt-1">
              {{ d.etiqueta }} — faltan {{ d.cantidad_faltante }}.
              <button
                v-if="!d.resuelta" class="ml-1 text-gold-strong underline decoration-dotted"
                @click="abrirMermaDesdeDiscrepancia(d)"
              >Registrar merma</button>
              <span v-else class="ml-1 text-ink-3">merma #{{ d.merma_id }} registrada</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
