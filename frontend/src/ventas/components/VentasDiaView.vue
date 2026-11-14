<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarSucursales } from '@/sucursales'
import { getVentasDia, listarVentas } from '@/ventas/services/ventasApi'

const fecha = ref(new Date().toISOString().slice(0, 10))
const fSucursal = ref('')
const sucursales = ref([])
const resumen = ref(null)
const detalle = ref([])
const loading = ref(false)
const errorMsg = ref('')

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    resumen.value = await getVentasDia({ fecha: fecha.value, sucursal_id: fSucursal.value || undefined })
    const res = await listarVentas({
      estado: 'confirmada', sucursal_id: fSucursal.value || undefined,
      desde: fecha.value, hasta: fecha.value, page: 1, size: 100,
    })
    detalle.value = res.items
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
watch([fecha, fSucursal], cargar)

const kpis = computed(() => [
  { label: 'Ventas del día', value: String(resumen.value?.ventas ?? 0) },
  { label: 'Total facturado', value: dinero(resumen.value?.total) },
  ...(resumen.value?.margen != null ? [{ label: 'Margen del día', value: dinero(resumen.value.margen), gold: true }] : []),
])
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => detalle.value.map((v) => ({ venta: v.numero, cliente: v.cliente_nombre, total: v.total, saldo: v.saldo })),
    totalFilas: detalle.value.length,
    imprimirPdf: () => window.print(),
  }),
)
const dinero = (n) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: 2 }))
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Ventas"
      titulo="Ventas del día"
      sub="Consulta operativa: total y margen del día por sucursal. El margen solo lo ven los roles administrativos. El análisis por marca/modelo/periodo es de Reportes (013)."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'ventas' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Ventas</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-center gap-3">
      <input v-model="fecha" type="date" class="cr-input max-w-[11rem]" />
      <select v-model="fSucursal" class="cr-input max-w-[12rem]">
        <option value="">Todas las sucursales</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
    </div>

    <KpiStrip :items="kpis" />

    <p v-if="errorMsg" class="my-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-else-if="loading" class="my-4 text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!detalle.length" class="cr-card mt-4 p-8 text-center text-ink-3">Sin ventas confirmadas ese día.</p>

    <ul v-else class="mt-4 cr-card divide-y divide-hairline-soft p-0">
      <li v-for="v in detalle" :key="v.id" class="flex flex-wrap items-center justify-between gap-2 px-6 py-3">
        <RouterLink :to="{ name: 'venta-ficha', params: { id: v.id } }" class="serif text-ink hover:text-gold-strong">{{ v.numero }}</RouterLink>
        <span class="flex-1 text-sm text-ink-2">{{ v.cliente_nombre }}</span>
        <span class="tabular-nums">{{ dinero(v.total) }}</span>
      </li>
    </ul>
  </div>
</template>
