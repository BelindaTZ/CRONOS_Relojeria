<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { getDesviacionLubricacion } from '@/lubricacion/services/lubricacionApi'

const rows = ref([])
const loading = ref(false)
const errorMsg = ref('')
const f = ref({ desde: '', hasta: '' })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await getDesviacionLubricacion({
      desde: f.value.desde || undefined,
      hasta: f.value.hasta || undefined,
    })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
let t
watch(f, () => { clearTimeout(t); t = setTimeout(cargar, 300) }, { deep: true })

const kpis = computed(() => [
  { label: 'Desviaciones', value: String(rows.value.length), gold: true },
  { label: 'OT afectadas', value: String(new Set(rows.value.map((r) => r.orden_trabajo_id)).size) },
])
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => rows.value,
    totalFilas: rows.value.length,
    imprimirPdf: () => window.print(),
  }),
)
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Taller · Lubricación"
      titulo="Desviaciones de lubricación"
      sub="Puntos donde el técnico usó un producto distinto al recomendado en la ficha del calibre. Versión operativa; el análisis agregado es de Reportes (013)."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'fichas-lubricacion' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Fichas</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-center gap-3">
      <input v-model="f.desde" type="date" class="cr-input max-w-[11rem]" />
      <input v-model="f.hasta" type="date" class="cr-input max-w-[11rem]" />
    </div>

    <KpiStrip :items="kpis" />

    <p v-if="errorMsg" class="my-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-else-if="loading" class="my-4 text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!rows.length" class="cr-card mt-4 p-8 text-center text-ink-3">Sin desviaciones en el periodo. Toda la lubricación siguió la ficha.</p>

    <div v-else class="mt-4 overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-table-head-border bg-surface-head text-left">
            <th class="px-3 py-2 font-medium">OT</th>
            <th class="px-3 py-2 font-medium">Punto</th>
            <th class="px-3 py-2 font-medium">Recomendado</th>
            <th class="px-3 py-2 font-medium">Usado</th>
            <th class="px-3 py-2 font-medium">Fecha</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="i" class="border-b border-hairline-soft">
            <td class="px-3 py-2 tabular-nums">#{{ r.orden_trabajo_id }}</td>
            <td class="px-3 py-2">{{ r.punto_nombre }}</td>
            <td class="px-3 py-2 text-ink-3">{{ r.producto_recomendado || '—' }}</td>
            <td class="px-3 py-2 text-warn">{{ r.producto_usado }}</td>
            <td class="px-3 py-2 tabular-nums">{{ new Date(r.fecha).toLocaleDateString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
