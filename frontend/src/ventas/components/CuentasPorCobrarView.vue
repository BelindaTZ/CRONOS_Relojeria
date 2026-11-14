<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarCuentasPorCobrar } from '@/ventas/services/ventasApi'

const router = useRouter()
const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')
const fEstado = ref('pendiente')

const TONO = { pendiente: 'warn', saldada: 'good', anulada: 'bad' }

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await listarCuentasPorCobrar({ estado: fEstado.value || undefined })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
watch(fEstado, cargar)

const kpis = computed(() => {
  const pend = rows.value.filter((c) => c.estado === 'pendiente')
  const suma = pend.reduce((s, c) => s + Number(c.saldo || 0), 0)
  return [
    { label: 'Cuentas', value: String(rows.value.length) },
    { label: 'Pendientes', value: String(pend.length) },
    { label: 'Saldo por cobrar', value: suma.toLocaleString(undefined, { minimumFractionDigits: 2 }), gold: true },
  ]
})
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => rows.value.map((c) => ({
      origen: `${c.origen_tipo} #${c.origen_id}`, cliente: c.cliente_nombre,
      monto_original: c.monto_original, saldo: c.saldo, estado: c.estado,
    })),
    totalFilas: rows.value.length,
    imprimirPdf: () => window.print(),
  }),
)
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Ventas"
      titulo="Cuentas por cobrar"
      sub="Saldos generados por ventas y órdenes de trabajo a crédito. El aging y el registro de cobros los maneja Contabilidad (010)."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'ventas' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Ventas</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-4 flex items-center gap-3">
      <select v-model="fEstado" class="cr-input max-w-[11rem]">
        <option value="">Todos los estados</option>
        <option value="pendiente">Pendiente</option>
        <option value="saldada">Saldada</option>
        <option value="anulada">Anulada</option>
      </select>
    </div>

    <KpiStrip :items="kpis" />

    <p v-if="errorMsg" class="my-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-else-if="loading" class="my-4 text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!rows.length" class="cr-card mt-4 p-8 text-center text-ink-3">Sin cuentas por cobrar para el filtro.</p>

    <div v-else class="mt-4 overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-table-head-border bg-surface-head text-left">
            <th class="px-3 py-2 font-medium">Origen</th>
            <th class="px-3 py-2 font-medium">Cliente</th>
            <th class="px-3 py-2 text-right font-medium">Monto original</th>
            <th class="px-3 py-2 text-right font-medium">Saldo</th>
            <th class="px-3 py-2 font-medium">Estado</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in rows" :key="c.id" class="border-b border-hairline-soft">
            <td class="px-3 py-2">
              <button
                v-if="c.origen_tipo === 'venta'"
                class="text-gold-strong hover:underline"
                @click="router.push({ name: 'venta-ficha', params: { id: c.origen_id } })"
              >Venta #{{ c.origen_id }}</button>
              <span v-else>OT #{{ c.origen_id }}</span>
            </td>
            <td class="px-3 py-2">{{ c.cliente_nombre }}</td>
            <td class="px-3 py-2 text-right tabular-nums">{{ dinero(c.monto_original) }}</td>
            <td class="px-3 py-2 text-right tabular-nums">{{ dinero(c.saldo) }}</td>
            <td class="px-3 py-2"><Pill :tone="TONO[c.estado] || 'neutral'" :label="c.estado" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
