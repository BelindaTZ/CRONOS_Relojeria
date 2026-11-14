<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import Pill from '@/shared/ui/Pill.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import {
  crearProgramada,
  listarProgramadas,
  listarProveedores,
  setEstadoProgramada,
} from '@/proveedores/services/proveedoresApi'
import LineasPedidoEditor from './LineasPedidoEditor.vue'

const columns = [
  { key: 'id', label: '#' },
  { key: 'proveedor_id', label: 'Proveedor' },
  { key: 'frecuencia', label: 'Frecuencia' },
  { key: 'proxima_generacion', label: 'Próxima generación' },
  { key: 'estado', label: 'Estado' },
]
const TONO = { activa: 'good', pausada: 'warn', cancelada: 'bad' }

const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const proveedores = ref([])
const sucursales = ref([])

const modal = reactive({
  abierto: false, guardando: false, error: '',
  proveedor_id: null, sucursal_destino_id: null, frecuencia: 'mensual',
})
const editor = ref(null)

function abrir() {
  modal.proveedor_id = null
  modal.sucursal_destino_id = null
  modal.frecuencia = 'mensual'
  modal.error = ''
  modal.abierto = true
}

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await listarProgramadas()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  const [pv, sc] = await Promise.all([listarProveedores({ estado: 'activo', page: 1 }), listarSucursales()])
  proveedores.value = pv.items
  sucursales.value = sc.items
  cargar()
})

const visibles = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return rows.value
  return rows.value.filter((r) => String(r.proveedor_id).includes(s) || r.frecuencia.includes(s))
})

async function guardar() {
  modal.error = ''
  if (!modal.proveedor_id || !modal.sucursal_destino_id) {
    return (modal.error = 'Completa proveedor y sucursal.')
  }
  let plantilla_lineas
  try {
    plantilla_lineas = editor.value.construirLineas()
  } catch (e) {
    return (modal.error = e.message)
  }
  modal.guardando = true
  try {
    await crearProgramada({
      proveedor_id: modal.proveedor_id,
      sucursal_destino_id: modal.sucursal_destino_id,
      frecuencia: modal.frecuencia,
      plantilla_lineas,
    })
    toast.success('Compra programada creada — generará una orden en borrador cada ciclo')
    modal.abierto = false
    cargar()
  } catch (e) {
    modal.error = e.message
  } finally {
    modal.guardando = false
  }
}

async function cambiarEstado(p, estado) {
  if (estado === 'pausada' && !(await confirm({
    title: 'Pausar la compra programada',
    message: 'Dejará de generar órdenes en borrador cada ciclo hasta que la reanudes. La programación y su plantilla se conservan.',
    confirmLabel: 'Pausar',
  }))) return
  if (estado === 'cancelada' && !(await confirm({
    title: 'Cancelar la compra programada',
    message: 'Detiene la programación de forma definitiva (no se puede reactivar). Las órdenes ya generadas no se tocan.',
    tone: 'danger', confirmLabel: 'Cancelar programación',
  }))) return
  try {
    await setEstadoProgramada(p.id, estado)
    const msg = { pausada: 'Programación pausada — no generará órdenes hasta que la reanudes.',
                  activa: 'Programación reanudada — volverá a generar órdenes cada ciclo.',
                  cancelada: 'Programación cancelada definitivamente.' }
    toast.success(msg[estado] || 'Estado actualizado')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const acciones = (p) => [
  { label: 'Pausar (deja de generar órdenes)', icon: 'clock', hidden: p.estado !== 'activa', onClick: () => cambiarEstado(p, 'pausada') },
  { label: 'Reanudar', icon: 'refresh-cw', hidden: p.estado !== 'pausada', onClick: () => cambiarEstado(p, 'activa') },
  { label: 'Cancelar definitivamente', icon: 'ban', danger: true, hidden: p.estado === 'cancelada', onClick: () => cambiarEstado(p, 'cancelada') },
]
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Abastecimiento"
      titulo="Compras programadas"
      sub="Generan una orden en borrador cada ciclo (semanal/mensual/trimestral); el sistema las revisa cada hora. «Pausar» las detiene temporalmente; «Cancelar» las detiene para siempre."
      :columns="columns"
      :rows="visibles"
      :total="visibles.length"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      :page-size="visibles.length || 1"
      search-placeholder="Filtrar…"
      :row-actions="acciones"
      empty-title="Sin compras programadas"
      empty-hint="Programa un abastecimiento recurrente (semanal, mensual o trimestral)."
      empty-icon="refresh-cw"
      @retry="cargar"
    >
      <template #actions>
        <RouterLink :to="{ name: 'compras' }" class="cr-btn cr-btn-ghost">Órdenes</RouterLink>
        <button class="cr-btn cr-btn-primary" @click="abrir">Nueva programada</button>
      </template>
      <template #cell-proxima_generacion="{ row }">{{ new Date(row.proxima_generacion).toLocaleDateString() }}</template>
      <template #cell-estado="{ row }"><Pill :tone="TONO[row.estado] || 'neutral'" :label="row.estado" /></template>
    </WorkPanel>

    <FormModal
      v-model="modal.abierto"
      titulo="Nueva compra programada"
      subtitulo="El sistema generará una orden en borrador con esta plantilla cada ciclo. Revísala y emítela cuando toque."
      :guardando="modal.guardando"
      ancho="max-w-3xl"
      @guardar="guardar"
    >
      <FormField label="Proveedor" required>
        <ComboBox v-model="modal.proveedor_id" :opciones="proveedores" opcion-label="razon_social" opcion-value="id" placeholder="Elegir…" />
      </FormField>
      <FormField label="Sucursal destino" required>
        <ComboBox v-model="modal.sucursal_destino_id" :opciones="sucursales" opcion-label="nombre" opcion-value="id" placeholder="Elegir…" />
      </FormField>
      <FormField label="Frecuencia" required>
        <select v-model="modal.frecuencia" class="cr-input">
          <option value="semanal">Semanal</option>
          <option value="mensual">Mensual</option>
          <option value="trimestral">Trimestral</option>
        </select>
      </FormField>

      <LineasPedidoEditor v-if="modal.abierto" ref="editor" :con-serie="false" />

      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
