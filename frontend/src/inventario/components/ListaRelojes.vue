<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import { listarRelojes, valorInventario } from '@/inventario/services/inventarioApi'
import RelojFormModal from './RelojFormModal.vue'

const router = useRouter()
const route = useRoute()
const session = useSessionStore()

const DISPONIBILIDAD_TONO = {
  disponible: 'good',
  reservado: 'warn',
  en_transito: 'warn',
  en_servicio: 'info',
  vendido: 'neutral',
  dado_de_baja: 'bad',
}

const columns = [
  { key: 'numero_serie', label: 'N.º serie' },
  { key: 'modelo', label: 'Marca / Referencia' },
  { key: 'calibre_codigo', label: 'Calibre' },
  { key: 'sucursal_actual_id', label: 'Sucursal' },
  { key: 'disponibilidad', label: 'Estado' },
  { key: 'precio_venta', label: 'Precio', align: 'right' },
  { key: 'costo_adquisicion', label: 'Costo', align: 'right' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const filtroSucursal = ref('')
const filtroEstado = ref('disponible')
const page = ref(1)
const sucursales = ref([])
const valor = ref(null)
const modalAlta = ref(false)

const sucursalNombre = (id) => sucursales.value.find((s) => s.id === id)?.nombre ?? (id ? `#${id}` : '—')
const verCostos = computed(() => rows.value.some((r) => r.costos_visibles))

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [res, val] = await Promise.all([
      listarRelojes({
        q: q.value || undefined,
        sucursal_id: filtroSucursal.value || undefined,
        disponibilidad: filtroEstado.value || undefined,
        page: page.value,
      }),
      valorInventario(filtroSucursal.value || undefined).catch(() => null),
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

onMounted(async () => {
  sucursales.value = (await listarSucursales().catch(() => ({ items: [] }))).items
  cargar()
  if (route.query.fichar) {
    modalAlta.value = true
    router.replace({ query: {} })
  }
})

let t
watch([q, filtroSucursal, filtroEstado], () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 250)
})
watch(page, cargar)

const kpis = computed(() => {
  const k = [
    { label: 'Unidades en stock', value: String(valor.value?.unidades ?? '—') },
    {
      label: 'Valor a precio de venta',
      value: valor.value ? `$ ${Number(valor.value.a_precio_venta).toLocaleString()}` : '—',
      gold: true,
    },
  ]
  if (valor.value?.a_costo != null)
    k.push({ label: 'Valor a costo', value: `$ ${Number(valor.value.a_costo).toLocaleString()}` })
  return k
})

const acciones = (r) => [
  { label: 'Ver ficha', icon: 'chevron-right', onClick: () => abrirFicha(r) },
  { label: 'Corregir ficha (rol elevado)', icon: 'edit', onClick: () => abrirFicha(r) },
]
function abrirFicha(r) {
  router.push({ name: 'reloj-ficha', params: { serie: r.numero_serie } })
}
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Inventario"
      titulo="Relojes en inventario"
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="N.º de serie, marca, referencia o calibre…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay relojes en inventario"
      empty-hint="Registra cada unidad con su número de serie al recibir una orden de compra o manualmente."
      empty-icon="watch"
      @retry="cargar"
      @row-click="abrirFicha"
    >
      <template #actions>
        <RouterLink :to="{ name: 'alertas-stock' }" class="cr-btn cr-btn-ghost">Alertas de stock</RouterLink>
        <RouterLink :to="{ name: 'calibres' }" class="cr-btn cr-btn-ghost">Calibres</RouterLink>
        <button v-if="!session.esGerencia" class="cr-btn cr-btn-primary" @click="modalAlta = true">Registrar unidad</button>
      </template>

      <template #toolbar>
        <select v-model="filtroSucursal" class="cr-input max-w-[12rem]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
        <select v-model="filtroEstado" class="cr-input max-w-[11rem]">
          <option value="">Todos los estados</option>
          <option value="disponible">Disponible</option>
          <option value="reservado">Reservado</option>
          <option value="en_transito">En tránsito</option>
          <option value="en_servicio">En servicio</option>
          <option value="vendido">Vendido</option>
          <option value="dado_de_baja">Dado de baja</option>
        </select>
      </template>

      <template #cell-modelo="{ row }">
        <span class="font-medium text-ink">{{ row.marca }}</span>
        <span class="text-ink-3"> · {{ row.referencia }}</span>
      </template>
      <template #cell-calibre_codigo="{ row }">{{ row.calibre_codigo || '—' }}</template>
      <template #cell-sucursal_actual_id="{ row }">{{ sucursalNombre(row.sucursal_actual_id) }}</template>
      <template #cell-disponibilidad="{ row }">
        <Pill :tone="DISPONIBILIDAD_TONO[row.disponibilidad] || 'neutral'" :label="row.disponibilidad.replace(/_/g, ' ')" />
      </template>
      <template #cell-precio_venta="{ row }">{{ row.precio_venta != null ? `$ ${Number(row.precio_venta).toLocaleString()}` : '—' }}</template>
      <template #cell-costo_adquisicion="{ row }">
        <span v-if="row.costos_visibles" class="tabular-nums">{{ row.costo_adquisicion != null ? `$ ${Number(row.costo_adquisicion).toLocaleString()}` : '—' }}</span>
        <span v-else class="text-ink-3">···</span>
      </template>
    </WorkPanel>

    <RelojFormModal v-model="modalAlta" @creado="(serie) => router.push({ name: 'reloj-ficha', params: { serie } })" />
  </div>
</template>
