<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import Pill from '@/shared/ui/Pill.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { getBalance } from '@/contabilidad/services/contabilidadApi'

const periodo = ref('')
const bal = ref(null)
const loading = ref(true)
const errorMsg = ref('')

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    bal.value = await getBalance({ periodo: periodo.value || undefined })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
watch(periodo, cargar)

const kpis = computed(() => bal.value ? [
  { label: 'Total debe', value: dinero(bal.value.total_debe) },
  { label: 'Total haber', value: dinero(bal.value.total_haber) },
  { label: 'Cuadrado', value: bal.value.cuadrado ? 'Sí' : 'No', gold: bal.value.cuadrado },
] : [])
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => (bal.value?.filas || []).map((f) => ({ cuenta: `${f.cuenta_codigo} — ${f.cuenta_nombre}`, debe: f.debe, haber: f.haber })),
    totalFilas: bal.value?.filas?.length || 0,
    imprimirPdf: () => window.print(),
  }),
)
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <PageHeader eyebrow="Contabilidad" titulo="Balance de comprobación" sub="Σ debe por cuenta debe igualar Σ haber, en todo momento.">
      <template #acciones>
        <RouterLink :to="{ name: 'libro-diario' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Libro diario</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <input v-model="periodo" class="cr-input mb-4 max-w-[10rem]" placeholder="AAAA-MM o id" />

    <p v-if="errorMsg" class="text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <template v-else-if="!loading && bal">
      <KpiStrip :items="kpis" />
      <div v-if="!bal.filas.length" class="cr-card mt-4 p-8 text-center text-ink-3">Sin movimientos para el periodo.</div>
      <div v-else class="cr-card mt-4 overflow-hidden p-0">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-table-head-border bg-surface-head text-left">
              <th class="px-4 py-2 font-medium">Cuenta</th>
              <th class="px-4 py-2 text-right font-medium">Debe</th>
              <th class="px-4 py-2 text-right font-medium">Haber</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in bal.filas" :key="f.cuenta_codigo" class="border-b border-hairline-soft">
              <td class="px-4 py-2">{{ f.cuenta_codigo }} — {{ f.cuenta_nombre }}</td>
              <td class="px-4 py-2 text-right tabular-nums">{{ dinero(f.debe) }}</td>
              <td class="px-4 py-2 text-right tabular-nums">{{ dinero(f.haber) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
