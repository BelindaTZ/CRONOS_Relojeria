<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { opcionesExportacion } from '@/shared/exportar'
import { getAgingCxp, listarCxp, registrarPagoCxp } from '@/contabilidad/services/contabilidadApi'

const session = useSessionStore()

const columns = [
  { key: 'contraparte', label: 'Contraparte' },
  { key: 'origen', label: 'Origen' },
  { key: 'monto', label: 'Monto original', align: 'right' },
  { key: 'saldo', label: 'Saldo', align: 'right' },
  { key: 'dias', label: 'Días' },
]
const rows = ref([])
const aging = ref(null)
const loading = ref(true)
const fOrigen = ref('')
const modal = ref({ abierto: false, cxp: null })
const f = reactive({ monto: null, medio_pago: 'efectivo', retencion_monto: null })

async function cargar() {
  loading.value = true
  ;[rows.value, aging.value] = await Promise.all([
    listarCxp({ estado: 'pendiente', origen_tipo: fOrigen.value || undefined }).catch(() => []),
    getAgingCxp().catch(() => null),
  ])
  loading.value = false
}
onMounted(cargar)

const kpis = computed(() => aging.value ? [
  ...aging.value.tramos.map((t) => ({ label: t.tramo + ' días', value: `${t.cantidad} · ${dinero(t.saldo)}` })),
  { label: 'Total por pagar', value: dinero(aging.value.total), gold: true },
] : [])
const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => rows.value.map((r) => ({
      contraparte: r.proveedor_nombre || r.beneficiario_nombre,
      origen: `${r.origen_tipo === 'orden_compra' ? 'Compra' : 'Gasto'} #${r.orden_compra_id || r.gasto_id}`,
      monto_original: r.monto_original, saldo: r.saldo, dias: r.dias,
    })),
    totalFilas: rows.value.length,
    imprimirPdf: () => window.print(),
  }),
)

function abrirModal(c) { modal.value = { abierto: true, cxp: c }; f.monto = c.saldo; f.medio_pago = 'efectivo'; f.retencion_monto = null }
async function guardarPago() {
  if (!f.monto || Number(f.monto) <= 0) return toast.error('Indica el monto.')
  try {
    await registrarPagoCxp(modal.value.cxp.id, {
      monto: Number(f.monto), medio_pago: f.medio_pago,
      retencion: f.retencion_monto ? { monto: Number(f.retencion_monto) } : null,
    })
    toast.success('Pago registrado')
    modal.value.abierto = false
    cargar()
  } catch (e) {
    toast.error(e.status === 403 ? 'Requiere Gerencia General o Contador.' : e.message)
  }
}
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Contabilidad"
      titulo="Cuentas por pagar"
      sub="Subledger con aging, de compras a proveedores (002) y de gastos «por pagar» (a proveedor o beneficiario). Solo Gerencia General o Contador registra pagos."
      :columns="columns"
      :rows="rows"
      :total="rows.length"
      :loading="loading"
      :page-size="200"
      :kpis="kpis"
      :row-actions="(c) => [{ label: 'Registrar pago', icon: 'circle-check', hidden: !session.puede('contable', 'editar'), onClick: () => abrirModal(c) }]"
      empty-title="Sin cuentas por pagar pendientes"
      empty-icon="inbox"
      @retry="cargar"
    >
      <template #toolbar>
        <select v-model="fOrigen" class="cr-input max-w-[12rem]" @change="cargar">
          <option value="">Compras y gastos</option>
          <option value="orden_compra">Compras</option>
          <option value="gasto">Gastos</option>
        </select>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
      <template #cell-contraparte="{ row }">{{ row.proveedor_nombre || row.beneficiario_nombre }}</template>
      <template #cell-origen="{ row }">{{ row.origen_tipo === 'orden_compra' ? 'Compra' : 'Gasto' }} #{{ row.orden_compra_id || row.gasto_id }}</template>
      <template #cell-monto="{ row }"><span class="tabular-nums">{{ dinero(row.monto_original) }}</span></template>
      <template #cell-saldo="{ row }"><span class="tabular-nums text-warn">{{ dinero(row.saldo) }}</span></template>
      <template #cell-dias="{ row }">{{ row.dias }}</template>
    </WorkPanel>

    <FormModal
      :model-value="modal.abierto" titulo="Registrar pago" :guardando="false" ancho="max-w-md" :sucio="true"
      @update:model-value="modal.abierto = $event" @guardar="guardarPago"
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
      <FormField label="Retención en la fuente" wide helper="Monto retenido, si aplica (sin cálculo fiscal automático).">
        <input v-model="f.retencion_monto" type="number" step="0.01" min="0" class="cr-input tabular-nums" />
      </FormField>
    </FormModal>
  </div>
</template>
