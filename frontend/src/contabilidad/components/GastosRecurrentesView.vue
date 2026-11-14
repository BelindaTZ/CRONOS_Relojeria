<script setup>
import { onMounted, reactive, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import { listarCategoriasGasto } from '@/configuracion'

const session = useSessionStore()
import {
  crearBeneficiario,
  crearGastoRecurrente,
  listarBeneficiarios,
  listarGastosRecurrentes,
  setEstadoGastoRecurrente,
} from '@/contabilidad/services/contabilidadApi'

const TONO = { activo: 'good', pausado: 'warn', cancelado: 'bad' }
const rows = ref([])
const loading = ref(true)
const modal = ref(false)
const sucursales = ref([])
const categorias = ref([])
const beneficiarios = ref([])

async function cargar() {
  loading.value = true
  rows.value = await listarGastosRecurrentes().catch(() => [])
  loading.value = false
}
onMounted(async () => {
  ;[sucursales.value, categorias.value, beneficiarios.value] = await Promise.all([
    listarSucursales().then((r) => r.items).catch(() => []),
    listarCategoriasGasto().catch(() => []),
    listarBeneficiarios().catch(() => []),
  ])
  cargar()
})

async function cambiarEstado(g, estado) {
  const etiqueta = { activo: 'reactivar', pausado: 'pausar', cancelado: 'cancelar' }[estado]
  if (!(await confirm({ title: `¿${etiqueta} "${g.descripcion}"?`, message: estado === 'cancelado' ? 'No se puede reactivar un recurrente cancelado.' : '', confirmLabel: etiqueta }))) return
  try {
    await setEstadoGastoRecurrente(g.id, estado)
    toast.success('Estado actualizado')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

function vacio() {
  return { categoria_gasto_id: null, sucursal_id: null, beneficiario_id: null, descripcion: '',
          monto_estimado: null, frecuencia: 'mensual', proxima_generacion: new Date().toISOString().slice(0, 10) }
}
const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')

async function nuevoBeneficiario(nombre) {
  try {
    const b = await crearBeneficiario({ nombre, identificacion: null, tipo_servicio: null })
    beneficiarios.value.push(b)
    return b
  } catch (e) {
    toast.error(e.message)
    return null
  }
}

async function guardar() {
  error.value = ''
  if (!f.categoria_gasto_id || !f.sucursal_id) return (error.value = 'Completa categoría y sucursal.')
  if (!f.beneficiario_id) return (error.value = 'Elige el beneficiario o proveedor.')
  if (!f.descripcion.trim() || !f.monto_estimado) return (error.value = 'Completa descripción y monto estimado.')
  guardando.value = true
  try {
    await crearGastoRecurrente({
      categoria_gasto_id: f.categoria_gasto_id, sucursal_id: f.sucursal_id, beneficiario_id: f.beneficiario_id,
      descripcion: f.descripcion.trim(), monto_estimado: Number(f.monto_estimado), frecuencia: f.frecuencia,
      proxima_generacion: f.proxima_generacion,
    })
    toast.success('Gasto recurrente creado')
    modal.value = false
    Object.assign(f, vacio())
    cargar()
  } catch (e) {
    error.value = e.status === 403 ? 'Los gastos recurrentes requieren Gerencia General o Contador.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Contabilidad"
      titulo="Gastos recurrentes"
      sub="Agua, wifi, arriendo, teléfono… se repiten cada periodo. En cada ciclo se genera un gasto en borrador para que lo confirmes con el monto real."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'gastos' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Gastos</RouterLink>
        <button v-if="session.puede('contable', 'crear')" class="cr-btn cr-btn-primary" @click="modal = true">Nuevo recurrente</button>
      </template>
    </PageHeader>

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!rows.length" class="cr-card p-8 text-center text-ink-3">Sin gastos recurrentes configurados.</p>
    <ul v-else class="cr-card divide-y divide-hairline-soft p-0">
      <li v-for="g in rows" :key="g.id" class="flex flex-wrap items-center gap-3 px-6 py-3">
        <div class="min-w-[14rem] flex-1">
          <p class="text-sm font-medium text-ink">{{ g.descripcion }}</p>
          <p class="text-xs text-ink-3">{{ g.categoria_nombre }} · {{ g.sucursal_nombre }} · {{ g.contraparte_nombre }}</p>
        </div>
        <span class="tabular-nums text-sm">{{ Number(g.monto_estimado).toLocaleString(undefined, { minimumFractionDigits: 2 }) }}</span>
        <span class="text-xs text-ink-3">{{ g.frecuencia }} · próx. {{ g.proxima_generacion }}</span>
        <Pill :tone="TONO[g.estado]" :label="g.estado" />
        <div class="flex gap-1">
          <button v-if="g.estado === 'activo'" class="cr-btn cr-btn-ghost text-xs" @click="cambiarEstado(g, 'pausado')">Pausar</button>
          <button v-if="g.estado === 'pausado'" class="cr-btn cr-btn-ghost text-xs" @click="cambiarEstado(g, 'activo')">Reactivar</button>
          <button v-if="g.estado !== 'cancelado'" class="cr-btn cr-btn-ghost text-xs text-bad" @click="cambiarEstado(g, 'cancelado')">Cancelar</button>
        </div>
      </li>
    </ul>

    <FormModal
      :model-value="modal" titulo="Nuevo gasto recurrente"
      subtitulo="Se genera un borrador cada ciclo; confírmalo con el monto real desde Gastos."
      :guardando="guardando" ancho="max-w-2xl" :sucio="!!f.descripcion"
      @update:model-value="modal = $event" @guardar="guardar"
    >
      <FormField label="Categoría" required>
        <select v-model="f.categoria_gasto_id" class="cr-input">
          <option :value="null">Elige…</option>
          <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
        </select>
      </FormField>
      <FormField label="Sucursal" required>
        <select v-model="f.sucursal_id" class="cr-input">
          <option :value="null">Elige…</option>
          <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </FormField>
      <FormField label="Beneficiario / proveedor" wide required>
        <ComboBox v-model="f.beneficiario_id" :opciones="beneficiarios" opcion-label="nombre" opcion-value="id"
                 placeholder="Buscar o crear…" :crear="nuevoBeneficiario" crear-label="Crear beneficiario" />
      </FormField>
      <FormField label="Descripción" wide required>
        <input v-model="f.descripcion" class="cr-input" placeholder="Ej. Internet oficina" />
      </FormField>
      <FormField label="Monto estimado" required>
        <input v-model="f.monto_estimado" type="number" step="0.01" min="0.01" class="cr-input tabular-nums" />
      </FormField>
      <FormField label="Frecuencia">
        <select v-model="f.frecuencia" class="cr-input">
          <option value="mensual">Mensual</option>
          <option value="bimestral">Bimestral</option>
          <option value="trimestral">Trimestral</option>
        </select>
      </FormField>
      <FormField label="Próxima generación">
        <input v-model="f.proxima_generacion" type="date" class="cr-input" />
      </FormField>
      <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
    </FormModal>
  </div>
</template>
