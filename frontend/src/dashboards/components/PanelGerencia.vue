<script setup>
/**
 * Panel principal de Gerencia General (§4.11.3, feature 013): 6 KPIs críticos
 * del periodo, carga asíncrona, sello de frescura, drill-down a flujos reales.
 */
import { onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import KpiCard from '@/dashboards/components/KpiCard.vue'
import SelloFrescura from '@/dashboards/components/SelloFrescura.vue'
import { getPanel } from '@/dashboards/services/dashboardsApi'

function mesActual() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const periodo = ref(mesActual())
const cargando = ref(true)
const disponible = ref(true)
const motivo = ref('')
const kpis = ref([])

async function cargar() {
  cargando.value = true
  try {
    const r = await getPanel({ periodo: periodo.value })
    disponible.value = r.disponible
    motivo.value = r.motivo || ''
    kpis.value = r.kpis || []
  } catch (e) {
    disponible.value = false
    motivo.value = e.message
  } finally {
    cargando.value = false
  }
}

watch(periodo, cargar)
onMounted(cargar)
</script>

<template>
  <div>
    <PageHeader eyebrow="Reportes" titulo="Panel de Gerencia" sub="Los 5-6 indicadores críticos del periodo (§4.11.3).">
      <template #acciones>
        <SelloFrescura />
      </template>
    </PageHeader>

    <div class="mb-5 flex items-center gap-3">
      <label class="cr-label" for="panel-periodo">Periodo</label>
      <input id="panel-periodo" v-model="periodo" type="month" class="cr-input w-44" />
    </div>

    <div v-if="!cargando && !disponible" class="cr-card flex items-center gap-3 p-6 text-ink-2">
      <CrIcon name="alert-circle" :size="20" class="text-warn shrink-0" />
      <div>
        <p class="font-medium text-ink">Datos analíticos no disponibles</p>
        <p class="text-sm">{{ motivo || 'El warehouse no respondió. El resto de la aplicación sigue funcionando con normalidad.' }}</p>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <template v-if="cargando">
        <KpiCard v-for="i in 6" :key="i" cargando />
      </template>
      <template v-else>
        <KpiCard v-for="k in kpis" :key="k.clave" :kpi="k" />
      </template>
    </div>
  </div>
</template>
