<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { listarSucursales } from '@/sucursales'
import { listarLotesCaducidad } from '@/piezas/services/piezasApi'

const router = useRouter()
const LOTE_TONO = { vigente: 'good', proximo_vencer: 'warn', vencido: 'bad' }

const columns = [
  { key: 'pieza', label: 'Pieza' },
  { key: 'numero_lote', label: 'Lote' },
  { key: 'sucursal_id', label: 'Sucursal' },
  { key: 'fecha_caducidad', label: 'Caducidad' },
  { key: 'dias_restantes', label: 'Días', align: 'right' },
  { key: 'cantidad', label: 'Cantidad', align: 'right' },
  { key: 'estado', label: 'Estado' },
]

const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')
const filtroEstado = ref('')
const filtroSucursal = ref('')
const sucursales = ref([])

const sucursalNombre = (id) => sucursales.value.find((s) => s.id === id)?.nombre ?? `#${id}`

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await listarLotesCaducidad({
      estado: filtroEstado.value || undefined,
      sucursal_id: filtroSucursal.value || undefined,
    })
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
watch([filtroEstado, filtroSucursal], cargar)

const kpis = computed(() => {
  const c = (e) => rows.value.filter((r) => r.estado === e).length
  return [
    { label: 'Vencidos', value: String(c('vencido')) },
    { label: 'Próximos a vencer', value: String(c('proximo_vencer')) },
    { label: 'Vigentes', value: String(c('vigente')) },
  ]
})

const acciones = (r) => [
  { label: 'Ver pieza', icon: 'chevron-right', onClick: () => router.push({ name: 'pieza-ficha', params: { id: r.pieza_id } }) },
  { label: 'Dar de baja por merma (disponible con Mermas · feature 011)', icon: 'ban', danger: true, disabled: true, onClick: () => {} },
]
</script>

<template>
  <WorkPanel
    eyebrow="Inventario · Piezas"
    titulo="Lotes y caducidad"
    sub="Insumos perecederos. El consumo descuenta primero el lote que vence antes (FEFO)."
    :columns="columns"
    :rows="rows"
    :total="rows.length"
    :loading="loading"
    :error="errorMsg"
    :page-size="rows.length || 1"
    :kpis="kpis"
    :row-actions="acciones"
    empty-title="Sin lotes de insumos perecederos"
    empty-hint="Los lotes aparecen al ingresar stock de una pieza marcada como perecedera."
    empty-icon="clock"
    @retry="cargar"
  >
    <template #actions>
      <RouterLink :to="{ name: 'piezas' }" class="cr-btn cr-btn-ghost">Piezas</RouterLink>
      <RouterLink :to="{ name: 'alertas-stock' }" class="cr-btn cr-btn-ghost">Alertas de stock</RouterLink>
    </template>
    <template #toolbar>
      <select v-model="filtroEstado" class="cr-input max-w-[12rem]">
        <option value="">Todos los estados</option>
        <option value="vigente">Vigente</option>
        <option value="proximo_vencer">Próximo a vencer</option>
        <option value="vencido">Vencido</option>
      </select>
      <select v-model="filtroSucursal" class="cr-input max-w-[12rem]">
        <option value="">Todas las sucursales</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
    </template>

    <template #cell-pieza="{ row }">
      <span class="font-medium text-ink">{{ row.pieza_codigo }}</span>
      <span class="text-ink-3"> · {{ row.pieza_descripcion }}</span>
    </template>
    <template #cell-sucursal_id="{ row }">{{ sucursalNombre(row.sucursal_id) }}</template>
    <template #cell-fecha_caducidad="{ row }"><span class="tabular-nums">{{ row.fecha_caducidad }}</span></template>
    <template #cell-dias_restantes="{ row }">
      <span class="tabular-nums" :class="{ 'font-semibold text-bad': row.dias_restantes < 0 }">{{ row.dias_restantes }}</span>
    </template>
    <template #cell-estado="{ row }"><Pill :tone="LOTE_TONO[row.estado] || 'neutral'" :label="row.estado.replace(/_/g, ' ')" /></template>
  </WorkPanel>
</template>
