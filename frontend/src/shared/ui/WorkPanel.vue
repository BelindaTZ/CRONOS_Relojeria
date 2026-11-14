<script setup>
/**
 * Panel de trabajo estándar de CRONOS (Principio XI). Todo maestro de datos lo usa.
 *
 * Estructura: encabezado (eyebrow oro + título serif + acción primaria) →
 * tira de KPIs opcional → toolbar (búsqueda reactiva + filtros) + conteo →
 * tabla (columnas + acciones por fila + estado como pill) → paginación →
 * estados vacío / error / cargando.
 *
 *   <WorkPanel eyebrow="Abastecimiento" titulo="Proveedores"
 *     :columns="cols" :rows="items" :total="total" :loading="loading" :error="error"
 *     v-model:search="q" v-model:page="page" :page-size="20"
 *     :kpis="kpis" :row-actions="acciones" @retry="cargar">
 *     <template #actions><button class="cr-btn cr-btn-primary" @click="abrirAlta">Agregar</button></template>
 *     <template #toolbar> <select ...> </template>
 *     <template #cell-estado="{ row }"> <Pill .../> </template>
 *   </WorkPanel>
 */
import { computed } from 'vue'
import CrIcon from './CrIcon.vue'
import KpiStrip from './KpiStrip.vue'

const props = defineProps({
  eyebrow: { type: String, default: '' },
  titulo: { type: String, required: true },
  sub: { type: String, default: '' },
  columns: { type: Array, required: true }, // [{ key, label, align?, class? }]
  rows: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  search: { type: String, default: '' },
  searchPlaceholder: { type: String, default: 'Buscar…' },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
  kpis: { type: Array, default: null },
  rowActions: { type: Function, default: null }, // (row) => [{label,icon,danger,onClick,hidden}]
  rowKey: { type: String, default: 'id' },
  emptyTitle: { type: String, default: 'Aún no hay registros' },
  emptyHint: { type: String, default: '' },
  emptyIcon: { type: String, default: 'inbox' },
})
const emit = defineEmits(['update:search', 'update:page', 'retry', 'row-click'])

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const rango = computed(() => {
  if (!props.total) return '0'
  const desde = (props.page - 1) * props.pageSize + 1
  const hasta = Math.min(props.page * props.pageSize, props.total)
  return `${desde}–${hasta} de ${props.total}`
})
const vacio = computed(() => !props.loading && !props.error && props.rows.length === 0)
</script>

<template>
  <div>
    <header class="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-hairline pb-4">
      <div>
        <p v-if="eyebrow" class="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gold">{{ eyebrow }}</p>
        <h1 class="serif text-2xl leading-tight text-ink">{{ titulo }}</h1>
        <p v-if="sub" class="mt-1 text-sm text-ink-2">{{ sub }}</p>
      </div>
      <div class="flex items-center gap-2"><slot name="actions" /></div>
    </header>

    <KpiStrip v-if="kpis && kpis.length" :items="kpis" />

    <div class="mb-3 flex flex-wrap items-center gap-2">
      <div class="relative">
        <CrIcon name="search" :size="16" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
        <input
          class="cr-input min-w-[16rem] pl-9"
          :value="search"
          :placeholder="searchPlaceholder"
          @input="emit('update:search', $event.target.value)"
        />
      </div>
      <slot name="toolbar" />
      <span class="ml-auto text-xs text-ink-3">{{ rango }}</span>
    </div>

    <div class="cr-card overflow-hidden p-0">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
              <th
                v-for="c in columns"
                :key="c.key"
                class="px-4 py-3 text-[0.7rem] font-semibold uppercase tracking-wide text-ink-2"
                :class="[c.align === 'right' ? 'text-right' : '', c.class]"
              >
                {{ c.label }}
              </th>
              <th v-if="rowActions" class="px-4 py-3 text-right text-[0.7rem] font-semibold uppercase tracking-wide text-ink-2">
                Acciones
              </th>
            </tr>
          </thead>

          <tbody v-if="loading">
            <tr v-for="n in 6" :key="n" class="border-t border-hairline-soft">
              <td v-for="c in columns" :key="c.key" class="px-4 py-3">
                <div class="h-3 w-2/3 animate-pulse rounded bg-surface-sunk"></div>
              </td>
              <td v-if="rowActions"></td>
            </tr>
          </tbody>

          <tbody v-else-if="!vacio && !error" class="divide-y divide-hairline-soft">
            <tr
              v-for="row in rows"
              :key="row[rowKey]"
              class="transition-colors hover:bg-surface-sunk"
              @click="emit('row-click', row)"
            >
              <td
                v-for="c in columns"
                :key="c.key"
                class="px-4 py-3 align-middle"
                :class="[c.align === 'right' ? 'text-right tabular-nums' : '', c.class]"
              >
                <slot :name="`cell-${c.key}`" :row="row" :value="row[c.key]">
                  {{ row[c.key] ?? '—' }}
                </slot>
              </td>
              <td v-if="rowActions" class="whitespace-nowrap px-3 py-2 text-right" @click.stop>
                <button
                  v-for="(a, i) in (rowActions(row) || []).filter((x) => !x.hidden)"
                  :key="i"
                  type="button"
                  class="ml-0.5 rounded-lg p-1.5 text-ink-3 transition-colors"
                  :class="a.danger ? 'hover:bg-bad-bg hover:text-bad' : 'hover:bg-surface-head hover:text-ink'"
                  :title="a.label"
                  :aria-label="a.label"
                  :disabled="a.disabled"
                  @click="a.onClick && a.onClick()"
                >
                  <CrIcon :name="a.icon || 'more-vertical'" :size="17" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- estados -->
      <div v-if="error" class="flex flex-col items-center gap-3 px-6 py-16 text-center">
        <CrIcon name="alert-triangle" :size="40" class="text-bad" />
        <p class="serif text-lg text-ink">No se pudo cargar la información</p>
        <p class="max-w-sm text-sm text-ink-2">{{ error }}</p>
        <button class="cr-btn cr-btn-ghost" @click="emit('retry')">Reintentar</button>
      </div>

      <div v-else-if="vacio" class="flex flex-col items-center gap-2 px-6 py-16 text-center">
        <slot name="empty">
          <CrIcon :name="emptyIcon" :size="44" class="text-ink-3" />
          <p class="serif text-lg text-ink">{{ search ? 'Sin resultados' : emptyTitle }}</p>
          <p v-if="!search && emptyHint" class="max-w-sm text-sm text-ink-2">{{ emptyHint }}</p>
          <div v-if="!search" class="mt-2"><slot name="actions" /></div>
        </slot>
      </div>
    </div>

    <div v-if="!vacio && !error && totalPages > 1" class="mt-4 flex items-center justify-end gap-3 text-sm text-ink-2">
      <button
        class="cr-btn cr-btn-ghost px-3 py-1.5"
        :disabled="page <= 1"
        @click="emit('update:page', page - 1)"
      >
        <CrIcon name="chevron-left" :size="15" />
      </button>
      <span class="tabular-nums">Página {{ page }} de {{ totalPages }}</span>
      <button
        class="cr-btn cr-btn-ghost px-3 py-1.5"
        :disabled="page >= totalPages"
        @click="emit('update:page', page + 1)"
      >
        <CrIcon name="chevron-right" :size="15" />
      </button>
    </div>
  </div>
</template>
