<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { getOrdenesEnCurso } from '@/servicio_tecnico/services/servicioTecnicoApi'

const router = useRouter()
const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')

const ETIQ = {
  recibido: 'Recibido', en_diagnostico: 'En diagnóstico', presupuesto: 'Presupuesto',
  en_reparacion: 'En reparación', listo: 'Listo',
}
const TONO = { recibido: 'neutral', en_diagnostico: 'info', presupuesto: 'warn', en_reparacion: 'info', listo: 'good' }
const ORDEN = ['recibido', 'en_diagnostico', 'presupuesto', 'en_reparacion', 'listo']

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await getOrdenesEnCurso()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)

const porEstado = computed(() =>
  ORDEN.map((e) => ({ estado: e, items: rows.value.filter((o) => o.estado === e) })),
)
const kpis = computed(() => [
  { label: 'OT en curso', value: String(rows.value.length) },
  { label: 'Listas para entregar', value: String(rows.value.filter((o) => o.estado === 'listo').length), gold: true },
  {
    label: 'Con entrega estimada vencida',
    value: String(rows.value.filter((o) => o.fecha_estimada_entrega && new Date(o.fecha_estimada_entrega) < new Date()).length),
  },
])
const fecha = (d) => (d ? new Date(d).toLocaleDateString() : '—')
</script>

<template>
  <div>
    <PageHeader eyebrow="Taller" titulo="Órdenes en curso" sub="Tablero del taller: cada orden abierta en su estado actual (§4.11.1).">
      <template #acciones>
        <RouterLink :to="{ name: 'ordenes-trabajo' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Órdenes</RouterLink>
        <button class="cr-btn cr-btn-ghost" @click="cargar"><CrIcon name="refresh-cw" :size="14" /> Actualizar</button>
      </template>
    </PageHeader>

    <KpiStrip :items="kpis" />

    <p v-if="errorMsg" class="my-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-else-if="loading" class="my-4 text-sm text-ink-3">Cargando…</p>

    <div v-else class="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <section v-for="col in porEstado" :key="col.estado" class="cr-card p-0">
        <header class="flex items-center justify-between border-b border-hairline px-4 py-2.5">
          <Pill :tone="TONO[col.estado]" :label="ETIQ[col.estado]" />
          <span class="text-xs text-ink-3 tabular-nums">{{ col.items.length }}</span>
        </header>
        <ul class="divide-y divide-hairline-soft">
          <li
            v-for="o in col.items"
            :key="o.id"
            class="cursor-pointer px-4 py-2.5 hover:bg-surface-sunk/50"
            @click="router.push({ name: 'ot-ficha', params: { id: o.id } })"
          >
            <p class="serif text-sm text-ink">{{ o.numero }}</p>
            <p class="text-xs text-ink-2">{{ o.reloj_marca }} {{ o.reloj_referencia }}</p>
            <p class="text-xs text-ink-3">{{ o.tecnico_nombre || 'sin asignar' }} · est. {{ fecha(o.fecha_estimada_entrega) }}</p>
          </li>
          <li v-if="!col.items.length" class="px-4 py-3 text-xs text-ink-3">—</li>
        </ul>
      </section>
    </div>
  </div>
</template>
