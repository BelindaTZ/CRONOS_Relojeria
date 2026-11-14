<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarPeriodos, listarProductividad } from '@/tecnicos/services/tecnicosApi'

const periodos = ref([])
const periodoId = ref(null)
const filas = ref([])
const loading = ref(false)
const errorMsg = ref('')

const periodo = computed(() => periodos.value.find((p) => p.id === periodoId.value) || null)

async function cargar() {
  if (!periodoId.value) {
    filas.value = []
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    filas.value = await listarProductividad({ periodo_id: periodoId.value })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  periodos.value = await listarPeriodos().catch(() => [])
  if (periodos.value.length) periodoId.value = periodos.value[0].id
  cargar()
})
watch(periodoId, cargar)

const kpis = computed(() => {
  const totOt = filas.value.reduce((s, f) => s + f.ot_completadas, 0)
  const totMargen = filas.value.reduce((s, f) => s + Number(f.margen_generado || 0), 0)
  const totBono = filas.value.reduce((s, f) => s + Number(f.bono_alcanzado || 0), 0)
  return [
    { label: 'OT completadas', value: String(totOt) },
    { label: 'Margen generado', value: `$ ${totMargen.toLocaleString()}` },
    { label: 'Bonos del periodo', value: `$ ${totBono.toLocaleString()}`, gold: true },
  ]
})

const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () =>
      filas.value.map((f) => ({
        tecnico: f.tecnico_nombre,
        ot_completadas: f.ot_completadas,
        tiempo_promedio_horas: f.tiempo_promedio_horas,
        margen_generado: f.margen_generado,
        bono_alcanzado: f.bono_alcanzado,
      })),
    totalFilas: filas.value.length,
    imprimirPdf: () => window.print(),
  }),
)
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Técnicos"
      titulo="Productividad por técnico"
      sub="Vista operativa para el Técnico Jefe. El comparativo entre técnicos, periodos y sucursales en el tiempo está en Reportes."
    >
      <template #acciones>
        <div class="flex gap-1">
          <button
            v-for="o in exportOpts"
            :key="o.formato"
            class="cr-btn cr-btn-ghost text-xs"
            :disabled="!o.disponible"
            @click="o.ejecutar"
          >
            {{ o.etiqueta }}
          </button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-6 flex flex-wrap items-center gap-3">
      <label class="text-sm text-ink-2">Periodo</label>
      <select v-model="periodoId" class="cr-input max-w-[18rem]">
        <option v-if="!periodos.length" :value="null">— sin periodos —</option>
        <option v-for="p in periodos" :key="p.id" :value="p.id">
          {{ p.fecha_inicio }} → {{ p.fecha_fin }} ({{ p.estado }})
        </option>
      </select>
    </div>

    <KpiStrip v-if="periodo && filas.length" :items="kpis" />

    <p v-if="errorMsg" class="mb-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-if="!periodo" class="cr-card p-8 text-center text-ink-3">
      Elige un periodo de liquidación (se crean en «Bonos por periodo»).
    </p>
    <p v-else-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!filas.length" class="cr-card p-8 text-center text-ink-3">
      No hay técnicos activos con datos en este periodo.
    </p>

    <div v-else class="cr-card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
            <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Técnico</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">OT completadas</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Tiempo prom. (h)</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Margen generado</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Bono alcanzado</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-hairline-soft">
          <tr v-for="f in filas" :key="f.tecnico_id">
            <td class="px-6 py-2.5 font-medium text-ink">{{ f.tecnico_nombre }}</td>
            <td class="px-6 py-2.5 text-right tabular-nums">{{ f.ot_completadas }}</td>
            <td class="px-6 py-2.5 text-right tabular-nums">{{ f.tiempo_promedio_horas }}</td>
            <td class="px-6 py-2.5 text-right tabular-nums">$ {{ Number(f.margen_generado).toLocaleString() }}</td>
            <td class="px-6 py-2.5 text-right tabular-nums" :class="Number(f.bono_alcanzado) > 0 ? 'text-gold-strong font-medium' : 'text-ink-3'">
              $ {{ Number(f.bono_alcanzado).toLocaleString() }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
