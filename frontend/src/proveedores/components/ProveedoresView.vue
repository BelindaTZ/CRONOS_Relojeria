<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import Pill from '@/shared/ui/Pill.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import ProveedorFormFields from './ProveedorFormFields.vue'
import {
  actualizarProveedor,
  crearProveedor,
  inactivarProveedor,
  listarProveedores,
} from '@/proveedores/services/proveedoresApi'

const TIPOS = ['relojes', 'piezas_originales', 'piezas_no_originales', 'lubricantes', 'herramientas']
const router = useRouter()
const session = useSessionStore()

const columns = [
  { key: 'razon_social', label: 'Proveedor' },
  { key: 'ruc_nit', label: 'RUC / NIT' },
  { key: 'tipos', label: 'Tipos' },
  { key: 'condicion_pago', label: 'Pago' },
  { key: 'cumplimiento', label: 'Cumplimiento', align: 'right' },
  { key: 'estado', label: 'Estado' },
]

const rows = ref([])
const total = ref(0)
const totalActivos = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const filtroTipo = ref('')
const page = ref(1)

function vacio() {
  return {
    razon_social: '', ruc_nit: '', nombre_comercial: '', contacto_nombre: '', telefono: '',
    email: '', condicion_pago_id: null, certificacion_autorizada: false, marcas_autorizadas: [], tipos: [],
  }
}

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const [res, activos] = await Promise.all([
      listarProveedores({ q: q.value || undefined, tipo: filtroTipo.value || undefined, page: page.value }),
      listarProveedores({ estado: 'activo', page: 1 }),
    ])
    rows.value = res.items
    total.value = res.total
    totalActivos.value = activos.total
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
let t
watch([q, filtroTipo], () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 250)
})
watch(page, cargar)

const kpis = computed(() => {
  const conInd = rows.value.filter((p) => p.indicador_plazos_dias != null)
  const prom = conInd.length
    ? (conInd.reduce((s, p) => s + Number(p.indicador_plazos_dias), 0) / conInd.length).toFixed(1)
    : null
  return [
    { label: 'Proveedores', value: String(total.value) },
    { label: 'Activos', value: String(totalActivos.value) },
    { label: 'Cumplimiento prom.', value: prom == null ? '—' : `${Number(prom) > 0 ? '+' : ''}${prom} d`, gold: true },
  ]
})

const modal = reactive({ abierto: false, editId: null, guardando: false, error: '' })
const form = reactive(vacio())

function abrirAlta() {
  Object.assign(form, vacio())
  modal.editId = null
  modal.error = ''
  modal.abierto = true
}
function abrirEdicion(p) {
  Object.assign(form, {
    razon_social: p.razon_social, ruc_nit: p.ruc_nit ?? '', nombre_comercial: p.nombre_comercial ?? '',
    contacto_nombre: p.contacto_nombre ?? '', telefono: p.telefono ?? '', email: p.email ?? '',
    condicion_pago_id: p.condicion_pago_id ?? null,
    certificacion_autorizada: p.certificacion_autorizada,
    marcas_autorizadas: [...(p.marcas_autorizadas || [])], tipos: [...p.tipos],
  })
  modal.editId = p.id
  modal.error = ''
  modal.abierto = true
}

async function guardar() {
  modal.guardando = true
  modal.error = ''
  try {
    const payload = { ...form }
    if (modal.editId) {
      await actualizarProveedor(modal.editId, payload)
      toast.success('Proveedor actualizado')
      modal.abierto = false
      cargar()
    } else {
      const p = await crearProveedor(payload)
      toast.success('Proveedor creado')
      modal.abierto = false
      router.push({ name: 'proveedor-ficha', params: { id: p.id } })
    }
  } catch (e) {
    modal.error =
      e.status === 409 ? 'Ya existe un proveedor con ese RUC/NIT.' :
      e.status === 403 ? 'Razón social y RUC/NIT solo los cambia un rol elevado.' : e.message
  } finally {
    modal.guardando = false
  }
}

async function inactivar(p) {
  const ok = await confirm({
    title: `Inactivar «${p.razon_social}»`,
    message: 'El proveedor no se elimina; queda inactivo y sale de los selectores. Sus órdenes y su historial se conservan.',
    confirmLabel: 'Inactivar',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await inactivarProveedor(p.id)
    toast.success(`«${p.razon_social}» inactivado`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const acciones = (p) => [
  { label: 'Ver ficha', icon: 'chevron-right', onClick: () => router.push({ name: 'proveedor-ficha', params: { id: p.id } }) },
  { label: 'Editar', icon: 'edit', onClick: () => abrirEdicion(p) },
  { label: 'Inactivar', icon: 'ban', danger: true, hidden: p.estado !== 'activo', onClick: () => inactivar(p) },
]
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Abastecimiento"
      titulo="Proveedores"
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Nombre, RUC/NIT, email o teléfono…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay proveedores"
      empty-hint="Registra un proveedor para poder emitirle órdenes de compra."
      empty-icon="truck"
      @retry="cargar"
      @row-click="(p) => router.push({ name: 'proveedor-ficha', params: { id: p.id } })"
    >
      <template #actions>
        <RouterLink :to="{ name: 'compras' }" class="cr-btn cr-btn-ghost">Órdenes de compra</RouterLink>
        <button v-if="!session.esGerencia" class="cr-btn cr-btn-primary" @click="abrirAlta">Agregar proveedor</button>
      </template>

      <template #toolbar>
        <select v-model="filtroTipo" class="cr-input max-w-[13rem]">
          <option value="">Todos los tipos</option>
          <option v-for="tp in TIPOS" :key="tp" :value="tp">{{ tp.replace(/_/g, ' ') }}</option>
        </select>
      </template>

      <template #cell-tipos="{ row }">
        <span class="text-ink-3">{{ row.tipos.map((x) => x.replace(/_/g, ' ')).join(', ') || '—' }}</span>
      </template>
      <template #cell-cumplimiento="{ row }">
        <span v-if="row.indicador_plazos_dias != null">{{ Number(row.indicador_plazos_dias) > 0 ? '+' : '' }}{{ row.indicador_plazos_dias }} d</span>
        <span v-else class="text-ink-3">—</span>
      </template>
      <template #cell-estado="{ row }">
        <Pill :tone="row.estado === 'activo' ? 'good' : 'bad'" :label="row.estado" />
      </template>
    </WorkPanel>

    <FormModal
      v-model="modal.abierto"
      :titulo="modal.editId ? 'Editar proveedor' : 'Nuevo proveedor'"
      :guardando="modal.guardando"
      :sucio="form.razon_social.length > 0"
      ancho="max-w-2xl"
      @guardar="guardar"
    >
      <ProveedorFormFields :model-value="form" :edicion="!!modal.editId" :error="modal.error" />
    </FormModal>
  </div>
</template>
