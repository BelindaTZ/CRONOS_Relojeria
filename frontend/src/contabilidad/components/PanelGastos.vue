<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import { listarCategoriasGasto } from '@/configuracion'
import { listarGastos } from '@/contabilidad/services/contabilidadApi'
import GastoFormModal from './GastoFormModal.vue'
import ConfirmarGastoModal from './ConfirmarGastoModal.vue'

const session = useSessionStore()

const columns = [
  { key: 'fecha', label: 'Fecha' },
  { key: 'sucursal', label: 'Sucursal' },
  { key: 'categoria', label: 'Categoría' },
  { key: 'contraparte', label: 'Contraparte' },
  { key: 'monto', label: 'Monto', align: 'right' },
  { key: 'estado', label: 'Estado' },
]
const TONO = { pagado: 'good', por_pagar: 'warn' }

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const page = ref(1)
const fSucursal = ref('')
const fCategoria = ref('')
const fEstado = ref('')
const sucursales = ref([])
const categorias = ref([])
const modalNuevo = ref(false)
const modalConfirmar = ref({ abierto: false, gasto: null })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarGastos({
      sucursal_id: fSucursal.value || undefined, categoria_gasto_id: fCategoria.value || undefined,
      estado_pago: fEstado.value || undefined, page: page.value,
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
  ;[sucursales.value, categorias.value] = await Promise.all([
    listarSucursales().then((r) => r.items).catch(() => []),
    listarCategoriasGasto().catch(() => []),
  ])
  cargar()
})
watch([fSucursal, fCategoria, fEstado], () => { page.value = 1; cargar() })
watch(page, cargar)

const kpis = computed(() => {
  const borradores = rows.value.filter((g) => g.estado === 'borrador').length
  const suma = rows.value.filter((g) => g.estado === 'confirmado').reduce((s, g) => s + Number(g.monto || 0), 0)
  return [
    { label: 'Gastos (esta página)', value: String(rows.value.length) },
    { label: 'Pendientes de confirmar', value: String(borradores) },
    { label: 'Total confirmado (página)', value: suma.toLocaleString(undefined, { minimumFractionDigits: 2 }), gold: true },
  ]
})

const acciones = (g) => [
  { label: 'Confirmar', icon: 'circle-check', hidden: g.estado !== 'borrador' || !session.puede('contable', 'editar'), onClick: () => (modalConfirmar.value = { abierto: true, gasto: g }) },
  { label: 'Ver soporte', icon: 'image', hidden: !g.documento_soporte_url, onClick: () => window.open(g.documento_soporte_url, '_blank', 'noopener') },
]
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Contabilidad"
      titulo="Gastos operativos"
      sub="Registro de gastos por sucursal y categoría (§4.10.1). Pagado ahora genera un movimiento de caja; por pagar, una cuenta por pagar. Solo Gerencia General o Contador registra y confirma."
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:page="page"
      :page-size="20"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay gastos registrados"
      empty-hint="Registra arriendo, luz, agua, sueldos u otros gastos operativos."
      empty-icon="tag"
      @retry="cargar"
    >
      <template #actions>
        <RouterLink :to="{ name: 'gastos-recurrentes' }" class="cr-btn cr-btn-ghost">Recurrentes</RouterLink>
        <button v-if="session.puede('contable', 'crear')" class="cr-btn cr-btn-primary" @click="modalNuevo = true">Registrar gasto</button>
      </template>
      <template #toolbar>
        <select v-model="fSucursal" class="cr-input max-w-[11rem]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
        <select v-model="fCategoria" class="cr-input max-w-[12rem]">
          <option value="">Todas las categorías</option>
          <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
        </select>
        <select v-model="fEstado" class="cr-input max-w-[10rem]">
          <option value="">Pagado / por pagar</option>
          <option value="pagado">Pagado</option>
          <option value="por_pagar">Por pagar</option>
        </select>
      </template>

      <template #cell-fecha="{ row }"><span class="tabular-nums">{{ row.fecha }}</span></template>
      <template #cell-sucursal="{ row }">{{ row.sucursal_nombre }}</template>
      <template #cell-categoria="{ row }">{{ row.categoria_nombre }}</template>
      <template #cell-contraparte="{ row }">{{ row.contraparte_nombre || '—' }}</template>
      <template #cell-monto="{ row }"><span class="tabular-nums">{{ dinero(row.monto) }}</span></template>
      <template #cell-estado="{ row }">
        <Pill v-if="row.estado === 'borrador'" tone="neutral" label="borrador" />
        <Pill v-else :tone="TONO[row.estado_pago] || 'neutral'" :label="row.estado_pago || '—'" />
      </template>
    </WorkPanel>

    <GastoFormModal v-model="modalNuevo" @guardado="cargar" />
    <ConfirmarGastoModal
      v-if="modalConfirmar.gasto"
      v-model="modalConfirmar.abierto"
      :gasto="modalConfirmar.gasto"
      @guardado="cargar"
    />
  </div>
</template>
