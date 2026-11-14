<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { listarCheques, protestarCheque } from '@/contabilidad/services/contabilidadApi'

const columns = [
  { key: 'tipo', label: 'Tipo' },
  { key: 'banco', label: 'Banco / N.º' },
  { key: 'monto', label: 'Monto', align: 'right' },
  { key: 'fecha', label: 'Fecha' },
  { key: 'estado', label: 'Estado' },
]
const TONO = { en_cartera: 'neutral', depositado: 'info', cobrado: 'good', protestado: 'bad' }

const rows = ref([])
const loading = ref(true)
const fTipo = ref('')
const fEstado = ref('')

async function cargar() {
  loading.value = true
  rows.value = await listarCheques({ tipo: fTipo.value || undefined, estado: fEstado.value || undefined }).catch(() => [])
  loading.value = false
}
onMounted(cargar)
watch([fTipo, fEstado], cargar)

const kpis = computed(() => [
  { label: 'Cheques', value: String(rows.value.length) },
  { label: 'Protestados', value: String(rows.value.filter((c) => c.estado === 'protestado').length), gold: true },
])

async function protestar(c) {
  if (!(await confirm({
    title: `Protestar el cheque ${c.numero || c.id}`,
    message: 'Revierte el cobro asociado y reactiva la cuenta por cobrar. No es reversible.',
    confirmLabel: 'Protestar', tone: 'danger',
  }))) return
  try {
    await protestarCheque(c.id)
    toast.success('Cheque protestado · CxC reactivada')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const acciones = (c) => [
  { label: 'Protestar', icon: 'alert-triangle', danger: true, hidden: !(c.tipo === 'recibido' && c.estado !== 'protestado'), onClick: () => protestar(c) },
]
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Contabilidad"
      titulo="Cheques"
      sub="Emitidos y recibidos. Un cheque recibido protestado revierte el cobro y reactiva la cuenta por cobrar."
      :columns="columns"
      :rows="rows"
      :total="rows.length"
      :loading="loading"
      :page-size="200"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Sin cheques registrados"
      empty-icon="inbox"
      @retry="cargar"
    >
      <template #toolbar>
        <select v-model="fTipo" class="cr-input max-w-[10rem]">
          <option value="">Emitido / recibido</option>
          <option value="emitido">Emitido</option>
          <option value="recibido">Recibido</option>
        </select>
        <select v-model="fEstado" class="cr-input max-w-[11rem]">
          <option value="">Todos los estados</option>
          <option value="en_cartera">En cartera</option>
          <option value="depositado">Depositado</option>
          <option value="cobrado">Cobrado</option>
          <option value="protestado">Protestado</option>
        </select>
      </template>

      <template #cell-tipo="{ row }">{{ row.tipo }}</template>
      <template #cell-banco="{ row }">{{ row.banco || '—' }} <span v-if="row.numero" class="text-xs text-ink-3">{{ row.numero }}</span></template>
      <template #cell-monto="{ row }"><span class="tabular-nums">{{ dinero(row.monto) }}</span></template>
      <template #cell-fecha="{ row }"><span class="tabular-nums">{{ row.fecha }}</span></template>
      <template #cell-estado="{ row }"><Pill :tone="TONO[row.estado] || 'neutral'" :label="row.estado" /></template>
    </WorkPanel>
  </div>
</template>
