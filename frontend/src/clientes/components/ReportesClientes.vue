<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { reporteClientesPorNivel, reporteMejoresClientes } from '@/clientes/services/clientesApi'

const porNivel = ref([])
const mejores = ref([])
const top = ref(20)
const loading = ref(true)

async function cargar() {
  loading.value = true
  ;[porNivel.value, mejores.value] = await Promise.all([
    reporteClientesPorNivel().catch(() => []),
    reporteMejoresClientes({ top: top.value }).catch(() => []),
  ])
  loading.value = false
}
onMounted(cargar)

const totalClientes = computed(() => porNivel.value.reduce((s, n) => s + n.clientes, 0))

const exportNivel = computed(() =>
  opcionesExportacion({
    filas: () => porNivel.value.map((n) => ({ nivel: n.nivel_nombre, clientes: n.clientes })),
    imprimirPdf: () => window.print(),
  }),
)
const exportMejores = computed(() =>
  opcionesExportacion({
    filas: () => mejores.value.map((m) => ({
      cliente: m.nombre, afiliado: m.numero_afiliado,
      compras: m.total_compras, servicios: m.total_servicios, total: m.total,
    })),
    totalFilas: mejores.value.length,
    imprimirPdf: () => window.print(),
  }),
)
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Clientes · Reportes operativos"
      titulo="Reportes de clientes"
      sub="Distribución por nivel para campañas dirigidas y ranking de mejores clientes por volumen. El análisis comparado en el tiempo está en Reportes (013)."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'clientes-en-riesgo' }" class="cr-btn cr-btn-ghost">Clientes en riesgo</RouterLink>
        <RouterLink :to="{ name: 'clientes' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Clientes</RouterLink>
      </template>
    </PageHeader>

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>

    <div v-else class="grid gap-5 lg:grid-cols-2">
      <section class="cr-card p-6">
        <header class="mb-4 flex items-center justify-between">
          <h2 class="serif text-lg text-ink">Clientes por nivel</h2>
          <div class="flex gap-1">
            <button v-for="o in exportNivel" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
          </div>
        </header>
        <ul class="space-y-3">
          <li v-for="n in porNivel" :key="n.nivel_nombre">
            <div class="mb-1 flex items-baseline justify-between text-sm">
              <span class="text-ink">{{ n.nivel_nombre }}</span>
              <span class="tabular-nums text-ink-2">{{ n.clientes }}<span class="text-ink-3"> · {{ totalClientes ? ((n.clientes / totalClientes) * 100).toFixed(0) : 0 }} %</span></span>
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-surface-sunk">
              <div class="h-full rounded-full bg-gold/60" :style="{ width: `${totalClientes ? (n.clientes / totalClientes) * 100 : 0}%` }"></div>
            </div>
          </li>
        </ul>
        <p v-if="!porNivel.length" class="text-sm text-ink-3">Sin datos.</p>
      </section>

      <section class="cr-card overflow-hidden p-0">
        <header class="flex items-center justify-between p-6 pb-3">
          <h2 class="serif text-lg text-ink">Mejores clientes</h2>
          <div class="flex items-center gap-2">
            <select v-model.number="top" class="cr-input max-w-[6rem] text-xs" @change="cargar">
              <option :value="10">Top 10</option><option :value="20">Top 20</option><option :value="50">Top 50</option>
            </select>
            <button v-for="o in exportMejores" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
          </div>
        </header>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Cliente</th>
              <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Compras</th>
              <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Servicios</th>
              <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Total</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-hairline-soft">
            <tr v-for="(m, i) in mejores" :key="m.cliente_id">
              <td class="px-6 py-2.5">
                <span class="mr-1.5 text-xs text-ink-3">{{ i + 1 }}.</span>
                <span class="font-medium text-ink">{{ m.nombre }}</span>
                <span class="ml-1 text-xs text-ink-3">{{ m.numero_afiliado }}</span>
              </td>
              <td class="px-6 py-2.5 text-right tabular-nums">$ {{ Number(m.total_compras).toLocaleString() }}</td>
              <td class="px-6 py-2.5 text-right tabular-nums">$ {{ Number(m.total_servicios).toLocaleString() }}</td>
              <td class="px-6 py-2.5 text-right tabular-nums font-medium text-gold-strong">$ {{ Number(m.total).toLocaleString() }}</td>
            </tr>
            <tr v-if="!mejores.length"><td colspan="4" class="px-6 py-6 text-center text-ink-3">Aún no hay compras ni servicios registrados (008 / 009).</td></tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>
