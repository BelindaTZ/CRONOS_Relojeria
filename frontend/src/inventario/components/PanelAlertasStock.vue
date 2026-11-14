<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import { listarAlertasStock } from '@/inventario/services/inventarioApi'

const router = useRouter()

const TIPO_META = {
  ultima_unidad: { label: 'Reposición', tone: 'bad', icon: 'alert-triangle' },
  cerca_maximo: { label: 'Sobre-stock', tone: 'info', icon: 'trending-up' },
  bajo_minimo: { label: 'Bajo mínimo', tone: 'warn', icon: 'alert-circle' },
  caducidad_proxima: { label: 'Caducidad próxima', tone: 'warn', icon: 'clock' },
  lote_vencido: { label: 'Lote vencido', tone: 'bad', icon: 'alert-triangle' },
}

const alertas = ref([])
const loading = ref(true)
const errorMsg = ref('')
const filtroTipo = ref('')
const filtroSucursal = ref('')
const sucursales = ref([])

const sucursalNombre = (id) => sucursales.value.find((s) => s.id === id)?.nombre ?? (id ? `#${id}` : 'Todas')

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    alertas.value = await listarAlertasStock({
      tipo: filtroTipo.value || undefined,
      sucursal_id: filtroSucursal.value || undefined,
    })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  sucursales.value = (await listarSucursales().catch(() => ({ items: [] }))).items
  cargar()
})
watch([filtroTipo, filtroSucursal], cargar)

const kpis = computed(() => {
  const c = (t) => alertas.value.filter((a) => a.tipo === t).length
  return [
    { label: 'Relojes a reponer', value: String(c('ultima_unidad')) },
    { label: 'Piezas bajo mínimo', value: String(c('bajo_minimo')) },
    { label: 'Caducidad / vencidos', value: String(c('caducidad_proxima') + c('lote_vencido')) },
    { label: 'Sobre-stock', value: String(c('cerca_maximo')) },
  ]
})

function detalleTexto(a) {
  const d = a.detalle || {}
  if (a.tipo === 'ultima_unidad') return `Quedan ${d.unidades ?? 1} unidad(es) de este modelo`
  if (a.tipo === 'cerca_maximo') return `${d.unidades ?? '?'} unidades — alcanzó el máximo recomendado (${d.maximo ?? '?'})`
  if (a.tipo === 'bajo_minimo') return `Stock ${d.stock ?? '?'} ≤ mínimo ${d.minimo ?? '?'}`
  if (a.tipo === 'caducidad_proxima') return `${d.lotes ?? 1} lote(s) próximo(s) a caducar`
  if (a.tipo === 'lote_vencido') return `${d.lotes ?? 1} lote(s) vencido(s)`
  return ''
}

function reponer(a) {
  const ac = a.accion_reponer
  if (!ac) return
  const prellenar = {
    proveedor_id: ac.proveedor_id ?? null,
    lineas: [{
      item_tipo: ac.item_tipo,
      item_ref: ac.item_ref,
      marca_nombre: ac.marca ?? null,
      cantidad: ac.cantidad_sugerida,
      costo_unitario: null,
    }],
  }
  router.push({ name: 'compras', query: { prellenar: JSON.stringify(prellenar) } })
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Inventario"
      titulo="Alertas de stock"
      sub="No bloquean ninguna operación. La acción «Reponer» abre la orden de compra al proveedor con los datos puestos."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'inventario' }" class="cr-btn cr-btn-ghost">Relojes</RouterLink>
        <RouterLink :to="{ name: 'piezas-lotes' }" class="cr-btn cr-btn-ghost">Lotes y caducidad</RouterLink>
      </template>
    </PageHeader>

    <KpiStrip :items="kpis" />

    <div class="mb-3 flex flex-wrap items-center gap-2">
      <select v-model="filtroTipo" class="cr-input max-w-[13rem]">
        <option value="">Todos los tipos</option>
        <option v-for="(m, k) in TIPO_META" :key="k" :value="k">{{ m.label }}</option>
      </select>
      <select v-model="filtroSucursal" class="cr-input max-w-[12rem]">
        <option value="">Todas las sucursales</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
      <span class="ml-auto text-xs text-ink-3">{{ alertas.length }} alerta(s)</span>
    </div>

    <div v-if="errorMsg" class="cr-card flex flex-col items-center gap-3 px-6 py-16 text-center">
      <CrIcon name="alert-triangle" :size="36" class="text-bad" />
      <p class="text-sm text-ink-2">{{ errorMsg }}</p>
      <button class="cr-btn cr-btn-ghost" @click="cargar">Reintentar</button>
    </div>

    <div v-else-if="loading" class="cr-card space-y-3 p-6">
      <div v-for="n in 4" :key="n" class="h-12 animate-pulse rounded-lg bg-surface-sunk"></div>
    </div>

    <div v-else-if="!alertas.length" class="cr-card flex flex-col items-center gap-2 px-6 py-16 text-center">
      <CrIcon name="circle-check" :size="42" class="text-good" />
      <p class="serif text-lg text-ink">Sin alertas de stock</p>
      <p class="max-w-sm text-sm text-ink-2">Todo el inventario está dentro de los umbrales configurados.</p>
    </div>

    <ul v-else class="space-y-2">
      <li
        v-for="a in alertas"
        :key="a.id"
        class="cr-card flex flex-wrap items-center gap-4 p-4"
      >
        <span
          class="grid h-9 w-9 shrink-0 place-items-center rounded-full"
          :class="{
            'bg-bad-bg text-bad': TIPO_META[a.tipo]?.tone === 'bad',
            'bg-warn-bg text-warn': TIPO_META[a.tipo]?.tone === 'warn',
            'bg-primary-100 text-primary-700': TIPO_META[a.tipo]?.tone === 'info',
          }"
        >
          <CrIcon :name="TIPO_META[a.tipo]?.icon || 'alert-circle'" :size="17" />
        </span>
        <div class="min-w-[12rem] flex-1">
          <p class="font-medium text-ink">
            {{ a.etiqueta }}
            <span class="text-xs font-normal text-ink-3">· {{ a.ambito === 'modelo' ? 'modelo de reloj' : 'pieza' }}</span>
          </p>
          <p class="text-sm text-ink-2">{{ detalleTexto(a) }}</p>
        </div>
        <Pill :tone="TIPO_META[a.tipo]?.tone || 'neutral'" :label="TIPO_META[a.tipo]?.label || a.tipo" />
        <span class="text-xs text-ink-3">{{ sucursalNombre(a.sucursal_id) }}</span>
        <button
          v-if="a.accion_reponer"
          class="cr-btn cr-btn-primary text-xs"
          @click="reponer(a)"
        >
          <CrIcon name="truck" :size="14" /> Reponer stock
        </button>
      </li>
    </ul>
  </div>
</template>
