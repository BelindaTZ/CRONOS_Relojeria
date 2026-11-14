<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { getCliente, getHistorialCliente } from '@/clientes/services/clientesApi'

const route = useRoute()
const id = Number(route.params.id)
const cliente = ref(null)
const h = ref(null)
const loading = ref(true)

async function cargar() {
  loading.value = true
  ;[cliente.value, h.value] = await Promise.all([
    getCliente(id).catch(() => null),
    getHistorialCliente(id).catch(() => null),
  ])
  loading.value = false
}
onMounted(cargar)

const ICONO = { compra: 'package-check', servicio: 'watch', cambio_nivel: 'trending-up', cita: 'clock' }

const kpis = computed(() => [
  { label: 'Total en compras', value: h.value ? `$ ${Number(h.value.total_compras).toLocaleString()}` : '—' },
  { label: 'Total en servicios', value: h.value ? `$ ${Number(h.value.total_servicios).toLocaleString()}` : '—' },
  {
    label: 'Total histórico',
    value: h.value ? `$ ${(Number(h.value.total_compras) + Number(h.value.total_servicios)).toLocaleString()}` : '—',
    gold: true,
  },
])

const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => (h.value?.movimientos || []).map((m) => ({
      fecha: m.fecha, tipo: m.tipo, detalle: m.detalle, monto: m.monto, documento_id: m.documento_id,
    })),
    totalFilas: h.value?.movimientos?.length || 0,
    imprimirPdf: () => window.print(),
  }),
)
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Clientes · Historial"
      :titulo="cliente ? cliente.nombre : 'Historial'"
      :sub="cliente ? `${cliente.identificacion} · ${cliente.numero_afiliado}` : ''"
    >
      <template #acciones>
        <RouterLink :to="{ name: 'cliente-ficha', params: { id } }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Ficha</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">
            {{ o.etiqueta }}
          </button>
        </div>
      </template>
    </PageHeader>

    <KpiStrip v-if="h" :items="kpis" />

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>

    <div v-else-if="h" class="grid gap-5 lg:grid-cols-3">
      <section class="cr-card p-6 lg:col-span-2">
        <h2 class="serif text-lg text-ink">Compras y servicios</h2>
        <ol v-if="h.movimientos.length" class="mt-4 space-y-3">
          <li v-for="(m, i) in h.movimientos" :key="i" class="flex items-start gap-3 border-b border-hairline-soft pb-3 last:border-0">
            <span class="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-surface-sunk text-ink-2">
              <CrIcon :name="ICONO[m.tipo] || 'circle-check'" :size="14" />
            </span>
            <div class="flex-1">
              <p class="text-sm text-ink">{{ m.detalle }}</p>
              <p class="text-xs text-ink-3">
                {{ new Date(m.fecha).toLocaleDateString() }}
                <span v-if="m.sucursal_nombre"> · {{ m.sucursal_nombre }}</span>
                <span v-if="m.documento_id"> · doc. #{{ m.documento_id }}</span>
              </p>
            </div>
            <span v-if="m.monto != null" class="tabular-nums text-sm font-medium text-ink">$ {{ Number(m.monto).toLocaleString() }}</span>
          </li>
        </ol>
        <p v-else class="mt-4 text-sm text-ink-3">Este cliente aún no tiene compras ni servicios registrados.</p>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Cambios de nivel</h2>
        <ol v-if="h.cambios_nivel.length" class="mt-4 space-y-3 text-sm">
          <li v-for="(cn, i) in h.cambios_nivel" :key="i" class="border-b border-hairline-soft pb-2 last:border-0">
            <p class="text-ink-2">{{ new Date(cn.fecha).toLocaleDateString() }}</p>
            <p class="text-xs text-ink-3">
              {{ cn.hecho.replace(/_/g, ' ') }}<span v-if="cn.documento_id"> · doc. #{{ cn.documento_id }}</span>
            </p>
          </li>
        </ol>
        <p v-else class="mt-4 text-sm text-ink-3">Sin cambios de nivel.</p>
        <p class="mt-3 text-xs text-ink-3">Las citas del cliente se listan aquí cuando exista el módulo de citas (007).</p>
      </section>
    </div>
  </div>
</template>
