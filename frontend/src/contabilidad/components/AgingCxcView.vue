<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import Pill from '@/shared/ui/Pill.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { opcionesExportacion } from '@/shared/exportar'
import { getAgingCxc, listarCxc, registrarCobroCxc } from '@/contabilidad/services/contabilidadApi'

const session = useSessionStore()

const columns = [
  { key: 'cliente', label: 'Cliente' },
  { key: 'origen', label: 'Origen' },
  { key: 'monto', label: 'Monto original', align: 'right' },
  { key: 'saldo', label: 'Saldo', align: 'right' },
  { key: 'dias', label: 'Días' },
]
const rows = ref([])
const aging = ref(null)
const loading = ref(true)
const modal = ref({ abierto: false, cxc: null })

async function cargar() {
  loading.value = true
  ;[rows.value, aging.value] = await Promise.all([
    listarCxc({ estado: 'pendiente' }).catch(() => []),
    getAgingCxc().catch(() => null),
  ])
  loading.value = false
}
onMounted(cargar)

const kpis = computed(() => aging.value ? [
  ...aging.value.tramos.map((t) => ({ label: t.tramo + ' días', value: `${t.cantidad} · ${dinero(t.saldo)}` })),
  { label: 'Total pendiente', value: dinero(aging.value.total), gold: true },
] : [])
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => rows.value.map((r) => ({ cliente: r.cliente_nombre, origen: `${r.origen_tipo} #${r.origen_id}`, monto_original: r.monto_original, saldo: r.saldo, dias: r.dias })),
    totalFilas: rows.value.length,
    imprimirPdf: () => window.print(),
  }),
)

const f = reactive({ monto: null, medio_pago: 'efectivo' })
function abrirModal(c) { modal.value = { abierto: true, cxc: c }; f.monto = c.saldo; f.medio_pago = 'efectivo' }
async function guardarCobro() {
  if (!f.monto || Number(f.monto) <= 0) return toast.error('Indica el monto.')
  try {
    await registrarCobroCxc(modal.value.cxc.id, { monto: Number(f.monto), medio_pago: f.medio_pago })
    toast.success('Cobro registrado')
    modal.value.abierto = false
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Contabilidad"
      titulo="Cuentas por cobrar"
      sub="Subledger con aging por tramos (0-30 / 31-60 / 61-90 / +90). Se alimenta de las ventas a crédito (009) y las órdenes de trabajo entregadas a crédito (008)."
      :columns="columns"
      :rows="rows"
      :total="rows.length"
      :loading="loading"
      :page-size="200"
      :kpis="kpis"
      :row-actions="(c) => [{ label: 'Registrar cobro', icon: 'circle-check', hidden: !session.puede('contable', 'editar'), onClick: () => abrirModal(c) }]"
      empty-title="Sin cuentas por cobrar pendientes"
      empty-icon="inbox"
      @retry="cargar"
    >
      <template #toolbar>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
      <template #cell-cliente="{ row }">{{ row.cliente_nombre }}</template>
      <template #cell-origen="{ row }">{{ row.origen_tipo === 'venta' ? 'Venta' : 'Servicio técnico' }} #{{ row.origen_id }}</template>
      <template #cell-monto="{ row }"><span class="tabular-nums">{{ dinero(row.monto_original) }}</span></template>
      <template #cell-saldo="{ row }"><span class="tabular-nums text-warn">{{ dinero(row.saldo) }}</span></template>
      <template #cell-dias="{ row }">{{ row.dias }}</template>
    </WorkPanel>

    <FormModal
      :model-value="modal.abierto" titulo="Registrar cobro" :guardando="false" ancho="max-w-md" :sucio="true"
      @update:model-value="modal.abierto = $event" @guardar="guardarCobro"
    >
      <FormField label="Monto" required>
        <input v-model="f.monto" type="number" step="0.01" min="0.01" class="cr-input tabular-nums" />
      </FormField>
      <FormField label="Medio de pago">
        <select v-model="f.medio_pago" class="cr-input">
          <option value="efectivo">Efectivo</option>
          <option value="transferencia">Transferencia</option>
          <option value="cheque">Cheque</option>
          <option value="tarjeta">Tarjeta</option>
        </select>
      </FormField>
    </FormModal>
  </div>
</template>
