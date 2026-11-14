<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import { listarVentas } from '@/ventas/services/ventasApi'

const router = useRouter()
const session = useSessionStore()

const TONO = { borrador: 'neutral', confirmada: 'good', anulada: 'bad' }
const columns = [
  { key: 'numero', label: 'Venta' },
  { key: 'cliente', label: 'Cliente' },
  { key: 'sucursal', label: 'Sucursal' },
  { key: 'fecha', label: 'Fecha' },
  { key: 'total', label: 'Total', align: 'right' },
  { key: 'estado', label: 'Estado' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const page = ref(1)
const q = ref('')
const fEstado = ref('')
const fSucursal = ref('')
const sucursales = ref([])

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarVentas({
      q: q.value || undefined,
      estado: fEstado.value || undefined,
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
  sucursales.value = await listarSucursales().then((r) => r.items).catch(() => [])
  cargar()
})
let t
watch([q, fEstado, fSucursal], () => { clearTimeout(t); page.value = 1; t = setTimeout(cargar, 250) })
watch(page, cargar)

const kpis = computed(() => {
  const conf = rows.value.filter((v) => v.estado === 'confirmada')
  const borr = rows.value.filter((v) => v.estado === 'borrador').length
  const suma = conf.reduce((s, v) => s + Number(v.total || 0), 0)
  return [
    { label: 'Ventas (esta página)', value: String(rows.value.length) },
    { label: 'En borrador', value: String(borr) },
    { label: 'Confirmadas', value: String(conf.length) },
    { label: 'Facturado (página)', value: suma.toLocaleString(undefined, { minimumFractionDigits: 2 }), gold: true },
  ]
})

const acciones = (v) => [
  { label: 'Abrir', icon: 'chevron-right', onClick: () => router.push({ name: 'venta-ficha', params: { id: v.id } }) },
]
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Ventas"
      titulo="Ventas"
      sub="Órdenes de venta de relojes y piezas sueltas. Estados: borrador → confirmada → anulada. Al confirmar se descuenta stock y se generan el comprobante y el certificado."
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
      empty-title="Aún no hay ventas registradas"
      empty-hint="Registra una venta con el cliente, las unidades y los medios de pago."
      empty-icon="tag"
      @retry="cargar"
      @row-click="(v) => router.push({ name: 'venta-ficha', params: { id: v.id } })"
    >
      <template #actions>
        <RouterLink :to="{ name: 'ventas-dia' }" class="cr-btn cr-btn-ghost">Ventas del día</RouterLink>
        <RouterLink :to="{ name: 'cuentas-por-cobrar' }" class="cr-btn cr-btn-ghost">Cuentas por cobrar</RouterLink>
        <RouterLink v-if="!session.esGerencia" :to="{ name: 'venta-nueva' }" class="cr-btn cr-btn-primary">Nueva venta</RouterLink>
      </template>
      <template #toolbar>
        <select v-model="fEstado" class="cr-input max-w-[11rem]">
          <option value="">Todos los estados</option>
          <option value="borrador">Borrador</option>
          <option value="confirmada">Confirmada</option>
          <option value="anulada">Anulada</option>
        </select>
        <select v-model="fSucursal" class="cr-input max-w-[11rem]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </template>

      <template #cell-numero="{ row }">
        <span class="serif text-ink">{{ row.numero_factura || row.numero }}</span>
        <span v-if="row.numero_factura" class="ml-1 text-xs text-ink-3">{{ row.numero }}</span>
      </template>
      <template #cell-cliente="{ row }">
        {{ row.cliente_nombre }}
        <span class="ml-1 text-xs text-ink-3">{{ row.cliente_afiliado }}</span>
      </template>
      <template #cell-sucursal="{ row }">{{ row.sucursal_nombre }}</template>
      <template #cell-fecha="{ row }"><span class="tabular-nums">{{ new Date(row.fecha).toLocaleDateString() }}</span></template>
      <template #cell-total="{ row }">
        <span class="tabular-nums">{{ dinero(row.total) }}</span>
        <span v-if="row.saldo && Number(row.saldo) > 0" class="ml-1 text-xs text-warn">saldo {{ dinero(row.saldo) }}</span>
      </template>
      <template #cell-estado="{ row }"><Pill :tone="TONO[row.estado] || 'neutral'" :label="row.estado" /></template>
    </WorkPanel>
  </div>
</template>
