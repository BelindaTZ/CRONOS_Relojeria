<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarSucursales } from '@/sucursales'
import { getEstadoResultados } from '@/contabilidad/services/contabilidadApi'

const periodo = ref('')
const fSucursal = ref('')
const sucursales = ref([])
const er = ref(null)
const loading = ref(true)

async function cargar() {
  loading.value = true
  er.value = await getEstadoResultados({ periodo: periodo.value || undefined, sucursal_id: fSucursal.value || undefined }).catch(() => null)
  loading.value = false
}
onMounted(async () => {
  sucursales.value = await listarSucursales().then((r) => r.items).catch(() => [])
  cargar()
})
watch([periodo, fSucursal], cargar)

const kpis = computed(() => er.value ? [
  { label: 'Ingresos', value: dinero(er.value.ingresos) },
  { label: 'Costos', value: dinero(er.value.costos) },
  { label: 'Gastos', value: dinero(er.value.gastos) },
  { label: 'Utilidad neta', value: dinero(er.value.utilidad_neta), gold: true },
] : [])
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => (er.value?.detalle || []).map((f) => ({ cuenta: `${f.cuenta_codigo} — ${f.cuenta_nombre}`, tipo: f.tipo, debe: f.debe, haber: f.haber })),
    totalFilas: er.value?.detalle?.length || 0,
    imprimirPdf: () => window.print(),
  }),
)
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <PageHeader eyebrow="Contabilidad" titulo="Estado de resultados" sub="Ingresos por ventas y servicios, menos costos y gastos del periodo.">
      <template #acciones>
        <RouterLink :to="{ name: 'libro-diario' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Libro diario</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap gap-3">
      <input v-model="periodo" class="cr-input max-w-[10rem]" placeholder="AAAA-MM o id" />
      <select v-model="fSucursal" class="cr-input max-w-[12rem]">
        <option value="">Todas las sucursales</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
    </div>

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <template v-else-if="er">
      <KpiStrip :items="kpis" />
      <div v-if="er.detalle.length" class="cr-card mt-4 overflow-hidden p-0">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-table-head-border bg-surface-head text-left">
              <th class="px-4 py-2 font-medium">Cuenta</th>
              <th class="px-4 py-2 font-medium">Tipo</th>
              <th class="px-4 py-2 text-right font-medium">Debe</th>
              <th class="px-4 py-2 text-right font-medium">Haber</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in er.detalle" :key="f.cuenta_codigo" class="border-b border-hairline-soft">
              <td class="px-4 py-2">{{ f.cuenta_codigo }} — {{ f.cuenta_nombre }}</td>
              <td class="px-4 py-2 text-ink-3">{{ f.tipo }}</td>
              <td class="px-4 py-2 text-right tabular-nums">{{ dinero(f.debe) }}</td>
              <td class="px-4 py-2 text-right tabular-nums">{{ dinero(f.haber) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
