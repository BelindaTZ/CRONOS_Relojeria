<script setup>
/**
 * Modal de acción puntual sobre una OT (design-system: un modal, un propósito).
 * `tipo` ∈ diagnostico | trabajo | horas | descuento | pago | entregar | dano | reabrir
 */
import { computed, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import {
  aplicarDescuento,
  entregar,
  registrarDiagnostico,
  registrarHoras,
  registrarPago,
  registrarTrabajo,
  reabrirGarantia,
  reportarDano,
} from '@/servicio_tecnico/services/servicioTecnicoApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  tipo: { type: String, required: true },
  ot: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'hecho', 'merma-pendiente'])

const META = {
  diagnostico: { titulo: 'Registrar diagnóstico', sub: 'Al guardar, la OT pasa a «en diagnóstico».' },
  trabajo: { titulo: 'Trabajo realizado', sub: 'Resumen del servicio para el documento del cliente.' },
  horas: { titulo: 'Horas trabajadas', sub: 'Alimentan el costeo de mano de obra por tarifa horaria.' },
  descuento: { titulo: 'Aplicar descuento o cupón', sub: 'Se valida contra el margen mínimo protegido (006).' },
  pago: { titulo: 'Registrar pago', sub: 'Pagos multimedios. La OT no se entrega con saldo pendiente.' },
  entregar: { titulo: 'Entregar la orden', sub: 'Genera el documento de la OT y el certificado de garantía.' },
  dano: { titulo: 'Reportar daño en servicio', sub: 'Deriva a un registro de merma (011). Sin sanción automática.' },
  reabrir: { titulo: 'Reabrir por garantía', sub: 'Crea una OT nueva vinculada a esta.' },
}

const f = reactive({
  diagnostico: '', trabajo_realizado: '', horas: null,
  desc_tipo: 'porcentaje', desc_valor: null, es_cupon: false, codigo_cupon: '',
  medio_pago: 'efectivo', monto: null, referencia: '',
  autorizacion_credito_id: null,
  descripcion: '', pieza_id: null, reloj_serie: '',
  motivo: '', tipo_reparacion: '',
})
const guardando = ref(false)
const error = ref('')
const resultado = ref(null)

watch(
  () => props.modelValue,
  (v) => { if (v) { error.value = ''; resultado.value = null } },
)

const meta = computed(() => META[props.tipo] || { titulo: 'Acción', sub: '' })

