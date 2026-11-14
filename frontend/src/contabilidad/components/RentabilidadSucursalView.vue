<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarSucursales } from '@/sucursales'
import { getRentabilidadSucursal } from '@/contabilidad/services/contabilidadApi'

const sucursales = ref([])
const sucursalId = ref(null)
const desde = ref(mesActual().desde)
const hasta = ref(mesActual().hasta)
const datos = ref(null)
const loading = ref(true)

function mesActual() {
  const hoy = new Date()
  const d = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
  return { desde: d.toISOString().slice(0, 10), hasta: hoy.toISOString().slice(0, 10) }
}

async function cargar() {
  if (!sucursalId.value) return
  loading.value = true
  datos.value = await getRentabilidadSucursal({ sucursal_id: sucursalId.value, desde: desde.value, hasta: hasta.value }).catch(() => null)
  loading.value = false
}
onMounted(async () => {
  sucursales.value = await listarSucursales().then((r) => r.items).catch(() => [])
  sucursalId.value = sucursales.value[0]?.id || null
  cargar()
})
watch([sucursalId, desde, hasta], cargar)

const kpis = computed(() => datos.value ? [
  { label: 'Ingresos', value: dinero(datos.value.ingresos) },
  { label: 'Costos', value: dinero(datos.value.costos) },
  { label: 'Gastos de sucursal', value: dinero(datos.value.gastos) },
  { label: 'Utilidad operativa', value: dinero(datos.value.utilidad), gold: true },
] : [])
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => (datos.value ? [{ ingresos: datos.value.ingresos, costos: datos.value.costos, gastos: datos.value.gastos, utilidad: datos.value.utilidad }] : []),
    totalFilas: datos.value ? 1 : 0,
    imprimirPdf: () => window.print(),
  }),
)
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Contabilidad"
      titulo="Rentabilidad por sucursal"
      sub="Versión operativa: ingresos y costos de ventas y órdenes de trabajo entregadas, menos gastos imputados a la sucursal, en el periodo elegido."
    >
      <template #acciones>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <select v-model="sucursalId" class="cr-input max-w-[14rem]">
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
      <label class="text-xs text-ink-3">Desde
        <input v-model="desde" type="date" class="cr-input mt-1 block" />
      </label>
      <label class="text-xs text-ink-3">Hasta
        <input v-model="hasta" type="date" class="cr-input mt-1 block" />
      </label>
    </div>

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <KpiStrip v-else-if="datos" :items="kpis" />
    <p v-else class="cr-card p-8 text-center text-ink-3">Sin datos para el periodo seleccionado.</p>
  </div>
</template>
