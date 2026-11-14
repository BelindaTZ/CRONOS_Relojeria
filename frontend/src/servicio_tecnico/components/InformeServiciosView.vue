<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarTecnicos } from '@/tecnicos'
import { getInformeServicios } from '@/servicio_tecnico/services/servicioTecnicoApi'

const rows = ref([])
const loading = ref(false)
const errorMsg = ref('')
const tecnicos = ref([])
const f = ref({ tecnico_id: '', numero_serie: '', desde: '', hasta: '' })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await getInformeServicios({
      tecnico_id: f.value.tecnico_id || undefined,
      numero_serie: f.value.numero_serie || undefined,
      desde: f.value.desde || undefined,
      hasta: f.value.hasta || undefined,
    })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  tecnicos.value = await listarTecnicos({ page: 1, size: 100 }).then((r) => r.items).catch(() => [])
  cargar()
})
let t
watch(f, () => { clearTimeout(t); t = setTimeout(cargar, 300) }, { deep: true })

const kpis = computed(() => {
  const total = rows.value.reduce((s, r) => s + Number(r.precio_arreglo || 0), 0)
  return [
    { label: 'Servicios', value: String(rows.value.length) },
    { label: 'Facturado', value: total.toLocaleString(undefined, { minimumFractionDigits: 2 }), gold: true },
  ]
})
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => rows.value.map((r) => ({
      ot: r.numero, cliente: r.cliente, tecnico: r.tecnico, fecha: r.fecha,
      numero_serie: r.numero_serie, trabajo: r.trabajo_realizado,
      repuestos: (r.repuestos || []).join('; '), precio: r.precio_arreglo,
    })),
    totalFilas: rows.value.length,
    imprimirPdf: () => window.print(),
  }),
)
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Taller"
      titulo="Informe de servicios"
      sub="Detalle operativo por cliente, técnico, unidad y periodo: qué se arregló, fecha, repuestos y precio del arreglo. El análisis agregado es de Reportes (013)."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'ordenes-trabajo' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Órdenes</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-center gap-3">
      <select v-model="f.tecnico_id" class="cr-input max-w-[12rem]">
        <option value="">Todos los técnicos</option>
        <option v-for="t in tecnicos" :key="t.id" :value="t.id">{{ t.nombre }}</option>
      </select>
      <input v-model="f.numero_serie" class="cr-input max-w-[12rem] tabular-nums" placeholder="N.º de serie…" />
      <input v-model="f.desde" type="date" class="cr-input max-w-[11rem]" />
      <input v-model="f.hasta" type="date" class="cr-input max-w-[11rem]" />
    </div>

    <KpiStrip :items="kpis" />

    <p v-if="errorMsg" class="my-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-else-if="loading" class="my-4 text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!rows.length" class="cr-card mt-4 p-8 text-center text-ink-3">Sin servicios entregados para el filtro.</p>

    <div v-else class="mt-4 overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-table-head-border bg-surface-head text-left">
            <th class="px-3 py-2 font-medium">OT</th>
            <th class="px-3 py-2 font-medium">Fecha</th>
            <th class="px-3 py-2 font-medium">Cliente</th>
            <th class="px-3 py-2 font-medium">Técnico</th>
            <th class="px-3 py-2 font-medium">N.º de serie</th>
            <th class="px-3 py-2 font-medium">Trabajo realizado</th>
            <th class="px-3 py-2 font-medium">Repuestos</th>
            <th class="px-3 py-2 text-right font-medium">Precio</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.orden_trabajo_id" class="border-b border-hairline-soft">
            <td class="px-3 py-2 serif">{{ r.numero }}</td>
            <td class="px-3 py-2 tabular-nums">{{ r.fecha }}</td>
            <td class="px-3 py-2">{{ r.cliente }}</td>
            <td class="px-3 py-2">{{ r.tecnico }}</td>
            <td class="px-3 py-2 tabular-nums">{{ r.numero_serie }}</td>
            <td class="px-3 py-2 text-ink-2">{{ r.trabajo_realizado }}</td>
            <td class="px-3 py-2 text-ink-3">{{ (r.repuestos || []).join(', ') || '—' }}</td>
            <td class="px-3 py-2 text-right tabular-nums">{{ Number(r.precio_arreglo || 0).toLocaleString(undefined, { minimumFractionDigits: 2 }) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
