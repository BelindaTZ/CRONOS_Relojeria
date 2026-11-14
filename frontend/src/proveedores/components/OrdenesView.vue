<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm, prompt } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import OrdenFormModal from './OrdenFormModal.vue'
import RecepcionModal from './RecepcionModal.vue'
import {
  cancelarOrden,
  confirmarOrden,
  emitirOrden,
  listarOrdenes,
} from '@/proveedores/services/proveedoresApi'

const route = useRoute()
const session = useSessionStore()
const columns = [
  { key: 'id', label: 'Orden' },
  { key: 'proveedor_id', label: 'Proveedor' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'lineas', label: 'Ítems' },
  { key: 'fecha_pactada', label: 'Pactada' },
  { key: 'importe_a_pagar', label: 'Importe', align: 'right' },
  { key: 'estado', label: 'Estado' },
]
const TONO = { borrador: 'neutral', emitida: 'warn', confirmada: 'info', parcial: 'warn', recibida: 'good', cancelada: 'bad' }

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const filtroEstado = ref('')
const page = ref(1)
const kpiCounts = ref({ borrador: 0, transito: 0, recibida: 0 })

const modalCrear = ref(false)
const prellenado = ref(null)
const recepcion = ref({ abierto: false, orden: null })
const detalle = ref(null)

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarOrdenes({
      estado: filtroEstado.value || undefined,
      page: page.value,
    })
    rows.value = res.items
    total.value = res.total
    // KPIs: consultas ligeras por estado
    const [b, e, c, p2] = await Promise.all([
      listarOrdenes({ estado: 'borrador', page: 1 }),
      listarOrdenes({ estado: 'emitida', page: 1 }),
      listarOrdenes({ estado: 'confirmada', page: 1 }),
      listarOrdenes({ estado: 'parcial', page: 1 }),
    ])
    const r = await listarOrdenes({ estado: 'recibida', page: 1 })
    kpiCounts.value = { borrador: b.total, transito: e.total + c.total + p2.total, recibida: r.total }
  } catch (err) {
    errorMsg.value = err.message
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  if (route.query.prellenar) {
    try {
      prellenado.value = JSON.parse(route.query.prellenar)
      modalCrear.value = true
    } catch {
      /* ignore */
    }
  }
  cargar()
})
watch([filtroEstado], () => {
  page.value = 1
  cargar()
})
watch(page, cargar)

const kpis = computed(() => [
  { label: 'Borradores', value: String(kpiCounts.value.borrador) },
  { label: 'En tránsito', value: String(kpiCounts.value.transito), sub: 'emitidas / confirmadas / parciales' },
  { label: 'Recibidas (total)', value: String(kpiCounts.value.recibida), gold: true },
])

