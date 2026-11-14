<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { prompt } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarCanalesCita } from '@/configuracion'
import { listarSucursales } from '@/sucursales'
import { cancelarCita, confirmarCita, listarCitas } from '@/citas/services/citasApi'
import CitaFormModal from './CitaFormModal.vue'
import AtenderModal from './AtenderModal.vue'

const router = useRouter()
const session = useSessionStore()

const columns = [
  { key: 'cliente', label: 'Cliente' },
  { key: 'motivo', label: 'Motivo' },
  { key: 'fecha', label: 'Fecha' },
  { key: 'canal', label: 'Canal' },
  { key: 'sucursal', label: 'Sucursal' },
  { key: 'estado', label: 'Estado' },
]
const TONO = { pendiente: 'neutral', confirmada: 'info', cancelada: 'bad', atendida: 'good' }
const MOTIVO = { compra: 'Compra', servicio_tecnico: 'Servicio técnico', consulta: 'Consulta' }

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const page = ref(1)
const fEstado = ref('')
const fCanal = ref('')
const fSucursal = ref('')
const canales = ref([])
const sucursales = ref([])

const modalForm = ref({ abierto: false, cita: null })
const modalAtender = ref({ abierto: false, cita: null })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarCitas({
      q: q.value || undefined,
      estado: fEstado.value || undefined,
      canal_cita_id: fCanal.value || undefined,
      sucursal_id: fSucursal.value || undefined,
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
  ;[canales.value, sucursales.value] = await Promise.all([
    listarCanalesCita().catch(() => []),
    listarSucursales().then((r) => r.items).catch(() => []),
  ])
  cargar()
})
let t
watch([q, fEstado, fCanal, fSucursal], () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 250)
})
watch(page, cargar)

const kpis = computed(() => {
  const pend = rows.value.filter((c) => c.estado === 'pendiente').length
  const conf = rows.value.filter((c) => c.estado === 'confirmada').length
  return [
    { label: 'Citas (esta página)', value: String(rows.value.length) },
    { label: 'Pendientes', value: String(pend) },
    { label: 'Confirmadas', value: String(conf) },
    { label: 'Total registradas', value: String(total.value), gold: true },
  ]
})

async function confirmar(c) {
  try {
    const r = await confirmarCita(c.id)
    toast.success(r.warning ? `Cita agendada en firme · ${r.warning}` : 'Cita agendada en firme')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

async function cancelar(c) {
  const motivo = await prompt({
    title: `Cancelar la cita de ${c.cliente_nombre}`,
    message: 'Queda registrada como cancelada con el motivo.',
    label: 'Motivo de la cancelación',
  })
  if (!motivo) return
  try {
    await cancelarCita(c.id, motivo)
    toast.success('Cita cancelada')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const acciones = (c) => [
  { label: 'Confirmar (agendar en firme)', icon: 'check', hidden: c.estado !== 'pendiente', onClick: () => confirmar(c) },
  { label: 'Atender (el cliente llegó)', icon: 'circle-check', hidden: !['pendiente', 'confirmada'].includes(c.estado), onClick: () => (modalAtender.value = { abierto: true, cita: c }) },
  { label: 'Editar', icon: 'edit', hidden: !['pendiente', 'confirmada'].includes(c.estado), onClick: () => (modalForm.value = { abierto: true, cita: c }) },
  { label: 'Cancelar', icon: 'ban', danger: true, hidden: ['atendida', 'cancelada'].includes(c.estado), onClick: () => cancelar(c) },
]

const fmtFecha = (c) => new Date(c.fecha_confirmada || c.fecha_preferida).toLocaleString()
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Citas"
      titulo="Citas"
      sub="Registro manual de las solicitudes recibidas por correo o presencial. Estados: pendiente → confirmada → atendida (o cancelada). La cita atendida se vincula a su venta u orden de trabajo."
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Cliente por nombre, cédula/RUC, email o N.º de afiliado…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay citas registradas"
      empty-hint="Registra una cita a partir de una solicitud recibida por Gmail o en tienda."
      empty-icon="clock"
      @retry="cargar"
    >
      <template #actions>
        <RouterLink :to="{ name: 'citas-agenda' }" class="cr-btn cr-btn-ghost">Agenda</RouterLink>
        <button v-if="!session.esGerencia" class="cr-btn cr-btn-primary" @click="modalForm = { abierto: true, cita: null }">Nueva cita</button>
      </template>
      <template #toolbar>
        <select v-model="fEstado" class="cr-input max-w-[11rem]">
          <option value="">Todos los estados</option>
          <option value="pendiente">Pendiente</option>
          <option value="confirmada">Confirmada</option>
          <option value="atendida">Atendida</option>
          <option value="cancelada">Cancelada</option>
        </select>
        <select v-model="fCanal" class="cr-input max-w-[11rem]">
          <option value="">Todos los canales</option>
          <option v-for="c in canales" :key="c.id" :value="c.id">{{ c.nombre }}</option>
        </select>
        <select v-model="fSucursal" class="cr-input max-w-[11rem]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </template>

      <template #cell-cliente="{ row }">
        <span class="font-medium text-ink">{{ row.cliente_nombre }}</span>
        <span class="ml-1 text-xs text-ink-3">{{ row.cliente_afiliado }}</span>
      </template>
      <template #cell-motivo="{ row }">{{ MOTIVO[row.motivo] || row.motivo }}</template>
      <template #cell-fecha="{ row }">
        <span class="tabular-nums">{{ fmtFecha(row) }}</span>
        <span v-if="row.estado === 'confirmada'" class="ml-1 text-xs text-good">confirmada</span>
      </template>
      <template #cell-canal="{ row }">{{ row.canal_nombre }}</template>
      <template #cell-sucursal="{ row }">{{ row.sucursal_nombre }}</template>
      <template #cell-estado="{ row }">
        <Pill :tone="TONO[row.estado] || 'neutral'" :label="row.estado" />
        <span v-if="row.venta_id || row.orden_trabajo_id" class="ml-1 text-xs text-ink-3">
          → {{ row.orden_trabajo_id ? `OT #${row.orden_trabajo_id}` : `venta #${row.venta_id}` }}
        </span>
      </template>
    </WorkPanel>

    <CitaFormModal v-model="modalForm.abierto" :cita="modalForm.cita" @guardado="cargar" />
    <AtenderModal v-if="modalAtender.cita" v-model="modalAtender.abierto" :cita="modalAtender.cita" @atendida="cargar" />
  </div>
</template>
