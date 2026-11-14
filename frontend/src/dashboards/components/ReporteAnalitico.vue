<script setup>
/**
 * Reporte analítico de §4.11.2 (feature 013): filtros reactivos (sin botón
 * "Buscar"), gráfico `vue-echarts` según `tipo_grafico`, tabla de detalle y
 * exportación en 3 formatos.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarSucursales } from '@/sucursales'
import { listarMarcasReloj } from '@/configuracion'
import { listarTecnicos } from '@/tecnicos'
import { getReporteAnalitico } from '@/dashboards/services/dashboardsApi'
import GraficoEcharts from '@/dashboards/components/GraficoEcharts.vue'
import TablaDetalle from '@/dashboards/components/TablaDetalle.vue'
import SelloFrescura from '@/dashboards/components/SelloFrescura.vue'

const route = useRoute()
const router = useRouter()

function mesActual() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const filtros = reactive({
  periodo: typeof route.query.periodo === 'string' ? route.query.periodo : mesActual(),
  sucursal_id: route.query.sucursal_id ? Number(route.query.sucursal_id) : null,
  marca: route.query.marca || '',
  tecnico_id: route.query.tecnico_id ? Number(route.query.tecnico_id) : null,
})

const cargando = ref(true)
const dato = ref(null)
const sucursales = ref([])
const marcas = ref([])
const tecnicos = ref([])

onMounted(async () => {
  ;[sucursales.value, marcas.value, tecnicos.value] = await Promise.all([
    listarSucursales().then((r) => r.items).catch(() => []),
    listarMarcasReloj(true).then((r) => r.items || r).catch(() => []),
    listarTecnicos({ page: 1, size: 100 }).then((r) => r.items).catch(() => []),
  ])
  cargar()
})

async function cargar() {
  cargando.value = true
  try {
    const params = {}
    if (filtros.periodo) params.periodo = filtros.periodo
    if (filtros.sucursal_id) params.sucursal_id = filtros.sucursal_id
    if (filtros.marca) params.marca = filtros.marca
    if (filtros.tecnico_id) params.tecnico_id = filtros.tecnico_id
    dato.value = await getReporteAnalitico(route.params.slug, params)
  } catch (e) {
    dato.value = { disponible: false, motivo: e.message }
  } finally {
    cargando.value = false
  }
}

watch(() => route.params.slug, () => { cargar() })
let t
function onFiltroChange() {
  clearTimeout(t)
  t = setTimeout(cargar, 200)
}
watch(filtros, onFiltroChange, { deep: true })

const soporta = (f) => dato.value?.filtros_soportados?.includes(f) ?? false

const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => dato.value?.filas || [],
    totalFilas: dato.value?.total_filas || 0,
    imprimirPdf: () => window.print(),
    nombreArchivo: route.params.slug,
  }),
)
</script>

<template>
  <div>
    <PageHeader eyebrow="Reportes" :titulo="dato?.titulo || 'Reporte'" sub="Filtros reactivos — cambian el reporte al instante, sin botón «Buscar».">
      <template #acciones>
        <SelloFrescura />
        <RouterLink :to="{ name: 'reportes-indice' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Reportes</RouterLink>
      </template>
    </PageHeader>

    <div v-if="dato && (soporta('periodo') || soporta('sucursal') || soporta('marca') || soporta('tecnico'))" class="mb-5 flex flex-wrap items-end gap-3">
      <FormField v-if="soporta('periodo')" label="Periodo">
        <input v-model="filtros.periodo" type="month" class="cr-input" />
      </FormField>
      <FormField v-if="soporta('sucursal')" label="Sucursal" class="w-52">
        <ComboBox v-model="filtros.sucursal_id" :opciones="sucursales" opcion-label="nombre" opcion-value="id" placeholder="Todas las tuyas" />
      </FormField>
      <FormField v-if="soporta('marca')" label="Marca" class="w-52">
        <ComboBox v-model="filtros.marca" :opciones="marcas" opcion-label="nombre" opcion-value="nombre" placeholder="Todas" />
      </FormField>
      <FormField v-if="soporta('tecnico')" label="Técnico" class="w-52">
        <ComboBox v-model="filtros.tecnico_id" :opciones="tecnicos" opcion-label="nombre" opcion-value="id" placeholder="Todos" />
      </FormField>
    </div>

    <div v-if="cargando" class="cr-card flex h-64 items-center justify-center text-sm text-ink-3">Cargando…</div>

    <div v-else-if="!dato?.disponible" class="cr-card flex items-center gap-3 p-6 text-ink-2">
      <CrIcon name="alert-circle" :size="20" class="text-warn shrink-0" />
      <div>
        <p class="font-medium text-ink">Datos analíticos no disponibles</p>
        <p class="text-sm">{{ dato?.motivo || 'El warehouse no respondió.' }}</p>
      </div>
    </div>

    <template v-else>
      <section v-if="dato.tipo_grafico !== 'tabla'" class="cr-card mb-5 p-5">
        <GraficoEcharts :tipo="dato.tipo_grafico" :categorias="dato.categorias" :series="dato.series" />
      </section>

      <section class="cr-card p-5">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="serif text-lg text-ink">Detalle</h2>
          <div class="flex gap-1">
            <button v-for="o in exportOpts" :key="o.formato" type="button" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">
              {{ o.etiqueta }}
            </button>
          </div>
        </div>
        <TablaDetalle :filas="dato.filas" />
      </section>
    </template>
  </div>
</template>
