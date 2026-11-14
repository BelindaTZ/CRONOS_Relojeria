<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import {
  listarEspecialidades,
  listarTecnicos,
  setEstadoTecnico,
} from '@/tecnicos/services/tecnicosApi'
import TecnicoFormModal from './TecnicoFormModal.vue'
import EsquemaCostoModal from './EsquemaCostoModal.vue'

const router = useRouter()
const session = useSessionStore()

const columns = [
  { key: 'nombre', label: 'Técnico' },
  { key: 'especialidades', label: 'Especialidades' },
  { key: 'sucursal_ids', label: 'Sucursales', align: 'right' },
  { key: 'tarifa', label: 'Tarifa / h', align: 'right' },
  { key: 'estado', label: 'Estado' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const page = ref(1)
const especialidades = ref([])
const sucursales = ref([])
const fEspecialidad = ref('')
const fSucursal = ref('')

const modalForm = ref({ abierto: false, tecnico: null })
const modalCosto = ref({ abierto: false, tecnico: null })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarTecnicos({
      q: q.value || undefined,
      especialidad: fEspecialidad.value || undefined,
      sucursal_id: fSucursal.value || undefined,
      page: page.value,
    })
    rows.value = res.items
    total.value = res.total
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  ;[especialidades.value, sucursales.value] = await Promise.all([
    listarEspecialidades().catch(() => []),
    listarSucursales().then((r) => r.items).catch(() => []),
  ])
  cargar()
})
let t
watch([q, fEspecialidad, fSucursal], () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 250)
})
watch(page, cargar)

const sucursalNombre = (id) => sucursales.value.find((s) => s.id === id)?.nombre ?? `#${id}`

const kpis = computed(() => {
  const activos = rows.value.filter((x) => x.estado === 'activo').length
  const conCosto = rows.value.filter((x) => x.costo_vigente).length
  return [
    { label: 'Técnicos (esta página)', value: String(rows.value.length) },
    { label: 'Activos', value: String(activos) },
    { label: 'Con esquema de costo', value: String(conCosto), sub: 'necesario para costear OT' },
    { label: 'Especialidades', value: String(especialidades.value.length), gold: true },
  ]
})

async function cambiarEstado(x) {
  const inactivar = x.estado === 'activo'
  if (inactivar && !(await confirm({
    title: `Inactivar a ${x.nombre}`,
    message: 'El técnico no se elimina: queda inactivo y sale de la asignación de órdenes de trabajo. Su historial y bonos se conservan.',
    confirmLabel: 'Inactivar', tone: 'danger',
  }))) return
  try {
    await setEstadoTecnico(x.id, inactivar ? 'inactivo' : 'activo')
    toast.success(inactivar ? `${x.nombre} inactivado` : `${x.nombre} reactivado`)
    cargar()
  } catch (e) {
    toast.error(e.status === 403 ? 'Requiere Técnico Jefe o Gerencia General.' : e.message)
  }
}

// Solo Gerencia General/Técnico Jefe tienen tecnicos:editar en la matriz RBAC
// (0024) — antes se mostraban estas acciones a cualquiera que pudiera VER la
// lista (p. ej. Vendedor, con tecnicos:consultar tras el fix de 2026-09-11) y
// el backend recién las rechazaba al enviarlas (403 después de llenar el
// formulario). Gatearlas aquí evita ese callejón sin salida.
const acciones = (x) => {
  const base = [{ label: 'Ver ficha', icon: 'chevron-right', onClick: () => router.push({ name: 'tecnico-ficha', params: { id: x.id } }) }]
  if (!session.puede('tecnicos', 'editar')) return base
  return [
    ...base,
    { label: 'Editar', icon: 'edit', onClick: () => (modalForm.value = { abierto: true, tecnico: x }) },
    { label: 'Fijar costo interno', icon: 'trending-up', onClick: () => (modalCosto.value = { abierto: true, tecnico: x }) },
    { label: x.estado === 'activo' ? 'Inactivar' : 'Reactivar', icon: x.estado === 'activo' ? 'ban' : 'refresh-cw', danger: x.estado === 'activo', onClick: () => cambiarEstado(x) },
  ]
}
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Técnicos"
      titulo="Personal técnico"
      sub="RRHH del taller: especialidades, sucursales y costo interno de mano de obra (base del costeo de las órdenes de trabajo)."
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Nombre o certificación…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay técnicos registrados"
      empty-hint="Registra a los relojeros del taller para poder asignarles órdenes de trabajo y costear la mano de obra."
      empty-icon="users"
      @retry="cargar"
      @row-click="(x) => router.push({ name: 'tecnico-ficha', params: { id: x.id } })"
    >
      <template #actions>
        <button v-if="session.puede('tecnicos', 'crear')" class="cr-btn cr-btn-primary" @click="modalForm = { abierto: true, tecnico: null }">Agregar técnico</button>
      </template>
      <template #toolbar>
        <select v-model="fEspecialidad" class="cr-input max-w-[12rem]">
          <option value="">Todas las especialidades</option>
          <option v-for="e in especialidades" :key="e.id" :value="e.nombre">{{ e.nombre }}</option>
        </select>
        <select v-model="fSucursal" class="cr-input max-w-[11rem]">
          <option value="">Todas las sucursales</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </template>

      <template #cell-nombre="{ row }">
        <span class="font-medium text-ink" :class="{ 'text-ink-3 line-through': row.estado !== 'activo' }">{{ row.nombre }}</span>
        <span v-if="row.usuario_id" class="ml-1.5 text-xs text-ink-3">· con acceso</span>
      </template>
      <template #cell-especialidades="{ row }">
        <span v-if="!row.especialidades.length" class="text-ink-3">—</span>
        <span v-else class="flex flex-wrap gap-1">
          <span v-for="e in row.especialidades.slice(0, 3)" :key="e" class="rounded-full bg-surface-sunk px-2 py-0.5 text-xs text-ink-2">{{ e }}</span>
          <span v-if="row.especialidades.length > 3" class="text-xs text-ink-3">+{{ row.especialidades.length - 3 }}</span>
        </span>
      </template>
      <template #cell-sucursal_ids="{ row }">
        <span class="tabular-nums text-ink-2" :title="row.sucursal_ids.map(sucursalNombre).join(', ')">{{ row.sucursal_ids.length }}</span>
      </template>
      <template #cell-tarifa="{ row }">
        <span v-if="row.costo_vigente" class="tabular-nums text-ink">$ {{ Number(row.costo_vigente.tarifa_hora).toLocaleString() }}</span>
        <span v-else-if="row.costos_visibles" class="text-ink-3">sin fijar</span>
        <span v-else class="inline-flex items-center gap-1 text-ink-3"><CrIcon name="lock" :size="12" /> restringido</span>
      </template>
      <template #cell-estado="{ row }">
        <Pill :tone="row.estado === 'activo' ? 'good' : 'neutral'" :label="row.estado" />
      </template>
    </WorkPanel>

    <TecnicoFormModal v-model="modalForm.abierto" :tecnico="modalForm.tecnico" @guardado="cargar" />
    <EsquemaCostoModal
      v-if="modalCosto.tecnico"
      v-model="modalCosto.abierto"
      :tecnico="modalCosto.tecnico"
      @guardado="cargar"
    />
  </div>
</template>
