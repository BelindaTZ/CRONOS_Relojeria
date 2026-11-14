<script setup>
/**
 * Tarjeta individual de KPI del panel de Gerencia (013) — nunca un bloque
 * fundido (Principio XI, feature 000: "los KPIs son tarjetas individuales").
 * Carga asíncrona: mientras `cargando`, muestra un skeleton propio — el resto
 * del panel no espera a este KPI (research 013-D2).
 */
import { useRouter } from 'vue-router'
import CrIcon from '@/shared/ui/CrIcon.vue'

const props = defineProps({
  kpi: { type: Object, default: null },
  cargando: { type: Boolean, default: false },
})
const router = useRouter()

function dinero(n) {
  return Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}
function valorTexto(k) {
  if (k.valor === null || k.valor === undefined) return '—'
  return k.unidad === 'USD' ? `$${dinero(k.valor)}` : `${dinero(k.valor)} ${k.unidad || ''}`.trim()
}
function irADrillDown() {
  const d = props.kpi?.drill_down
  if (!d) return
  router.push({ path: d.ruta, query: d.filtros || {} })
}
const iconoTendencia = { sube: 'trending-up', baja: 'trending-down', estable: 'minus' }
</script>

<template>
  <button
    type="button"
    class="cr-card flex w-full flex-col gap-2 p-5 text-left transition hover:border-hairline-strong hover:shadow-md"
    :disabled="cargando || !kpi?.drill_down"
    @click="irADrillDown"
  >
    <template v-if="cargando">
      <span class="h-3 w-28 animate-pulse rounded bg-surface-sunk"></span>
      <span class="h-7 w-20 animate-pulse rounded bg-surface-sunk"></span>
    </template>
    <template v-else-if="kpi">
      <p class="text-[0.66rem] font-semibold uppercase tracking-[0.13em] text-ink-3">{{ kpi.titulo }}</p>
      <p class="serif text-2xl leading-none text-ink tabular-nums">{{ valorTexto(kpi) }}</p>
      <div class="mt-1 flex items-center justify-between">
        <span
          v-if="kpi.tendencia && kpi.tendencia.direccion !== 'estable'"
          class="inline-flex items-center gap-1 text-xs"
          :class="kpi.tendencia.direccion === 'sube' ? 'text-good' : 'text-bad'"
        >
          <CrIcon :name="iconoTendencia[kpi.tendencia.direccion]" :size="13" />
          {{ kpi.tendencia.valor != null ? `${kpi.tendencia.valor}%` : '' }}
        </span>
        <span v-else class="text-xs text-ink-3">—</span>
        <CrIcon v-if="kpi.drill_down" name="chevron-right" :size="15" class="text-ink-3" />
      </div>
    </template>
  </button>
</template>
