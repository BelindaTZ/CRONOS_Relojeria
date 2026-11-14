<script setup>
/**
 * Seguimiento y reintento de envíos (feature 014, US4) — también sirve como
 * el reporte operativo de envíos por tipo/estado (FR-014): mismo `listar()`
 * del backend para `/envios` y `/reportes/envios`.
 */
import { computed, onMounted, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { toast } from '@/shared/ui/toast'
import { opcionesExportacion } from '@/shared/exportar'
import { listarEnvios, reintentarEnvio } from '@/notificaciones/services/notificacionesApi'

const columns = [
  { key: 'creado_en', label: 'Fecha' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'destinatario_email', label: 'Destinatario' },
  { key: 'disparo_origen_tipo', label: 'Origen' },
  { key: 'estado', label: 'Estado' },
  { key: 'intentos', label: 'Intentos', align: 'right' },
]

const TONO = {
  encolado: 'neutral', enviando: 'info', enviado: 'info', entregado: 'good',
  rebotado: 'bad', fallido: 'bad', sin_destinatario: 'warn', cancelado: 'neutral',
}
const ESTADOS = Object.keys(TONO)

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const page = ref(1)
const tipo = ref('')
const estado = ref('')

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const r = await listarEnvios({ tipo: tipo.value || undefined, estado: estado.value || undefined, page: page.value })
    rows.value = r.items
    total.value = r.total
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
watch([tipo, estado], () => { page.value = 1; cargar() })
watch(page, cargar)

async function reintentar(envio) {
  try {
    await reintentarEnvio(envio.id)
    toast.success('Envío reencolado')
    cargar()
  } catch (e) {
    toast.error(e.status === 409 ? 'Este envío no se puede reintentar en su estado actual' : e.message)
  }
}

const kpis = computed(() => {
  const c = (estados) => rows.value.filter((r) => estados.includes(r.estado)).length
  return [
    { label: 'En esta página', value: String(rows.value.length) },
    { label: 'Entregados', value: String(c(['entregado'])) },
    { label: 'Fallidos / rebotados', value: String(c(['fallido', 'rebotado'])), gold: c(['fallido', 'rebotado']) > 0 },
    { label: 'Pendientes', value: String(c(['encolado', 'enviando'])) },
  ]
})

const exportOpts = computed(() =>
  opcionesExportacion({ filas: () => rows.value, totalFilas: total.value, imprimirPdf: () => window.print(), nombreArchivo: 'envios' }),
)

const fecha = (iso) => new Date(iso.endsWith('Z') ? iso : iso + 'Z').toLocaleString()
</script>

<template>
  <WorkPanel
    eyebrow="Notificaciones"
    titulo="Envíos"
    sub="Seguimiento de los correos automatizados del sistema — estado real de entrega y reintento manual."
    :columns="columns"
    :rows="rows"
    :total="total"
    :loading="loading"
    :error="errorMsg"
    :page="page"
    :page-size="20"
    :kpis="kpis"
    :row-actions="(r) => [{ label: 'Reintentar', icon: 'refresh-cw', hidden: !['fallido', 'rebotado'].includes(r.estado), onClick: () => reintentar(r) }]"
    empty-title="Sin envíos"
    empty-icon="send"
    @update:page="(p) => (page = p)"
    @retry="cargar"
  >
    <template #toolbar>
      <select v-model="estado" class="cr-input w-44">
        <option value="">Todos los estados</option>
        <option v-for="e in ESTADOS" :key="e" :value="e">{{ e }}</option>
      </select>
      <input v-model="tipo" class="cr-input w-44" placeholder="Tipo (ej. cupon)" />
      <div class="flex gap-1">
        <button v-for="o in exportOpts" :key="o.formato" type="button" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
      </div>
    </template>
    <template #cell-creado_en="{ row }">{{ fecha(row.creado_en) }}</template>
    <template #cell-destinatario_email="{ row }">{{ row.destinatario_email || '—' }}</template>
    <template #cell-disparo_origen_tipo="{ row }">{{ row.disparo_origen_tipo }} #{{ row.disparo_origen_id }}</template>
    <template #cell-estado="{ row }">
      <div class="flex items-center gap-2">
        <Pill :tone="TONO[row.estado] || 'neutral'" :label="row.estado" />
        <span v-if="row.motivo_estado" class="text-xs text-ink-3">{{ row.motivo_estado }}</span>
      </div>
    </template>
  </WorkPanel>
</template>