async function emitir(o) {
  if (!(await confirm({ title: `Emitir orden #${o.id}`, message: 'La orden queda registrada como enviada al proveedor.', confirmLabel: 'Emitir' }))) return
  try {
    await emitirOrden(o.id)
    toast.success(`Orden #${o.id} emitida`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}
async function confirmarProv(o) {
  if (!(await confirm({ title: `Confirmar aceptación · orden #${o.id}`, message: 'Registra que el proveedor ACEPTÓ el pedido (acordado por otro canal). Solo así se podrá recibir.', confirmLabel: 'El proveedor aceptó' }))) return
  try {
    await confirmarOrden(o.id)
    toast.success(`Orden #${o.id} confirmada`)
    cargar()
  } catch (e) {
    toast.error(e.status === 403 ? 'Requiere rol elevado (Gerencia General / Gerente de Sucursal).' : e.message)
  }
}
async function cancelar(o) {
  const motivo = await prompt({
    title: `Cancelar orden #${o.id}`,
    message: 'Se enviará un aviso al proveedor. No se puede cancelar si faltan menos de 24 h para la fecha pactada.',
    label: 'Motivo de la cancelación',
  })
  if (!motivo) return
  try {
    await cancelarOrden(o.id, motivo)
    toast.success(`Orden #${o.id} cancelada · proveedor notificado`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}
function recibir(o) {
  recepcion.value = { abierto: true, orden: o }
}

const acciones = (o) => [
  { label: 'Ver detalle', icon: 'chevron-right', onClick: () => (detalle.value = o) },
  { label: 'Emitir', icon: 'send', hidden: o.estado !== 'borrador', onClick: () => emitir(o) },
  { label: 'Confirmar (proveedor aceptó)', icon: 'check', hidden: o.estado !== 'emitida', onClick: () => confirmarProv(o) },
  { label: 'Recibir', icon: 'package-check', hidden: !['confirmada', 'parcial'].includes(o.estado), onClick: () => recibir(o) },
  { label: 'Cancelar', icon: 'ban', danger: true, hidden: ['recibida', 'cancelada'].includes(o.estado), onClick: () => cancelar(o) },
]
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Abastecimiento"
      titulo="Órdenes de compra"
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Buscar orden…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay órdenes de compra"
      empty-hint="Crea una orden para pedir relojes o piezas a un proveedor."
      empty-icon="inbox"
      @retry="cargar"
      @row-click="(o) => (detalle = o)"
    >
      <template #actions>
        <RouterLink :to="{ name: 'compras-programadas' }" class="cr-btn cr-btn-ghost">Compras programadas</RouterLink>
        <button v-if="!session.esGerencia" class="cr-btn cr-btn-primary" @click="((prellenado = null), (modalCrear = true))">Nueva orden</button>
      </template>
      <template #toolbar>
        <select v-model="filtroEstado" class="cr-input max-w-[12rem]">
          <option value="">Todos los estados</option>
          <option value="borrador">Borrador</option>
          <option value="emitida">Emitida</option>
          <option value="confirmada">Confirmada</option>
          <option value="parcial">Parcial</option>
          <option value="recibida">Recibida</option>
          <option value="cancelada">Cancelada</option>
        </select>
      </template>

      <template #cell-id="{ row }">
        <span class="font-medium text-ink">#{{ row.id }}</span>
        <Pill v-if="row.urgente" tone="bad" label="Urgente" class="ml-1.5" />
      </template>
      <template #cell-lineas="{ row }">
        <span class="text-ink-3">{{ row.lineas.map((l) => `${l.marca ? l.marca + ' ' : ''}${l.item_ref} ${l.cantidad_recibida}/${l.cantidad}`).join(' · ') }}</span>
      </template>
      <template #cell-fecha_pactada="{ row }">{{ row.fecha_pactada || '—' }}</template>
      <template #cell-importe_a_pagar="{ row }">{{ row.importe_a_pagar ?? '—' }}</template>
      <template #cell-estado="{ row }"><Pill :tone="TONO[row.estado] || 'neutral'" :label="row.estado" /></template>
    </WorkPanel>

    <OrdenFormModal v-model="modalCrear" :prellenado="prellenado" @creada="cargar" />
    <RecepcionModal v-model="recepcion.abierto" :orden="recepcion.orden" @recibida="cargar" />

    <!-- detalle -->
    <div v-if="detalle" class="fixed inset-0 z-50 flex min-h-full items-center justify-center overflow-y-auto bg-primary-950/60 p-4 py-10" @click.self="detalle = null">
      <div class="w-full max-w-xl rounded-2xl border border-hairline bg-surface shadow-md">
        <header class="flex items-center justify-between border-b border-hairline px-6 py-4">
          <h2 class="serif text-xl text-ink">Orden #{{ detalle.id }}</h2>
          <button class="rounded-lg p-1.5 text-ink-3 hover:bg-surface-sunk" @click="detalle = null"><CrIcon name="x" :size="18" /></button>
        </header>
        <div class="space-y-3 px-6 py-5 text-sm">
          <div class="flex gap-3">
            <Pill :tone="TONO[detalle.estado] || 'neutral'" :label="detalle.estado" />
            <span class="text-ink-2">{{ detalle.tipo }}</span>
          </div>
          <p><span class="text-ink-3">Proveedor:</span> #{{ detalle.proveedor_id }} · <span class="text-ink-3">Sucursal:</span> #{{ detalle.sucursal_destino_id }}</p>
          <p><span class="text-ink-3">Fecha pactada:</span> {{ detalle.fecha_pactada || '—' }} · <span class="text-ink-3">Condiciones:</span> {{ detalle.condiciones_pago || '—' }}</p>
          <table class="w-full">
            <thead><tr class="border-b border-hairline text-left text-[0.7rem] uppercase text-ink-2"><th class="py-2">Ítem</th><th class="py-2">Cant.</th><th class="py-2 text-right">Costo u.</th></tr></thead>
            <tbody class="divide-y divide-hairline-soft">
              <tr v-for="l in detalle.lineas" :key="l.id">
                <td class="py-2">
                  <span class="font-medium">{{ l.marca ? l.marca + ' ' : '' }}{{ l.item_ref }}</span>
                  <span v-if="l.calibre_codigo" class="text-ink-3"> · cal. {{ l.calibre_codigo }}</span>
                  <span v-if="l.anio" class="text-ink-3"> · {{ l.anio }}</span>
                  <span v-if="l.item_tipo === 'pieza' && l.marca_compatible" class="text-ink-3"> · compat. {{ l.marca_compatible }}</span>
                  <span v-if="l.item_tipo === 'pieza' && l.unidad_medida && l.unidad_medida !== 'unidad'" class="text-ink-3"> · {{ l.unidad_medida }}</span>
                  <span v-if="l.numero_serie" class="text-ink-3"> · N.º {{ l.numero_serie }}</span>
                  <span v-if="l.descripcion" class="block text-xs text-ink-3">{{ l.descripcion }}</span>
                  <span v-if="l.observaciones" class="block text-xs text-ink-3">Obs.: {{ l.observaciones }}</span>
                  <span v-if="l.es_perecedero" class="text-xs text-warn">· perecedero</span>
                </td>
                <td class="py-2 tabular-nums">{{ l.cantidad_recibida }}/{{ l.cantidad }}</td>
                <td class="py-2 text-right tabular-nums">
                  <span v-if="l.costo_unitario_real != null">{{ l.costo_unitario_real }}</span>
                  <span v-else-if="l.costo_unitario != null" class="text-ink-3">{{ l.costo_unitario }} <span class="text-[0.65rem]">est.</span></span>
                  <span v-else class="text-ink-3">—</span>
                </td>
              </tr>
            </tbody>
          </table>
          <p class="text-right text-sm">
            Importe {{ detalle.lineas.some((l) => l.costo_unitario_real != null) ? '' : 'estimado ' }}a pagar:
            <span class="font-medium tabular-nums">{{ detalle.importe_a_pagar ?? '—' }}</span>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
