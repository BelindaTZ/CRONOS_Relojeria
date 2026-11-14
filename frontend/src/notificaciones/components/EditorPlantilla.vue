<script setup>
/**
 * Editor de plantillas de correo (feature 014, US5) — solo Gerencia General /
 * delegado (gating real en el backend; esta pantalla ya vive detrás de
 * `soloGerencia` en el router). Preview con datos de ejemplo antes de guardar.
 */
import { onMounted, reactive, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { getPlantilla, listarPlantillas, previewPlantilla, setPlantilla } from '@/notificaciones/services/notificacionesApi'

const TITULOS = {
  password_temporal: 'Contraseña temporal', inactivacion_sucursal: 'Inactivación de sucursal',
  cancelacion_orden: 'Cancelación de orden de compra', usuario_bienvenida: 'Bienvenida de usuario',
  tecnico_asignado: 'Técnico asignado', factura_venta: 'Factura de venta',
  tecnico_nueva_ot: 'Nueva OT (al técnico)', diagnostico_cliente: 'Diagnóstico (al cliente)',
  servicio_listo_retiro: 'Servicio listo para retiro', compra_urgente_solicitada: 'Compra urgente solicitada',
  ot_entregado: 'Orden entregada', ot_cancelada: 'Orden cancelada',
  cupon: 'Cupón emitido', nivel: 'Ascenso de nivel', recordatorio_cita: 'Recordatorio de cita',
}

const cargando = ref(true)
const plantillas = ref([])
const modal = reactive({ abierto: false, tipo: '', guardando: false, error: '', asunto: '', cuerpo: '' })
const previa = ref(null)
const previsualizando = ref(false)

async function cargar() {
  cargando.value = true
  try {
    plantillas.value = await listarPlantillas()
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

async function abrir(tipo) {
  const detalle = await getPlantilla(tipo)
  modal.tipo = tipo
  modal.asunto = detalle.actual?.asunto || `CRONOS · ${TITULOS[tipo] || tipo}`
  modal.cuerpo = detalle.actual?.cuerpo || '<p>Estimado/a {{ cliente_nombre }},</p>\n<p>…</p>'
  modal.error = ''
  previa.value = null
  modal.abierto = true
}

async function ver() {
  previsualizando.value = true
  try {
    previa.value = await previewPlantilla(modal.tipo, { cliente_nombre: 'Cliente de ejemplo', ot_numero: 'OT-0001', codigo: 'DEMO10', descripcion: '10% de descuento', vigencia_fin: '2026-12-31', nivel_nombre: 'Oro', motivo: 'Revisión general', fecha_texto: 'Lunes 15, 10:00' })
  } catch (e) {
    toast.error(e.message)
  } finally {
    previsualizando.value = false
  }
}

async function guardar() {
  modal.guardando = true
  modal.error = ''
  try {
    await setPlantilla(modal.tipo, { asunto: modal.asunto, cuerpo: modal.cuerpo })
    toast.success('Plantilla actualizada')
    modal.abierto = false
    cargar()
  } catch (e) {
    modal.error = e.message
  } finally {
    modal.guardando = false
  }
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Notificaciones" titulo="Plantillas de correo" sub="Asunto y cuerpo de cada tipo de correo automatizado — con la identidad visual de CRONOS. Editable solo por Gerencia General." />

    <p v-if="cargando" class="text-sm text-ink-3">Cargando…</p>
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <button
        v-for="p in plantillas" :key="p.tipo" type="button"
        class="cr-card flex flex-col gap-2 p-4 text-left transition hover:border-hairline-strong hover:shadow-md"
        @click="abrir(p.tipo)"
      >
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-ink">{{ TITULOS[p.tipo] || p.tipo }}</span>
          <Pill :tone="p.activa ? 'good' : 'neutral'" :label="p.activa ? `v${p.version}` : 'predeterminada'" />
        </div>
        <p class="text-xs text-ink-3">{{ p.activa ? p.asunto : 'Usa la plantilla predeterminada del sistema' }}</p>
      </button>
    </div>

    <FormModal
      v-model="modal.abierto" :titulo="`Plantilla · ${TITULOS[modal.tipo] || modal.tipo}`" ancho="max-w-2xl"
      :guardando="modal.guardando" guardar-label="Guardar (nueva versión)" @guardar="guardar"
    >
      <FormField label="Asunto" wide required helper="Admite variables Jinja2, ej. {{ cliente_nombre }}">
        <input v-model="modal.asunto" class="cr-input" />
      </FormField>
      <FormField label="Cuerpo (HTML)" wide required helper="Hereda el layout de CRONOS automáticamente — solo el contenido interior.">
        <textarea v-model="modal.cuerpo" rows="10" class="cr-input font-mono text-xs"></textarea>
      </FormField>
      <div class="sm:col-span-2">
        <button type="button" class="cr-btn cr-btn-ghost text-xs" :disabled="previsualizando" @click="ver">
          <CrIcon name="watch" :size="13" /> {{ previsualizando ? 'Generando…' : 'Vista previa con datos de ejemplo' }}
        </button>
        <div v-if="previa" class="mt-3 rounded-lg border border-hairline p-3">
          <p class="cr-label mb-1">Asunto</p>
          <p class="mb-3 text-sm text-ink">{{ previa.asunto }}</p>
          <p class="cr-label mb-1">Cuerpo</p>
          <iframe :srcdoc="previa.html" class="h-64 w-full rounded border border-hairline-soft bg-white"></iframe>
        </div>
      </div>
      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
