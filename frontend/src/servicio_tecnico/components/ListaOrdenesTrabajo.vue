<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import { listarTecnicos } from '@/tecnicos'
import { listarOrdenesTrabajo } from '@/servicio_tecnico/services/servicioTecnicoApi'
import OrdenTrabajoFormModal from './OrdenTrabajoFormModal.vue'

const router = useRouter()
const route = useRoute()
const session = useSessionStore()

const ESTADOS = [
  ['recibido', 'Recibido'],
  ['en_diagnostico', 'En diagnóstico'],
  ['presupuesto', 'Presupuesto'],
  ['en_reparacion', 'En reparación'],
  ['listo', 'Listo'],
  ['entregado', 'Entregado'],
  ['cancelada', 'Cancelada'],
]
const TONO = {
  recibido: 'neutral', en_diagnostico: 'info', presupuesto: 'warn',
  en_reparacion: 'info', listo: 'good', entregado: 'good', cancelada: 'bad',
}
const ETIQ = Object.fromEntries(ESTADOS)

const columns = [
  { key: 'numero', label: 'OT' },
  { key: 'reloj', label: 'Unidad' },
  { key: 'cliente', label: 'Cliente' },
  { key: 'tecnico', label: 'Técnico' },
  { key: 'ingreso', label: 'Ingreso' },
  { key: 'estado', label: 'Estado' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const page = ref(1)
const fEstado = ref('')
const fTecnico = ref('')
const fSucursal = ref('')
const tecnicos = ref([])
const sucursales = ref([])
const modal = ref(false)
const modalPrefill = ref(null)

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarOrdenesTrabajo({
      estado: fEstado.value || undefined,
      tecnico_id: fTecnico.value || undefined,
      sucursal_id: fSucursal.value || undefined,
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
  ;[tecnicos.value, sucursales.value] = await Promise.all([
    listarTecnicos({ page: 1, size: 100 }).then((r) => r.items).catch(() => []),
    listarSucursales().then((r) => r.items).catch(() => []),
  ])
  cargar()
  // Llegada desde "Atender cita" (007): abre directo el formulario prellenado.
  if (route.query.nueva && route.query.cliente_id) {
    modalPrefill.value = {
      cliente_id: Number(route.query.cliente_id),
      cita_id: route.query.cita_id ? Number(route.query.cita_id) : null,
    }
    modal.value = true
    router.replace({ query: {} })
  }
})
let t
watch([q, fEstado, fTecnico, fSucursal], () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 250)
})
watch(page, cargar)

const kpis = computed(() => {
  const abiertas = rows.value.filter((o) => !['entregado', 'cancelada'].includes(o.estado)).length
  const listas = rows.value.filter((o) => o.estado === 'listo').length
  const presu = rows.value.filter((o) => o.estado === 'presupuesto').length
  return [
    { label: 'OT (esta página)', value: String(rows.value.length) },
    { label: 'Abiertas', value: String(abiertas) },
    { label: 'Esperando aprobación', value: String(presu), sub: 'presupuesto sin confirmar' },
    { label: 'Listas para entregar', value: String(listas), gold: true },
  ]
})

const acciones = (o) => [
  { label: 'Abrir ficha', icon: 'chevron-right', onClick: () => ir(o) },
]
const ir = (o) => router.push({ name: 'ot-ficha', params: { id: o.id } })
const fecha = (d) => (d ? new Date(d).toLocaleDateString() : '—')
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Taller"
      titulo="Órdenes de trabajo"
      sub="Servicio técnico: cada unidad que entra al taller abre una OT con trazabilidad por número de serie. Estados: recibido → en diagnóstico → presupuesto → en reparación → listo → entregado."
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Número de serie de la unidad…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay órdenes de trabajo"
      empty-hint="Abre una OT para el reloj que ingresa al taller (por su número de serie)."
      empty-icon="watch"
      @retry="cargar"
      @row-click="ir"
    >
      <template #actions>
        <RouterLink :to="{ name: 'ot-en-curso' }" class="cr-btn cr-btn-ghost">En curso</RouterLink>
        <RouterLink :to="{ name: 'informe-servicios' }" class="cr-btn cr-btn-ghost">Informe de servicios</RouterLink>
        <button v-if="!session.esGerencia" class="cr-btn cr-btn-primary" @click="modalPrefill = null; modal = true">Nueva orden</button>
      </template>
      <template #toolbar>
        <select v-model="fEstado" class="cr-input max-w-[12rem]">
          <option value="">Todos los estados</option>
          <option v-for="[k, l] in ESTADOS" :key="k" :value="k">{{ l }}</option>
        </select>
        <select v-model="fTecnico" class="cr-input max-w-[12rem]">
          <option value="">Todos los técnicos</option>
          <option v-for="t in tecnicos" :key="t.id" :value="t.id">{{ t.nombre }}</option>
        </select>
        <select v-model="fSucursal" class="cr-input max-w-[11rem]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </template>

      <template #cell-numero="{ row }">
        <span class="serif text-ink">{{ row.numero }}</span>
        <span v-if="row.reproceso" class="ml-1 text-xs text-warn">reproceso</span>
      </template>
      <template #cell-reloj="{ row }">
        <span class="font-medium text-ink">{{ row.reloj_marca }} {{ row.reloj_referencia }}</span>
        <span class="ml-1 text-xs text-ink-3 tabular-nums">{{ row.reloj_serie }}</span>
      </template>
      <template #cell-cliente="{ row }">
        {{ row.cliente_nombre }}
        <span class="ml-1 text-xs text-ink-3">{{ row.cliente_afiliado }}</span>
      </template>
      <template #cell-tecnico="{ row }">{{ row.tecnico_nombre || '— sin asignar' }}</template>
      <template #cell-ingreso="{ row }">
        <span class="tabular-nums">{{ fecha(row.fecha_ingreso) }}</span>
        <span v-if="row.fecha_estimada_entrega" class="ml-1 text-xs text-ink-3">→ {{ fecha(row.fecha_estimada_entrega) }}</span>
      </template>
      <template #cell-estado="{ row }">
        <Pill :tone="TONO[row.estado] || 'neutral'" :label="ETIQ[row.estado] || row.estado" />
      </template>
    </WorkPanel>

    <OrdenTrabajoFormModal
      v-model="modal"
      :prefill="modalPrefill"
      @guardado="(id) => router.push({ name: 'ot-ficha', params: { id } })"
    />
  </div>
</template>
