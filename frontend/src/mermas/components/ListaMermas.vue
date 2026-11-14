<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import { listarMermas } from '@/mermas/services/mermasApi'
import MermaFormModal from './MermaFormModal.vue'

const router = useRouter()
const session = useSessionStore()

const CAUSAS = {
  dano_tienda: 'Daño en tienda', dano_transito: 'Daño en tránsito', robo_perdida: 'Robo / pérdida',
  defecto_fabrica: 'Defecto de fábrica', dano_servicio: 'Daño en servicio', insumo_caducado: 'Insumo caducado',
}
const ESTADOS = {
  en_evaluacion: 'En evaluación', dado_de_baja: 'Dado de baja', en_reclamo_proveedor: 'En reclamo — proveedor',
  en_reclamo_seguro: 'En reclamo — seguro', reparado_reingresado: 'Reparado y reingresado',
}
const TONO = {
  en_evaluacion: 'warn', dado_de_baja: 'bad', en_reclamo_proveedor: 'info',
  en_reclamo_seguro: 'info', reparado_reingresado: 'good',
}

const columns = [
  { key: 'numero', label: 'N.º' },
  { key: 'bien', label: 'Bien' },
  { key: 'causa', label: 'Causa' },
  { key: 'sucursal', label: 'Sucursal' },
  { key: 'costo', label: 'Costo', align: 'right' },
  { key: 'estado', label: 'Estado' },
  { key: 'fecha', label: 'Fecha' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const page = ref(1)
const fCausa = ref('')
const fEstado = ref('')
const fSucursal = ref('')
const sucursales = ref([])
const modalNuevo = ref(false)

async function cargar() {
  loading.value = true
  const res = await listarMermas({
    causa: fCausa.value || undefined, estado: fEstado.value || undefined,
    sucursal_id: fSucursal.value || undefined, page: page.value,
  }).catch(() => ({ items: [], total: 0 }))
  rows.value = res.items
  total.value = res.total
  loading.value = false
}
onMounted(async () => {
  sucursales.value = await listarSucursales().then((r) => r.items).catch(() => [])
  cargar()
})
watch([fCausa, fEstado, fSucursal, page], cargar)

const kpis = computed(() => {
  const enEval = rows.value.filter((m) => m.estado === 'en_evaluacion').length
  const conCosto = rows.value.filter((m) => m.costo_visible)
  const totalMonto = conCosto.reduce((s, m) => s + Number(m.costo_perdida || 0), 0)
  return [
    { label: 'Mermas (esta página)', value: String(total.value) },
    { label: 'En evaluación', value: String(enEval) },
    ...(conCosto.length ? [{ label: 'Costo total (página)', value: totalMonto.toLocaleString(undefined, { minimumFractionDigits: 2 }), gold: true }] : []),
  ]
})
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Mermas"
      titulo="Mermas y pérdidas"
      sub="Relojes o piezas que salen de stock por daño, pérdida, robo, defecto o caducidad — sin venta (§4.12)."
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      v-model:page="page"
      :kpis="kpis"
      :row-actions="(m) => [{ label: 'Ver ficha', icon: 'eye', onClick: () => router.push({ name: 'merma-ficha', params: { id: m.id } }) }]"
      empty-title="Sin mermas registradas"
      empty-hint="Reporta el bien afectado, la causa y la fecha del hecho."
      empty-icon="alert-triangle"
      @retry="cargar"
      @row-click="(m) => router.push({ name: 'merma-ficha', params: { id: m.id } })"
    >
      <template #actions>
        <button class="cr-btn cr-btn-primary" @click="modalNuevo = true">Reportar merma</button>
      </template>
      <template #toolbar>
        <select v-model="fCausa" class="cr-input max-w-[12rem]">
          <option value="">Todas las causas</option>
          <option v-for="(l, c) in CAUSAS" :key="c" :value="c">{{ l }}</option>
        </select>
        <select v-model="fEstado" class="cr-input max-w-[13rem]">
          <option value="">Todos los estados</option>
          <option v-for="(l, e) in ESTADOS" :key="e" :value="e">{{ l }}</option>
        </select>
        <select v-if="sucursales.length > 1" v-model="fSucursal" class="cr-input max-w-[12rem]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </template>
      <template #cell-numero="{ row }"><span class="tabular-nums">{{ row.numero }}</span></template>
      <template #cell-bien="{ row }">
        <span v-if="row.bien_tipo === 'reloj'">Reloj {{ row.reloj_serie }}</span>
        <span v-else>{{ row.pieza_codigo }} <span v-if="row.cantidad > 1" class="text-ink-3">× {{ row.cantidad }}</span></span>
      </template>
      <template #cell-causa="{ row }">
        {{ CAUSAS[row.causa] || row.causa }}
        <span v-if="row.categoria_merma_nombre" class="text-ink-3"> · {{ row.categoria_merma_nombre }}</span>
      </template>
      <template #cell-sucursal="{ row }">{{ row.sucursal_nombre }}</template>
      <template #cell-costo="{ row }">
        <span v-if="row.costo_visible" class="tabular-nums">{{ dinero(row.costo_perdida) }}</span>
        <span v-else class="text-ink-3">—</span>
      </template>
      <template #cell-estado="{ row }"><Pill :tone="TONO[row.estado] || 'neutral'" :label="ESTADOS[row.estado] || row.estado" /></template>
      <template #cell-fecha="{ row }"><span class="tabular-nums">{{ row.fecha_evento }}</span></template>
    </WorkPanel>

    <MermaFormModal v-model="modalNuevo" @guardado="(m) => router.push({ name: 'merma-ficha', params: { id: m.id } })" />
  </div>
</template>
