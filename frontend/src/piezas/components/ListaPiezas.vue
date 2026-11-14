<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { inactivarPieza, listarPiezas, valorPiezas } from '@/piezas/services/piezasApi'
import PiezaFormModal from './PiezaFormModal.vue'
import MovimientoModal from './MovimientoModal.vue'

const router = useRouter()
const session = useSessionStore()

const columns = [
  { key: 'codigo', label: 'Código' },
  { key: 'descripcion', label: 'Descripción' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'unidad_medida', label: 'Unidad' },
  { key: 'stock_total', label: 'Stock', align: 'right' },
  { key: 'stock_minimo', label: 'Mínimo', align: 'right' },
  { key: 'perecedera', label: 'Perecedera' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const soloBajoMinimo = ref(false)
const page = ref(1)
const valor = ref(null)

const modalForm = ref({ abierto: false, pieza: null })
const modalMov = ref({ abierto: false, pieza: null })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [res, val] = await Promise.all([
      listarPiezas({ q: q.value || undefined, bajo_minimo: soloBajoMinimo.value || undefined, page: page.value }),
      valorPiezas().catch(() => null),
    ])
    rows.value = res.items
    total.value = res.total
    valor.value = val
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
let t
watch([q, soloBajoMinimo], () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 250)
})
watch(page, cargar)

const kpis = computed(() => {
  const bajo = rows.value.filter((p) => p.bajo_minimo).length
  const per = rows.value.filter((p) => p.perecedera).length
  return [
    { label: 'Referencias', value: String(valor.value?.referencias ?? total.value) },
    { label: 'Bajo mínimo (en esta página)', value: String(bajo) },
    { label: 'Perecederas (en esta página)', value: String(per) },
    {
      label: 'Valor del stock a precio',
      value: valor.value ? `$ ${Number(valor.value.a_precio_venta).toLocaleString()}` : '—',
      gold: true,
    },
  ]
})

const acciones = (p) => [
  { label: 'Ver ficha', icon: 'chevron-right', onClick: () => router.push({ name: 'pieza-ficha', params: { id: p.id } }) },
  { label: 'Editar', icon: 'edit', onClick: () => (modalForm.value = { abierto: true, pieza: p }) },
  { label: 'Registrar movimiento', icon: 'boxes', onClick: () => (modalMov.value = { abierto: true, pieza: p }) },
  { label: 'Inactivar', icon: 'ban', danger: true, hidden: !p.activo, onClick: () => inactivar(p) },
]

async function inactivar(p) {
  const ok = await confirm({
    title: `Inactivar «${p.codigo}»`,
    message: 'La pieza no se elimina; queda inactiva y sale de los selectores. Su stock, lotes y movimientos se conservan.',
    confirmLabel: 'Inactivar',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await inactivarPieza(p.id)
    toast.success(`«${p.codigo}» inactivada`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Inventario"
      titulo="Piezas y repuestos"
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Código, descripción, calibre o proveedor…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay piezas registradas"
      empty-hint="Registra repuestos e insumos; su stock alimenta las órdenes de trabajo y las alertas de reposición."
      empty-icon="boxes"
      @retry="cargar"
      @row-click="(p) => router.push({ name: 'pieza-ficha', params: { id: p.id } })"
    >
      <template #actions>
        <RouterLink :to="{ name: 'piezas-lotes' }" class="cr-btn cr-btn-ghost">Lotes y caducidad</RouterLink>
        <button v-if="!session.esGerencia" class="cr-btn cr-btn-primary" @click="modalForm = { abierto: true, pieza: null }">Agregar pieza</button>
      </template>
      <template #toolbar>
        <label class="flex items-center gap-2 text-sm text-ink-2">
          <input v-model="soloBajoMinimo" type="checkbox" /> Solo bajo mínimo
        </label>
      </template>

      <template #cell-descripcion="{ row }">
        <span :class="{ 'text-ink-3 line-through': !row.activo }">{{ row.descripcion }}</span>
        <span v-if="row.marca_compatible" class="block text-xs text-ink-3">compatible: {{ row.marca_compatible }}</span>
      </template>
      <template #cell-unidad_medida="{ row }"><span class="text-ink-2">{{ row.unidad_medida || 'unidad' }}</span></template>
      <template #cell-tipo="{ row }">
        <Pill :tone="row.tipo === 'original' ? 'info' : 'neutral'" :label="row.tipo === 'original' ? 'original' : 'no original'" />
      </template>
      <template #cell-stock_total="{ row }">
        <span class="tabular-nums" :class="{ 'font-semibold text-bad': row.bajo_minimo }">{{ row.stock_total }}</span>
      </template>
      <template #cell-perecedera="{ row }">
        <CrIcon v-if="row.perecedera" name="clock" :size="15" class="text-warn" />
        <span v-else class="text-ink-3">—</span>
      </template>
    </WorkPanel>

    <PiezaFormModal v-model="modalForm.abierto" :pieza="modalForm.pieza" @guardada="cargar" />
    <MovimientoModal v-if="modalMov.pieza" v-model="modalMov.abierto" :pieza="modalMov.pieza" @registrado="cargar" />
  </div>
</template>
