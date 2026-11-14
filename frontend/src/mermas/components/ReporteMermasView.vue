<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarSucursales } from '@/sucursales'
import { getReporteMermas } from '@/mermas/services/mermasApi'

const CAUSAS = {
  dano_tienda: 'Daño en tienda', dano_transito: 'Daño en tránsito', robo_perdida: 'Robo / pérdida',
  defecto_fabrica: 'Defecto de fábrica', dano_servicio: 'Daño en servicio', insumo_caducado: 'Insumo caducado',
}

const desde = ref('')
const hasta = ref('')
const sucursalId = ref('')
const sucursales = ref([])
const filas = ref([])
const loading = ref(true)

async function cargar() {
  loading.value = true
  filas.value = await getReporteMermas({
    desde: desde.value || undefined, hasta: hasta.value || undefined, sucursal_id: sucursalId.value || undefined,
  }).catch(() => [])
  loading.value = false
}
onMounted(async () => {
  sucursales.value = await listarSucursales().then((r) => r.items).catch(() => [])
  cargar()
})
watch([desde, hasta, sucursalId], cargar)

const kpis = computed(() => {
  const frecuencia = filas.value.reduce((s, f) => s + f.frecuencia, 0)
  const monto = filas.value.reduce((s, f) => s + Number(f.monto_total || 0), 0)
  return [
    { label: 'Mermas en el rango', value: String(frecuencia) },
    { label: 'Monto total', value: dinero(monto), gold: true },
  ]
})
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => filas.value.map((f) => ({ causa: CAUSAS[f.causa] || f.causa, frecuencia: f.frecuencia, monto_total: f.monto_total })),
    totalFilas: filas.value.length,
    imprimirPdf: () => window.print(),
  }),
)
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <PageHeader eyebrow="Mermas" titulo="Reporte de mermas y pérdidas" sub="Agrupado por causa, con monto y frecuencia (§4.11.2 — versión operativa).">
      <template #acciones>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <label class="text-xs text-ink-3">Desde<input v-model="desde" type="date" class="cr-input mt-1 block" /></label>
      <label class="text-xs text-ink-3">Hasta<input v-model="hasta" type="date" class="cr-input mt-1 block" /></label>
      <select v-if="sucursales.length > 1" v-model="sucursalId" class="cr-input max-w-[12rem]">
        <option value="">Todas las sucursales</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
    </div>

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <template v-else>
      <KpiStrip :items="kpis" />
      <div v-if="filas.length" class="cr-card mt-4 overflow-hidden p-0">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-table-head-border bg-surface-head text-left">
              <th class="px-4 py-2 font-medium">Causa</th>
              <th class="px-4 py-2 text-right font-medium">Frecuencia</th>
              <th class="px-4 py-2 text-right font-medium">Monto total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in filas" :key="f.causa" class="border-b border-hairline-soft">
              <td class="px-4 py-2">{{ CAUSAS[f.causa] || f.causa }}</td>
              <td class="px-4 py-2 text-right tabular-nums">{{ f.frecuencia }}</td>
              <td class="px-4 py-2 text-right tabular-nums">{{ dinero(f.monto_total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="cr-card mt-4 p-8 text-center text-ink-3">Sin mermas en el rango elegido.</p>
    </template>
  </div>
</template>
