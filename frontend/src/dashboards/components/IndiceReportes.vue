<script setup>
/**
 * Índice unificado de reportes (§4.11.1 simples + §4.11.2 complejos), filtrado
 * por permiso real de quien lo abre (backend ya filtra; aquí solo se pinta).
 */
import { onMounted, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { getIndiceReportes } from '@/dashboards/services/dashboardsApi'

const cargando = ref(true)
const simples = ref([])
const complejos = ref([])

const ICONO_TIPO = { barras: 'boxes', pastel: 'tag', lineas: 'history', tabla: 'layers' }

onMounted(async () => {
  try {
    const r = await getIndiceReportes()
    simples.value = r.simples
    complejos.value = r.complejos
  } finally {
    cargando.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader eyebrow="Reportes" titulo="Índice de reportes" sub="Operativos de consulta libre y analíticos de §4.11.2, según tu rol." />

    <p v-if="cargando" class="text-sm text-ink-3">Cargando…</p>
    <template v-else>
      <section v-if="simples.length" class="mb-8">
        <h2 class="cr-label mb-3">Reportes operativos</h2>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <RouterLink
            v-for="r in simples" :key="r.ruta + r.titulo" :to="r.ruta"
            class="cr-card flex items-center gap-3 p-4 transition hover:border-hairline-strong hover:shadow-md"
          >
            <CrIcon :name="r.icono" :size="18" class="shrink-0 text-ink-3" />
            <span class="text-sm text-ink">{{ r.titulo }}</span>
          </RouterLink>
        </div>
      </section>

      <section v-if="complejos.length">
        <h2 class="cr-label mb-3">Reportes analíticos (§4.11.2)</h2>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <RouterLink
            v-for="r in complejos" :key="r.slug" :to="{ name: 'reporte-analitico', params: { slug: r.slug } }"
            class="cr-card flex items-center gap-3 p-4 transition hover:border-hairline-strong hover:shadow-md"
          >
            <CrIcon :name="ICONO_TIPO[r.tipo_grafico] || 'layers'" :size="18" class="shrink-0 text-gold" />
            <span class="text-sm text-ink">{{ r.titulo }}</span>
          </RouterLink>
        </div>
      </section>

      <p v-if="!simples.length && !complejos.length" class="rounded-lg bg-surface-sunk px-4 py-6 text-center text-sm text-ink-3">
        No hay reportes disponibles para tu rol.
      </p>
    </template>
  </div>
</template>
