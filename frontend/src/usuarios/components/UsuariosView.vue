<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CheckList from '@/shared/ui/CheckList.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm, prompt } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { listarRoles } from '@/rbac'
import { listarSucursales } from '@/sucursales'
import {
  actualizarUsuario,
  crearUsuario,
  listarUsuarios,
  setRoles,
  setSucursales,
} from '@/usuarios/services/usuariosApi'

const columns = [
  { key: 'nombre', label: 'Nombre' },
  { key: 'identificacion', label: 'Identificación' },
  { key: 'email', label: 'Email' },
  { key: 'roles', label: 'Roles' },
  { key: 'estado', label: 'Estado' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const page = ref(1)
const roles = ref([])
const sucursales = ref([])

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarUsuarios({ q: q.value || undefined, page: page.value })
    rows.value = res.items
    total.value = res.total
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  ;[roles.value, sucursales.value] = await Promise.all([
    listarRoles(),
    listarSucursales().then((r) => r.items),
  ])
  cargar()
})
let t
watch(q, () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 250)
})
watch(page, cargar)

const kpis = computed(() => [
  { label: 'Usuarios', value: String(total.value) },
  { label: 'Activos', value: String(rows.value.filter((u) => u.estado === 'activo').length), sub: 'en esta página' },
])

// --- alta ---
const alta = reactive({ abierto: false, guardando: false, error: '', identificacion: '', nombre: '', email: '', rol_ids: [] })
function abrirAlta() {
  Object.assign(alta, { abierto: true, guardando: false, error: '', identificacion: '', nombre: '', email: '', rol_ids: [] })
}
async function crear() {
  alta.error = ''
  alta.guardando = true
  try {
    const u = await crearUsuario({
      identificacion: alta.identificacion.trim(), nombre: alta.nombre.trim(),
      email: alta.email.trim(), rol_ids: alta.rol_ids,
    })
    alta.abierto = false
    cargar()
    await prompt({
      title: `Usuario «${u.nombre}» creado`,
      message: 'Contraseña temporal (se muestra una sola vez y también se envió por correo). El usuario deberá cambiarla en el primer acceso.',
      label: 'Contraseña temporal',
      initialValue: u.password_temporal,
      required: false,
      confirmLabel: 'Listo',
    })
  } catch (e) {
    alta.error = e.status === 409 ? 'La identificación o el email ya están en uso.' : e.message
  } finally {
    alta.guardando = false
  }
}

// --- editar roles / sucursales ---
const asig = reactive({ abierto: false, tipo: '', usuario: null, ids: [], guardando: false, error: '' })
function abrirAsignar(u, tipo) {
  asig.tipo = tipo
  asig.usuario = u
  asig.error = ''
  const nombres = tipo === 'roles' ? u.roles : u.sucursales
  const fuente = tipo === 'roles' ? roles.value : sucursales.value
  asig.ids = fuente.filter((x) => nombres.includes(x.nombre)).map((x) => x.id)
  asig.abierto = true
}
async function guardarAsignacion() {
  asig.guardando = true
  asig.error = ''
  try {
    if (asig.tipo === 'roles') await setRoles(asig.usuario.id, asig.ids)
    else await setSucursales(asig.usuario.id, asig.ids)
    toast.success('Asignación actualizada')
    asig.abierto = false
    cargar()
  } catch (e) {
    asig.error = e.status === 409 ? 'Anti-lockout: no se puede dejar el sistema sin Gerencia General activo.' : e.message
  } finally {
    asig.guardando = false
  }
}

async function alternarEstado(u) {
  const nuevo = u.estado === 'activo' ? 'inactivo' : 'activo'
  const ok = await confirm({
    title: `${nuevo === 'inactivo' ? 'Desactivar' : 'Activar'} a «${u.nombre}»`,
    message: nuevo === 'inactivo' ? 'No podrá iniciar sesión hasta reactivarlo.' : 'Podrá volver a iniciar sesión.',
    tone: nuevo === 'inactivo' ? 'danger' : 'primary',
    confirmLabel: nuevo === 'inactivo' ? 'Desactivar' : 'Activar',
  })
  if (!ok) return
  try {
    await actualizarUsuario(u.id, { estado: nuevo })
    toast.success('Estado actualizado')
    cargar()
  } catch (e) {
    toast.error(e.status === 409 ? 'Es el único Gerencia General activo: no se puede desactivar.' : e.message)
  }
}

const acciones = (u) => [
  { label: 'Editar roles', icon: 'users', onClick: () => abrirAsignar(u, 'roles') },
  { label: 'Editar sucursales', icon: 'building', onClick: () => abrirAsignar(u, 'sucursales') },
  { label: u.estado === 'activo' ? 'Desactivar' : 'Activar', icon: u.estado === 'activo' ? 'ban' : 'check', danger: u.estado === 'activo', onClick: () => alternarEstado(u) },
]
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Sistema"
      titulo="Usuarios"
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Nombre, identificación o email…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay usuarios"
      empty-icon="users"
      @retry="cargar"
    >
      <template #actions>
        <button class="cr-btn cr-btn-primary" @click="abrirAlta">Agregar usuario</button>
      </template>
      <template #cell-roles="{ row }">
        <span class="text-ink-3">{{ row.roles.join(', ') || '—' }}</span>
      </template>
      <template #cell-estado="{ row }">
        <Pill :tone="row.estado === 'activo' ? 'good' : 'bad'" :label="row.estado" />
      </template>
    </WorkPanel>

    <FormModal v-model="alta.abierto" titulo="Nuevo usuario" subtitulo="El sistema genera la contraseña temporal." :guardando="alta.guardando" @guardar="crear">
      <FormField label="Identificación" required helper="Cédula o RUC">
        <input v-model="alta.identificacion" class="cr-input" required minlength="5" />
      </FormField>
      <FormField label="Nombre completo" required>
        <input v-model="alta.nombre" class="cr-input" required minlength="2" />
      </FormField>
      <FormField label="Correo electrónico" required wide>
        <input v-model="alta.email" type="email" class="cr-input" required />
      </FormField>
      <FormField label="Roles" wide>
        <CheckList v-model="alta.rol_ids" :opciones="roles" />
      </FormField>
      <p v-if="alta.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ alta.error }}</p>
    </FormModal>

    <FormModal
      v-model="asig.abierto"
      :titulo="asig.tipo === 'roles' ? `Roles de ${asig.usuario?.nombre}` : `Sucursales de ${asig.usuario?.nombre}`"
      :guardando="asig.guardando"
      ancho="max-w-md"
      @guardar="guardarAsignacion"
    >
      <div class="sm:col-span-2">
        <CheckList
          v-model="asig.ids"
          :opciones="asig.tipo === 'roles' ? roles : sucursales"
        />
        <p v-if="asig.error" class="mt-2 text-sm text-bad" role="alert">{{ asig.error }}</p>
      </div>
    </FormModal>
  </div>
</template>
