<script setup>
/**
 * Tabla de detalle genérica para un reporte analítico: columnas derivadas de
 * las claves de la primera fila, paginada en cliente (Principio XI — el
 * volumen real de cada reporte es pequeño, feature 012 D5/012 "Scale/Scope").
 */
import { computed, ref, watch } from 'vue'
import CrIcon from '@/shared/ui/CrIcon.vue'

const props = defineProps({ filas: { type: Array, default: () => [] }, porPagina: { type: Number, default: 25 } })
const pagina = ref(1)
watch(() => props.filas, () => { pagina.value = 1 })

const columnas = computed(() => (props.filas[0] ? Object.keys(props.filas[0]) : []))
const totalPaginas = computed(() => Math.max(1, Math.ceil(props.filas.length / props.porPagina)))
const filasPagina = computed(() => {
  const inicio = (pagina.value - 1) * props.porPagina
  return props.filas.slice(inicio, inicio + props.porPagina)
})

function etiquetaColumna(c) {
  return c.replaceAll('_', ' ').replace(/^./, (s) => s.toUpperCase())
}
function celda(v) {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'number') return v.toLocaleString(undefined, { maximumFractionDigits: 2 })
  return String(v)
}
</script>

<template>
  <div>
    <p v-if="!filas.length" class="rounded-lg bg-surface-sunk px-4 py-6 text-center text-sm text-ink-3">
      Sin filas para los filtros elegidos.
    </p>
    <div v-else class="overflow-x-auto rounded-lg border border-hairline">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-table-head-border bg-surface-head">
            <th v-for="c in columnas" :key="c" class="whitespace-nowrap px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-ink-2">
              {{ etiquetaColumna(c) }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-hairline-soft">
          <tr v-for="(f, i) in filasPagina" :key="i" class="hover:bg-surface-sunk/60">
            <td v-for="c in columnas" :key="c" class="whitespace-nowrap px-3 py-2 tabular-nums text-ink">{{ celda(f[c]) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="totalPaginas > 1" class="mt-3 flex items-center justify-between text-xs text-ink-3">
      <span>Página {{ pagina }} de {{ totalPaginas }} · {{ filas.length }} filas</span>
      <div class="flex gap-1">
        <button type="button" class="cr-btn cr-btn-ghost !p-1.5" :disabled="pagina <= 1" @click="pagina--"><CrIcon name="chevron-left" :size="15" /></button>
        <button type="button" class="cr-btn cr-btn-ghost !p-1.5" :disabled="pagina >= totalPaginas" @click="pagina++"><CrIcon name="chevron-right" :size="15" /></button>
      </div>
    </div>
  </div>
</template>