async function guardar() {
  error.value = ''
  guardando.value = true
  try {
    const id = props.ot.id
    let msg = 'Listo'
    if (props.tipo === 'diagnostico') {
      if (f.diagnostico.trim().length < 3) throw new Error('Escribe el diagnóstico.')
      await registrarDiagnostico(id, { diagnostico: f.diagnostico.trim() })
      msg = 'Diagnóstico registrado'
    } else if (props.tipo === 'trabajo') {
      await registrarTrabajo(id, { trabajo_realizado: f.trabajo_realizado.trim() })
      msg = 'Trabajo realizado registrado'
    } else if (props.tipo === 'horas') {
      await registrarHoras(id, { horas: Number(f.horas) })
      msg = 'Horas registradas'
    } else if (props.tipo === 'descuento') {
      const r = await aplicarDescuento(id, {
        tipo: f.desc_tipo, valor: Number(f.desc_valor),
        es_cupon: f.es_cupon, codigo_cupon: f.es_cupon ? f.codigo_cupon.trim() || null : null,
      })
      resultado.value = `Precio final ${r.precio_final} · descontado ${r.monto_descontado} · decisión: ${r.decision}`
      msg = 'Descuento aplicado'
    } else if (props.tipo === 'pago') {
      const r = await registrarPago(id, { medio_pago: f.medio_pago, monto: Number(f.monto), referencia: f.referencia.trim() || null })
      resultado.value = `Pago registrado. Saldo pendiente: ${r.saldo}`
      msg = 'Pago registrado'
    } else if (props.tipo === 'entregar') {
      await entregar(id, { autorizacion_credito_id: f.autorizacion_credito_id || null })
      msg = 'Orden entregada'
    } else if (props.tipo === 'dano') {
      const payload = await reportarDano(id, {
        descripcion: f.descripcion.trim(), pieza_id: f.pieza_id || null, reloj_serie: f.reloj_serie.trim() || null,
      })
      msg = 'Daño reportado'
      emit('merma-pendiente', { ...payload, causa: 'dano_servicio', sucursal_id: props.ot.sucursal_id })
    } else if (props.tipo === 'reabrir') {
      await reabrirGarantia(id, { motivo: f.motivo.trim(), tipo_reparacion: f.tipo_reparacion.trim() || null })
      msg = 'OT de garantía creada'
    }
    toast.success(msg)
    emit('hecho')
    if (!resultado.value) emit('update:modelValue', false)
  } catch (e) {
    error.value = e.status === 403 ? (e.message || 'Requiere autorización de Gerencia General.') : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="meta.titulo"
    :subtitulo="meta.sub"
    :guardando="guardando"
    ancho="max-w-xl"
    :sucio="true"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <template v-if="tipo === 'diagnostico'">
      <FormField label="Diagnóstico" wide required>
        <textarea v-model="f.diagnostico" rows="4" class="cr-input"></textarea>
      </FormField>
    </template>

    <template v-else-if="tipo === 'trabajo'">
      <FormField label="Trabajo realizado" wide required>
        <textarea v-model="f.trabajo_realizado" rows="4" class="cr-input"></textarea>
      </FormField>
    </template>

    <template v-else-if="tipo === 'horas'">
      <FormField label="Horas trabajadas" required helper="Decimales permitidos (ej. 2.5).">
        <input v-model="f.horas" type="number" step="0.25" min="0.25" class="cr-input tabular-nums" />
      </FormField>
    </template>

    <template v-else-if="tipo === 'descuento'">
      <FormField label="Tipo">
        <select v-model="f.desc_tipo" class="cr-input">
          <option value="porcentaje">Porcentaje</option>
          <option value="monto">Monto fijo</option>
        </select>
      </FormField>
      <FormField label="Valor" required :helper="f.desc_tipo === 'porcentaje' ? 'Fracción: 0.10 = 10 %' : 'Monto en la moneda'">
        <input v-model="f.desc_valor" type="number" step="0.01" min="0" class="cr-input tabular-nums" />
      </FormField>
      <FormField label="¿Es un cupón nominativo?" wide>
        <label class="flex items-center gap-2 text-sm"><input v-model="f.es_cupon" type="checkbox" /> Sí, consumir un cupón</label>
      </FormField>
      <FormField v-if="f.es_cupon" label="Código del cupón" wide>
        <input v-model="f.codigo_cupon" class="cr-input" />
      </FormField>
    </template>

    <template v-else-if="tipo === 'pago'">
      <FormField label="Medio de pago" required>
        <select v-model="f.medio_pago" class="cr-input">
          <option value="efectivo">Efectivo</option>
          <option value="transferencia">Transferencia</option>
          <option value="cheque">Cheque</option>
          <option value="tarjeta">Tarjeta</option>
        </select>
      </FormField>
      <FormField label="Monto" required>
        <input v-model="f.monto" type="number" step="0.01" min="0.01" class="cr-input tabular-nums" />
      </FormField>
      <FormField label="Referencia" wide helper="N.º de comprobante, últimos dígitos de la tarjeta, N.º de cheque…">
        <input v-model="f.referencia" class="cr-input" />
      </FormField>
    </template>

    <template v-else-if="tipo === 'entregar'">
      <p class="text-sm text-ink-2 sm:col-span-2">
        Saldo pendiente: <strong class="tabular-nums">{{ ot.saldo ?? '—' }}</strong>.
        Con saldo &gt; 0 la entrega exige una autorización de crédito de Gerencia General.
      </p>
      <FormField label="ID de autorización de crédito" wide helper="Solo si se entrega con saldo pendiente.">
        <input v-model="f.autorizacion_credito_id" type="number" class="cr-input tabular-nums" />
      </FormField>
    </template>

    <template v-else-if="tipo === 'dano'">
      <FormField label="Descripción del daño" wide required>
        <textarea v-model="f.descripcion" rows="3" class="cr-input"></textarea>
      </FormField>
      <FormField label="ID de pieza afectada">
        <input v-model="f.pieza_id" type="number" class="cr-input tabular-nums" />
      </FormField>
      <FormField label="N.º de serie afectado" helper="Por defecto, el de la unidad de la OT.">
        <input v-model="f.reloj_serie" class="cr-input tabular-nums" />
      </FormField>
    </template>

    <template v-else-if="tipo === 'reabrir'">
      <FormField label="Motivo de la reapertura" wide required>
        <textarea v-model="f.motivo" rows="3" class="cr-input"></textarea>
      </FormField>
      <FormField label="Tipo de reparación" helper="Por defecto, el de la OT original.">
        <input v-model="f.tipo_reparacion" class="cr-input" />
      </FormField>
    </template>

    <p v-if="resultado" class="rounded-md bg-good-bg px-3 py-2 text-sm text-good sm:col-span-2">{{ resultado }}</p>
    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
