<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import Pill from '@/shared/ui/Pill.vue'
import { prompt } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { crearSucursal, inactivarSucursal, listarSucursales } from '@/sucursales/services/sucursalesApi'
import { listarUsuarios } from '@/usuarios'
import HorarioModal from '@/sucursales/components/HorarioModal.vue'

const columns = [
  { key: 'nombre', label: 'Sucursal' },
  { key: 'direccion', label: 'Dirección' },
  { key: 'estado', label: 'Estado' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const responsables = ref([])

const modal = reactive({ abierto: false, guardando: false, error: '', nombre: '', direccion: '', responsable_usuario_id: null })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarSucursales({ q: q.value || undefined })
    rows.value = res.items
    total.value = res.total
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  responsables.value = await listarUsuarios({ page: 1 }).then((r) => r.items).catch(() => [])
  cargar()
})
let t
function onSearch(v) {
  q.value = v
  clearTimeout(t)
  t = setTimeout(cargar, 250)
}

const kpis = computed(() => [
  { label: 'Sucursales', value: String(total.value) },
  { label: 'Activas', value: String(rows.value.filter((s) => s.estado === 'activa').length) },
])

function abrirAlta() {
  Object.assign(modal, { abierto: true, guardando: false, error: '', nombre: '', direccion: '', responsable_usuario_id: null })
}
async function crear() {
  modal.error = ''
  modal.guardando = true
  try {
    await crearSucursal({
      nombre: modal.nombre.trim(),
      direccion: modal.direccion.trim() || null,
      responsable_usuario_id: modal.responsable_usuario_id,
    })
    toast.success('Sucursal creada')
    modal.abierto = false
    cargar()
  } catch (e) {
    modal.error = e.status === 409 ? 'Ya existe una sucursal con ese nombre.' : e.message
  } finally {
    modal.guardando = false
  }
}

async function inactivar(s) {
  const motivo = await prompt({
    title: `Inactivar «${s.nombre}»`,
    message: 'Se avisará por correo a todo el personal asignado. Sus datos históricos se conservan.',
    label: 'Motivo (obligatorio)',
  })
  if (!motivo) return
  try {
    await inactivarSucursal(s.id, motivo)
    toast.success('Sucursal inactivada · personal notificado')
    cargar()
  } catch (e) {
    toast.error(e.status === 422 ? 'El motivo es obligatorio (mín. 5 caracteres).' : e.message)
  }
}

const horarioModal = reactive({ abierto: false, sucursal: null })
function abrirHorario(s) {
  horarioModal.sucursal = s
  horarioModal.abierto = true
}

const acciones = (s) => [
  { label: 'Horario de atención', icon: 'clock', onClick: () => abrirHorario(s) },
  { label: 'Inactivar', icon: 'ban', danger: true, hidden: s.estado !== 'activa', onClick: () => inactivar(s) },
]
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Sistema"
      titulo="Sucursales"
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      :search="q"
      :page-size="rows.length || 1"
      search-placeholder="Nombre o dirección…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay sucursales"
      empty-icon="building"
      @update:search="onSearch"
      @retry="cargar"
    >
      <template #actions><button class="cr-btn cr-btn-primary" @click="abrirAlta">Agregar sucursal</button></template>
      <template #cell-direccion="{ row }">{{ row.direccion || '—' }}</template>
      <template #cell-estado="{ row }">
        <div class="flex items-center gap-2">
          <Pill :tone="row.estado === 'activa' ? 'good' : 'bad'" :label="row.estado" />
          <span v-if="row.motivo_inactivacion" class="text-xs text-ink-3">{{ row.motivo_inactivacion }}</span>
        </div>
      </template>
    </WorkPanel>

    <FormModal v-model="modal.abierto" titulo="Nueva sucursal" :guardando="modal.guardando" ancho="max-w-md" @guardar="crear">
      <FormField label="Nombre" required wide><input v-model="modal.nombre" class="cr-input" minlength="2" required /></FormField>
      <FormField label="Dirección" wide><input v-model="modal.direccion" class="cr-input" /></FormField>
      <FormField label="Responsable" wide helper="Usuario a cargo de la sucursal">
        <ComboBox v-model="modal.responsable_usuario_id" :opciones="responsables" opcion-label="nombre" opcion-value="id" placeholder="Elegir usuario…" />
      </FormField>
      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>

    <HorarioModal v-model="horarioModal.abierto" :sucursal="horarioModal.sucursal" />
  </div>
</template>
