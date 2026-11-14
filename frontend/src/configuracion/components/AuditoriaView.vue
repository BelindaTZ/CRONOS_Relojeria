<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { listarAuditoria } from '@/configuracion/services/configuracionApi'

const columns = [
  { key: 'creado_en', label: 'Fecha' },
  { key: 'actor', label: 'Actor' },
  { key: 'accion', label: 'Acción' },
  { key: 'entidad', label: 'Entidad' },
  { key: 'ip_origen', label: 'IP de origen' },
]
const TONO = { crear: 'good', editar: 'info', eliminar: 'bad', inactivar: 'warn', cancelar: 'bad', corregir: 'warn', confirmar: 'info', login: 'neutral' }

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ''
const q = ref('')
const filtroEntidad = ref('')
const page = ref(1)

async function cargar() {
  loading.value = true
  try {
    const res = await listarAuditoria({ entidad: filtroEntidad.value || undefined, page: page.value })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
watch([filtroEntidad], () => {
  page.value = 1
  cargar()
})
watch(page, cargar)

const visibles = computed(() => {
  const s = q.value.trim().toLowerCase()
  return s
    ? rows.value.filter((r) =>
        `${r.entidad} ${r.accion} ${r.actor_nombre ?? ''} ${r.actor_identificacion ?? ''} ${r.ip_origen ?? ''}`
          .toLowerCase()
          .includes(s),
      )
    : rows.value
})
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Sistema · Configuración"
      titulo="Auditoría"
      sub="Registro inmutable de todos los cambios sensibles (append-only)."
      :columns="columns"
      :rows="visibles"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Filtrar por entidad o acción…"
      empty-title="Sin registros de auditoría"
      empty-icon="clock"
      @retry="cargar"
    >
      <template #actions>
        <RouterLink :to="{ name: 'configuracion' }" class="cr-btn cr-btn-ghost">Catálogos</RouterLink>
        <RouterLink :to="{ name: 'parametros' }" class="cr-btn cr-btn-ghost">Parámetros</RouterLink>
      </template>
      <template #toolbar>
        <select v-model="filtroEntidad" class="cr-input max-w-[14rem]">
          <option value="">Todas las entidades</option>
          <option value="proveedor">Proveedor</option>
          <option value="orden_compra">Orden de compra</option>
          <option value="permisos_rol">Permisos de rol</option>
          <option value="parametro_configuracion">Parámetro</option>
          <option value="usuario">Usuario</option>
          <option value="sucursal">Sucursal</option>
        </select>
      </template>
      <template #cell-creado_en="{ row }">
        <span class="text-ink-2">{{ new Date(row.creado_en).toLocaleString() }}</span>
      </template>
      <template #cell-actor="{ row }">
        <span v-if="row.actor_nombre" class="text-ink">{{ row.actor_nombre }}</span>
        <span v-else class="text-ink-3">Sistema</span>
        <span v-if="row.actor_identificacion" class="block text-xs text-ink-3">{{ row.actor_identificacion }}</span>
      </template>
      <template #cell-ip_origen="{ row }">
        <span class="tabular-nums text-ink-2">{{ row.ip_origen || '—' }}</span>
      </template>
      <template #cell-accion="{ row }"><Pill :tone="TONO[row.accion] || 'neutral'" :label="row.accion" /></template>
      <template #cell-entidad="{ row }">
        <span class="text-ink">{{ row.entidad }}</span>
        <span v-if="row.entidad_id" class="text-ink-3"> #{{ row.entidad_id }}</span>
      </template>
    </WorkPanel>
  </div>
</template>
