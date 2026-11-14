<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { listarSucursales } from '@/sucursales'
import { valorInventario } from '@/inventario/services/inventarioApi'
import { valorPiezas } from '@/piezas'

const relojes = ref(null)
const piezas = ref(null)
const sucursales = ref([])
const filtroSucursal = ref('')
const errorMsg = ref('')

const sucursalNombre = (id) => sucursales.value.find((s) => s.id === id)?.nombre ?? (id ? `#${id}` : '—')
const fmt = (v) => (v == null ? '—' : `$ ${Number(v).toLocaleString()}`)

async function cargar() {
  errorMsg.value = ''
  try {
    ;[relojes.value, piezas.value] = await Promise.all([
      valorInventario(filtroSucursal.value || undefined),
      valorPiezas().catch(() => null),
    ])
  } catch (e) {
    errorMsg.value = e.message
  }
}
onMounted(async () => {
  sucursales.value = (await listarSucursales().catch(() => ({ items: [] }))).items
  cargar()
})
watch(filtroSucursal, cargar)

const totalPrecio = computed(() => {
  const a = Number(relojes.value?.a_precio_venta || 0)
  const b = Number(piezas.value?.a_precio_venta || 0)
  return a + b
})

const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => (relojes.value?.por_sucursal || []).map((s) => ({ ...s, sucursal: sucursalNombre(s.sucursal_id) })),
    imprimirPdf: () => window.print(),
  }),
)
</script>

<template>
  <div>
    <PageHeader eyebrow="Inventario" titulo="Valor del inventario" sub="Consulta operativa a costo y a precio de venta. El análisis comparado en el tiempo está en Reportes.">
      <template #acciones>
        <RouterLink :to="{ name: 'inventario' }" class="cr-btn cr-btn-ghost">Relojes</RouterLink>
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

    <div class="mb-5">
      <select v-model="filtroSucursal" class="cr-input max-w-[14rem]">
        <option value="">Todas las sucursales</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
    </div>

    <p v-if="errorMsg" class="text-sm text-bad">{{ errorMsg }}</p>

    <div class="grid gap-4 sm:grid-cols-3">
      <div class="cr-card p-6 shadow-sm">
        <p class="cr-label">Valor total a precio de venta</p>
        <p class="serif mt-2 text-3xl text-gold-strong tabular-nums">{{ fmt(totalPrecio) }}</p>
        <p class="mt-1 text-xs text-ink-3">Relojes {{ fmt(relojes?.a_precio_venta) }} · Piezas {{ fmt(piezas?.a_precio_venta) }}</p>
      </div>
      <div class="cr-card p-6 shadow-sm">
        <p class="cr-label">Valor a costo</p>
        <p v-if="relojes?.a_costo != null" class="serif mt-2 text-3xl text-ink tabular-nums">
          {{ fmt(Number(relojes.a_costo) + Number(piezas?.a_costo || 0)) }}
        </p>
        <p v-else class="mt-3 flex items-center gap-1 text-sm text-ink-3"><CrIcon name="lock" :size="13" /> restringido a roles administrativos</p>
      </div>
      <div class="cr-card p-6 shadow-sm">
        <p class="cr-label">Unidades / referencias</p>
        <p class="serif mt-2 text-3xl text-ink tabular-nums">{{ relojes?.unidades ?? '—' }}</p>
        <p class="mt-1 text-xs text-ink-3">{{ piezas?.referencias ?? 0 }} referencias de pieza con stock</p>
      </div>
    </div>

    <div v-if="relojes?.por_sucursal?.length" class="cr-card mt-5 overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
            <th class="px-4 py-3 text-[0.7rem] font-semibold uppercase text-ink-2">Sucursal</th>
            <th class="px-4 py-3 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Unidades</th>
            <th class="px-4 py-3 text-right text-[0.7rem] font-semibold uppercase text-ink-2">A precio</th>
            <th class="px-4 py-3 text-right text-[0.7rem] font-semibold uppercase text-ink-2">A costo</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-hairline-soft">
          <tr v-for="s in relojes.por_sucursal" :key="s.sucursal_id">
            <td class="px-4 py-2.5">{{ sucursalNombre(s.sucursal_id) }}</td>
            <td class="px-4 py-2.5 text-right tabular-nums">{{ s.unidades }}</td>
            <td class="px-4 py-2.5 text-right tabular-nums">{{ fmt(s.a_precio_venta) }}</td>
            <td class="px-4 py-2.5 text-right tabular-nums">{{ s.a_costo != null ? fmt(s.a_costo) : '···' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
