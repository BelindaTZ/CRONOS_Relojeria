<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarClientes, listarNiveles, setEstadoCliente } from '@/clientes/services/clientesApi'
import ClienteFormModal from './ClienteFormModal.vue'

const router = useRouter()
const session = useSessionStore()

const columns = [
  { key: 'nombre', label: 'Cliente' },
  { key: 'identificacion', label: 'Cédula / RUC' },
  { key: 'numero_afiliado', label: 'N.º afiliado' },
  { key: 'nivel', label: 'Fidelización' },
  { key: 'estado', label: 'Estado' },
]

const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const page = ref(1)
const niveles = ref([])
const fNivel = ref('')
const modalForm = ref({ abierto: false, cliente: null })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarClientes({ q: q.value || undefined, nivel_id: fNivel.value || undefined, page: page.value })
    rows.value = res.items
    total.value = res.total
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  niveles.value = await listarNiveles().catch(() => [])
  cargar()
})
let t
watch([q, fNivel], () => {
  clearTimeout(t)
  page.value = 1
  t = setTimeout(cargar, 250)
})
watch(page, cargar)

const kpis = computed(() => {
  const activos = rows.value.filter((c) => c.estado === 'activo').length
  return [
    { label: 'Clientes (esta página)', value: String(rows.value.length) },
    { label: 'Activos', value: String(activos) },
    { label: 'Niveles configurados', value: String(niveles.value.length) },
    { label: 'Total registrados', value: String(total.value), gold: true },
  ]
})

async function cambiarEstado(c) {
  const inactivar = c.estado === 'activo'
  if (inactivar && !(await confirm({
    title: `Inactivar a ${c.nombre}`,
    message: 'El cliente no se elimina: queda inactivo y sale de los selectores de citas, servicio y ventas. Su historial se conserva.',
    confirmLabel: 'Inactivar', tone: 'danger',
  }))) return
  try {
    await setEstadoCliente(c.id, inactivar ? 'inactivo' : 'activo')
    toast.success(inactivar ? `${c.nombre} inactivado` : `${c.nombre} reactivado`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const acciones = (c) => [
  { label: 'Ver ficha', icon: 'chevron-right', onClick: () => router.push({ name: 'cliente-ficha', params: { id: c.id } }) },
  { label: 'Historial', icon: 'history', onClick: () => router.push({ name: 'cliente-historial', params: { id: c.id } }) },
  { label: 'Editar', icon: 'edit', onClick: () => (modalForm.value = { abierto: true, cliente: c }) },
  { label: c.estado === 'activo' ? 'Inactivar' : 'Reactivar', icon: c.estado === 'activo' ? 'ban' : 'refresh-cw', danger: c.estado === 'activo', onClick: () => cambiarEstado(c) },
]
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Clientes"
      titulo="Clientes y fidelización"
      sub="CRM del negocio: identificación, contacto, nivel de fidelización y consentimiento de datos. Base de citas, servicio técnico y ventas."
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      v-model:page="page"
      :page-size="20"
      search-placeholder="Nombre, cédula/RUC, email, teléfono o N.º de afiliado…"
      :kpis="kpis"
      :row-actions="acciones"
      empty-title="Aún no hay clientes registrados"
      empty-hint="Registra a los clientes para vincular sus compras, servicios y beneficios de fidelización."
      empty-icon="users"
      @retry="cargar"
      @row-click="(c) => router.push({ name: 'cliente-ficha', params: { id: c.id } })"
    >
      <template #actions>
        <RouterLink :to="{ name: 'reportes-clientes' }" class="cr-btn cr-btn-ghost">Reportes</RouterLink>
        <button v-if="!session.esGerencia" class="cr-btn cr-btn-primary" @click="modalForm = { abierto: true, cliente: null }">Agregar cliente</button>
      </template>
      <template #toolbar>
        <select v-model="fNivel" class="cr-input max-w-[12rem]">
          <option value="">Todos los niveles</option>
          <option v-for="n in niveles" :key="n.id" :value="n.id">{{ n.nombre }}</option>
        </select>
      </template>

      <template #cell-nombre="{ row }">
        <span class="font-medium text-ink" :class="{ 'text-ink-3 line-through': row.estado !== 'activo' }">{{ row.nombre }}</span>
        <span class="ml-1.5 text-xs text-ink-3">{{ row.tipo === 'juridica' ? 'jurídica' : 'natural' }}</span>
      </template>
      <template #cell-identificacion="{ row }"><span class="tabular-nums">{{ row.identificacion }}</span></template>
      <template #cell-numero_afiliado="{ row }"><span class="tabular-nums text-ink-2">{{ row.numero_afiliado }}</span></template>
      <template #cell-nivel="{ row }">
        <span
          v-if="row.nivel_nombre"
          class="inline-flex items-center rounded-full border border-gold/50 bg-gold-pale px-2.5 py-0.5 text-xs font-medium text-gold-strong"
        >{{ row.nivel_nombre }}</span>
        <span v-else class="text-ink-3">—</span>
      </template>
      <template #cell-estado="{ row }"><Pill :tone="row.estado === 'activo' ? 'good' : 'neutral'" :label="row.estado" /></template>
    </WorkPanel>

    <ClienteFormModal v-model="modalForm.abierto" :cliente="modalForm.cliente" @guardado="cargar" />
  </div>
</template>
