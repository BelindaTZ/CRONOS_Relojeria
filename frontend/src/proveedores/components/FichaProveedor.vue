<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import ProveedorFormFields from './ProveedorFormFields.vue'
import {
  actualizarProveedor,
  calificarProveedor,
  getProveedor,
  inactivarProveedor,
  listarDocumentos,
  subirDocumento,
} from '@/proveedores/services/proveedoresApi'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)
const p = ref(null)
const docs = ref([])

async function cargar() {
  p.value = await getProveedor(id)
  docs.value = await listarDocumentos(id).catch(() => [])
}
onMounted(cargar)

// --- editar ---
const editModal = reactive({ abierto: false, guardando: false, error: '' })
const form = reactive({})
function abrirEdicion() {
  Object.assign(form, {
    razon_social: p.value.razon_social, ruc_nit: p.value.ruc_nit ?? '', nombre_comercial: p.value.nombre_comercial ?? '',
    contacto_nombre: p.value.contacto_nombre ?? '', telefono: p.value.telefono ?? '', email: p.value.email ?? '',
    condicion_pago_id: p.value.condicion_pago_id ?? null,
    certificacion_autorizada: p.value.certificacion_autorizada,
    marcas_autorizadas: [...(p.value.marcas_autorizadas || [])], tipos: [...p.value.tipos],
  })
  editModal.error = ''
  editModal.abierto = true
}
async function guardarEdicion() {
  editModal.guardando = true
  editModal.error = ''
  try {
    await actualizarProveedor(id, { ...form })
    editModal.abierto = false
    toast.success('Proveedor actualizado')
    cargar()
  } catch (e) {
    editModal.error = e.status === 403 ? 'Razón social y RUC/NIT solo los cambia un rol elevado.' : e.message
  } finally {
    editModal.guardando = false
  }
}

// --- calificar ---
const calModal = reactive({ abierto: false, guardando: false, calidad: null, soporte: null })
function abrirCalificar() {
  calModal.calidad = p.value.calificacion_vigente?.nota_calidad ?? null
  calModal.soporte = p.value.calificacion_vigente?.nota_soporte ?? null
  calModal.abierto = true
}
async function guardarCalificacion() {
  calModal.guardando = true
  try {
    await calificarProveedor(id, { nota_calidad: calModal.calidad, nota_soporte: calModal.soporte })
    calModal.abierto = false
    toast.success('Calificación registrada')
    cargar()
  } catch (e) {
    toast.error(e.message)
  } finally {
    calModal.guardando = false
  }
}

async function inactivar() {
  const ok = await confirm({
    title: `Inactivar «${p.value.razon_social}»`,
    message: 'El proveedor no se elimina; queda inactivo. Sus órdenes se conservan.',
    confirmLabel: 'Inactivar',
    tone: 'danger',
  })
  if (!ok) return
  await inactivarProveedor(id)
  toast.success('Proveedor inactivado')
  cargar()
}

async function adjuntar(ev) {
  const file = ev.target.files[0]
  if (!file) return
  const tipo = await confirm({ title: 'Adjuntar documento', message: `¿Adjuntar «${file.name}» como certificado?`, confirmLabel: 'Adjuntar' })
  if (!tipo) return (ev.target.value = '')
  try {
    await subirDocumento(id, 'certificado', file)
    toast.success('Documento adjuntado')
    docs.value = await listarDocumentos(id)
  } catch (e) {
    toast.error(e.message)
  }
  ev.target.value = ''
}

const cal = computed(() => p.value?.calificacion_vigente)
const ESTADO_TONO = { borrador: 'neutral', emitida: 'warn', confirmada: 'info', parcial: 'warn', recibida: 'good', cancelada: 'bad' }
</script>

<template>
  <div v-if="p">
    <PageHeader
      eyebrow="Abastecimiento · Proveedor"
      :titulo="p.razon_social"
      :sub="p.tipos.map((x) => x.replace(/_/g, ' ')).join(' · ') || 'Sin tipos'"
    >
      <template #acciones>
        <RouterLink :to="{ name: 'proveedores' }" class="cr-btn cr-btn-ghost">
          <CrIcon name="chevron-left" :size="15" /> Proveedores
        </RouterLink>
        <button class="cr-btn cr-btn-ghost" @click="abrirEdicion">Editar</button>
        <button v-if="p.estado === 'activo'" class="cr-btn cr-btn-danger" @click="inactivar">Inactivar</button>
      </template>
    </PageHeader>

    <div class="mb-6 flex items-center gap-3">
      <Pill :tone="p.estado === 'activo' ? 'good' : 'bad'" :label="p.estado" />
      <Pill v-if="p.certificacion_autorizada" tone="info" label="Distribución autorizada" />
    </div>

    <div class="grid gap-5 lg:grid-cols-2">
      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Datos</h2>
        <dl class="mt-4 space-y-2.5 text-sm">
          <div class="flex justify-between gap-4"><dt class="text-ink-3">RUC / NIT</dt><dd>{{ p.ruc_nit || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Contacto</dt><dd>{{ p.contacto_nombre || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Teléfono</dt><dd>{{ p.telefono || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Email</dt><dd>{{ p.email || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Condición de pago</dt><dd>{{ p.condicion_pago || '—' }}</dd></div>
          <div v-if="p.marcas_autorizadas_nombres && p.marcas_autorizadas_nombres.length" class="flex justify-between gap-4">
            <dt class="text-ink-3">Marcas autorizadas</dt><dd>{{ p.marcas_autorizadas_nombres.join(', ') }}</dd>
          </div>
        </dl>
      </section>

      <section class="cr-card p-6">
        <div class="flex items-center justify-between">
          <h2 class="serif text-lg text-ink">Calificación</h2>
          <button class="cr-btn cr-btn-ghost text-xs" @click="abrirCalificar">Calificar</button>
        </div>
        <div v-if="cal" class="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
          <p><span class="text-ink-3">Plazos (auto)</span><br /><strong class="serif text-xl text-gold-strong">{{ cal.nota_plazos ?? '—' }}</strong></p>
          <p><span class="text-ink-3">Agregada</span><br /><strong class="serif text-xl text-ink">{{ cal.nota_agregada ?? '—' }}</strong></p>
          <p><span class="text-ink-3">Calidad</span><br />{{ cal.nota_calidad ?? '—' }}</p>
          <p><span class="text-ink-3">Soporte</span><br />{{ cal.nota_soporte ?? '—' }}</p>
        </div>
        <p v-else class="mt-4 text-sm text-ink-3">Sin calificación aún.</p>
        <p class="mt-4 border-t border-hairline-soft pt-3 text-xs text-ink-3">
          Cumplimiento de plazos:
          <template v-if="p.indicador_plazos_dias != null">
            <strong class="text-ink-2">{{ p.indicador_plazos_dias }} días</strong> de desfase promedio (últimas recepciones). La nota de plazos se recalcula sola.
          </template>
          <template v-else>sin recepciones registradas.</template>
        </p>
      </section>

      <section class="cr-card p-6">
        <div class="flex items-center justify-between">
          <h2 class="serif text-lg text-ink">Documentos</h2>
          <label class="cr-btn cr-btn-ghost cursor-pointer text-xs">
            Adjuntar<input type="file" class="hidden" @change="adjuntar" />
          </label>
        </div>
        <ul class="mt-4 space-y-2 text-sm">
          <li v-for="d in docs" :key="d.id" class="flex items-center gap-2">
            <CrIcon name="archive" :size="15" class="text-ink-3" />
            <a :href="d.url" target="_blank" rel="noopener" class="text-gold-strong hover:underline">{{ d.nombre }}</a>
            <span class="text-ink-3">· {{ d.tipo }}</span>
          </li>
          <li v-if="!docs.length" class="text-ink-3">Sin documentos.</li>
        </ul>
      </section>

      <section class="cr-card overflow-hidden p-0">
        <header class="p-6 pb-3"><h2 class="serif text-lg text-ink">Historial de compras</h2></header>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
                <th class="px-4 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Orden</th>
                <th class="px-4 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Tipo</th>
                <th class="px-4 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Estado</th>
                <th class="px-4 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Importe</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-hairline-soft">
              <tr v-for="o in p.historial_compras" :key="o.id">
                <td class="px-4 py-2.5">#{{ o.id }}</td>
                <td class="px-4 py-2.5 text-ink-2">{{ o.tipo }}</td>
                <td class="px-4 py-2.5"><Pill :tone="ESTADO_TONO[o.estado] || 'neutral'" :label="o.estado" /></td>
                <td class="px-4 py-2.5 text-right tabular-nums">{{ o.importe_a_pagar ?? '—' }}</td>
              </tr>
              <tr v-if="!p.historial_compras.length"><td colspan="4" class="px-4 py-6 text-center text-ink-3">Sin órdenes.</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <FormModal v-model="editModal.abierto" titulo="Editar proveedor" :guardando="editModal.guardando" ancho="max-w-2xl" @guardar="guardarEdicion">
      <ProveedorFormFields :model-value="form" edicion :error="editModal.error" />
    </FormModal>

    <FormModal v-model="calModal.abierto" titulo="Calificar proveedor" subtitulo="La nota de plazos es automática; solo se editan calidad y soporte." :guardando="calModal.guardando" @guardar="guardarCalificacion">
      <FormField label="Calidad (1–5)"><input v-model.number="calModal.calidad" type="number" min="1" max="5" step="0.5" class="cr-input" /></FormField>
      <FormField label="Soporte postventa (1–5)"><input v-model.number="calModal.soporte" type="number" min="1" max="5" step="0.5" class="cr-input" /></FormField>
    </FormModal>
  </div>
</template>
