<script setup>
/**
 * Un solo flujo para cerrar una venta en borrador (feedback del usuario
 * 2026-09-11: "descuento, pago y confirmar venta parecen 3 acciones ajenas,
 * deben ser una sola"). Reúne descuento/cupón + pagos + el desglose de IVA en
 * vivo + confirmar, todo en un mismo modal — nada de saltar entre botones
 * sueltos de la barra superior para completar una sola operación.
 */
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { confirm, prompt } from '@/shared/ui/dialogs'
import { listarDescuentos } from '@/clientes'
import { aplicarDescuentoVenta, confirmarVenta, registrarPagoVenta } from '@/ventas/services/ventasApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  venta: { type: Object, required: true },
})
const emit = defineEmits(['update:modelValue', 'hecho'])

const dinero = (n) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: 2 }))

const DECISION_LABEL = {
  permitir: 'Aplicado',
  requiere_autorizacion: 'Aplicado · requiere autorización de Gerencia General al confirmar',
}

const descuentos = ref([])
onMounted(() => { listarDescuentos().then((r) => (descuentos.value = r)).catch(() => []) })

// --- descuento / cupón ---
const editandoDescuento = ref(false)
const fd = reactive({ modo: 'descuento', descuento_id: null, cupon_codigo: '' })
const guardandoDescuento = ref(false)
const errorDescuento = ref('')

function resetDescuentoForm() {
  Object.assign(fd, { modo: 'descuento', descuento_id: null, cupon_codigo: '' })
  errorDescuento.value = ''
  editandoDescuento.value = !props.venta.descuento_aplicado
}

async function aplicarDescuento() {
  errorDescuento.value = ''
  const payload = fd.modo === 'descuento' ? { descuento_id: fd.descuento_id } : { cupon_codigo: fd.cupon_codigo.trim() }
  if (fd.modo === 'descuento' && !fd.descuento_id) return (errorDescuento.value = 'Elige el descuento.')
  if (fd.modo === 'cupon' && !payload.cupon_codigo) return (errorDescuento.value = 'Escribe el código del cupón.')
  guardandoDescuento.value = true
  try {
    const r = await aplicarDescuentoVenta(props.venta.id, payload)
    toast.success(`Descuento aplicado · ${DECISION_LABEL[r.decision] || r.decision}`)
    editandoDescuento.value = false
    emit('hecho')
  } catch (e) {
    errorDescuento.value = e.status === 409 ? 'El descuento deja el margen bajo el mínimo protegido (política: bloquear).' : e.message
  } finally {
    guardandoDescuento.value = false
  }
}

// --- pagos ---
// Los pagos se acumulan EN EL MODAL, sin tocar el backend, y solo se registran
// (uno a uno) en el mismo clic que confirma la venta. Antes, "Agregar pago"
// llamaba al backend al instante — permitía dejar un pago cobrado contra un
// borrador que nunca se confirmaba (feedback del usuario, 2026-09-11: "puedo
// agregar pago y nunca registrar la venta???"). Cerrar el modal sin confirmar
// ahora descarta los pagos pendientes: nada se cobra hasta que la venta se cierra.
const fp = reactive({ medio_pago: 'efectivo', monto: null, referencia: '' })
const pagosPendientes = ref([])
const errorPago = ref('')

const saldoProyectado = () => {
  const acumulado = pagosPendientes.value.reduce((s, p) => s + p.monto, 0)
  return Math.max(0, Number(props.venta.saldo || 0) - acumulado)
}

function resetPagoForm() {
  pagosPendientes.value = []
  fp.medio_pago = 'efectivo'
  fp.monto = props.venta.saldo != null && Number(props.venta.saldo) > 0 ? Number(props.venta.saldo) : null
  fp.referencia = ''
  errorPago.value = ''
}

function agregarPagoPendiente() {
  errorPago.value = ''
  if (!fp.monto || Number(fp.monto) <= 0) return (errorPago.value = 'Indica el monto.')
  pagosPendientes.value.push({ medio_pago: fp.medio_pago, monto: Number(fp.monto), referencia: fp.referencia.trim() || null })
  const restante = saldoProyectado()
  fp.monto = restante > 0 ? restante : null
  fp.referencia = ''
}

function quitarPagoPendiente(i) {
  pagosPendientes.value.splice(i, 1)
}

// --- confirmar (registra los pagos pendientes y confirma, todo en un solo paso) ---
const confirmando = ref(false)
const errorConfirmar = ref('')

async function confirmarVentaFlujo() {
  errorConfirmar.value = ''
  const da = props.venta.descuento_aplicado || {}
  let autorizacion_margen_minimo_id = null
  if (da.decision === 'requiere_autorizacion') {
    const val = await prompt({
      title: 'Confirmar con autorización de margen',
      message: 'El descuento deja el margen bajo el mínimo protegido. Ingresa el ID de la autorización registrada por Gerencia General.',
      label: 'ID de autorización de margen mínimo',
    })
    if (!val) return
    autorizacion_margen_minimo_id = Number(val)
  } else if (!(await confirm({
    title: `Confirmar la venta ${props.venta.numero}`,
    message: pagosPendientes.value.length
      ? `Se registran ${pagosPendientes.value.length} pago(s), se descuenta stock, se generan el comprobante y el certificado, y (si queda saldo) la cuenta por cobrar. No es reversible salvo anulación.`
      : 'Se descuenta stock, se generan el comprobante y el certificado, y (si hay saldo) la cuenta por cobrar. No es reversible salvo anulación.',
    confirmLabel: 'Confirmar venta',
  }))) {
    return
  }
  confirmando.value = true
  try {
    while (pagosPendientes.value.length) {
      const p = pagosPendientes.value[0]
      await registrarPagoVenta(props.venta.id, p)
      pagosPendientes.value.shift()
    }
    await confirmarVenta(props.venta.id, { autorizacion_margen_minimo_id })
    toast.success('Venta confirmada')
    emit('hecho')
    emit('update:modelValue', false)
  } catch (e) {
    errorConfirmar.value = e.status === 403 ? (e.message || 'Requiere autorización de Gerencia General.') : e.message
    emit('hecho') // por si algún pago sí se alcanzó a registrar antes del error
  } finally {
    confirmando.value = false
  }
}

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    resetDescuentoForm()
    resetPagoForm()
    errorConfirmar.value = ''
  },
)
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="`Finalizar venta ${venta.numero}`"
    subtitulo="Descuento, pagos y confirmación de una misma operación — todo aquí."
    ancho="max-w-2xl"
    :guardando="confirmando"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="confirmarVentaFlujo"
  >
    <!-- resumen con desglose de IVA -->
    <div class="sm:col-span-2 rounded-xl border border-hairline bg-surface-sunk p-4 text-sm">
      <div class="flex justify-between"><span class="text-ink-3">Subtotal (PVP)</span><span class="tabular-nums">{{ dinero(venta.subtotal) }}</span></div>
      <template v-if="venta.subtotal_sin_impuestos != null">
        <div class="flex justify-between text-ink-3"><span>Subtotal sin impuestos</span><span class="tabular-nums">{{ dinero(venta.subtotal_sin_impuestos) }}</span></div>
        <div v-if="Number(venta.total_descuento) > 0" class="flex justify-between text-ink-3"><span>Descuento</span><span class="tabular-nums">−{{ dinero(venta.total_descuento) }}</span></div>
        <div class="flex justify-between text-ink-3">
          <span>IVA {{ venta.iva_porcentaje != null ? (Number(venta.iva_porcentaje) * 100).toFixed(0) : '' }}%</span>
          <span class="tabular-nums">{{ dinero(venta.iva_monto) }}</span>
        </div>
      </template>
      <div class="mt-1 flex justify-between border-t border-hairline-soft pt-1 font-medium text-ink"><span>Total</span><span class="tabular-nums">{{ dinero(venta.total) }}</span></div>
      <div class="mt-1 flex justify-between text-xs text-ink-3"><span>Pagado</span><span class="tabular-nums">{{ dinero(venta.pagado) }}</span></div>
      <div v-if="pagosPendientes.length" class="flex justify-between text-xs text-ink-3">
        <span>Pagos por confirmar</span><span class="tabular-nums">{{ dinero(pagosPendientes.reduce((s, p) => s + p.monto, 0)) }}</span>
      </div>
      <div class="flex justify-between text-xs" :class="saldoProyectado() > 0 ? 'text-warn' : 'text-good'">
        <span>Saldo{{ pagosPendientes.length ? ' proyectado' : '' }}</span><span class="tabular-nums">{{ dinero(saldoProyectado()) }}</span>
      </div>
    </div>

    <!-- descuento / cupón -->
    <div class="sm:col-span-2 rounded-xl border border-hairline p-4">
      <div class="mb-2 flex items-center justify-between">
        <h3 class="text-sm font-medium text-ink">Descuento o cupón</h3>
        <button
          v-if="venta.descuento_aplicado && !editandoDescuento"
          type="button" class="cr-btn cr-btn-ghost text-xs" @click="editandoDescuento = true"
        >
          Cambiar
        </button>
      </div>

      <div v-if="venta.descuento_aplicado && !editandoDescuento" class="rounded-md px-3 py-2 text-sm"
           :class="venta.descuento_aplicado.decision === 'permitir' ? 'bg-good-bg text-good' : 'bg-warn-bg text-warn'">
        {{ venta.descuento_aplicado.es_cupon ? `Cupón ${venta.descuento_aplicado.cupon_codigo}` : 'Descuento general' }}
        — descontado {{ dinero(venta.descuento_aplicado.monto_descontado) }}.
        {{ DECISION_LABEL[venta.descuento_aplicado.decision] || venta.descuento_aplicado.decision }}
      </div>

      <template v-else>
        <div class="mb-2 flex gap-4 text-sm">
          <label class="flex items-center gap-1"><input v-model="fd.modo" type="radio" value="descuento" /> Descuento general</label>
          <label class="flex items-center gap-1"><input v-model="fd.modo" type="radio" value="cupon" /> Cupón del cliente</label>
        </div>
        <div class="flex flex-wrap items-end gap-2">
          <div class="min-w-[14rem] flex-1">
            <select v-if="fd.modo === 'descuento'" v-model="fd.descuento_id" class="cr-input">
              <option :value="null">Elige…</option>
              <option v-for="d in descuentos" :key="d.id" :value="d.id">
                {{ d.nombre }} — {{ d.tipo === 'porcentaje' ? (Number(d.valor) * 100).toFixed(0) + ' %' : d.valor }}
              </option>
            </select>
            <input v-else v-model="fd.cupon_codigo" class="cr-input" placeholder="Código del cupón"
                   @keydown.enter.prevent="aplicarDescuento" />
          </div>
          <button type="button" class="cr-btn cr-btn-ghost shrink-0" :disabled="guardandoDescuento" @click="aplicarDescuento">
            {{ guardandoDescuento ? 'Aplicando…' : 'Aplicar' }}
          </button>
          <button v-if="venta.descuento_aplicado" type="button" class="cr-btn cr-btn-ghost shrink-0 text-xs" @click="editandoDescuento = false">
            Cancelar
          </button>
        </div>
        <p v-if="errorDescuento" class="mt-1 text-sm text-bad" role="alert">{{ errorDescuento }}</p>
      </template>
    </div>

    <!-- pagos: se acumulan aquí y se registran recién al confirmar (no antes) -->
    <div class="sm:col-span-2 rounded-xl border border-hairline p-4">
      <h3 class="mb-2 text-sm font-medium text-ink">Pagos</h3>
      <ul v-if="venta.pagos.length || pagosPendientes.length" class="mb-2 divide-y divide-hairline-soft text-sm">
        <li v-for="p in venta.pagos" :key="p.pago_id" class="flex justify-between py-1">
          <span>{{ p.medio_pago }} <span v-if="p.referencia" class="text-ink-3">· {{ p.referencia }}</span></span>
          <span class="tabular-nums">{{ dinero(p.monto) }}</span>
        </li>
        <li v-for="(p, i) in pagosPendientes" :key="`pend-${i}`" class="flex justify-between py-1">
          <span>
            {{ p.medio_pago }} <span v-if="p.referencia" class="text-ink-3">· {{ p.referencia }}</span>
            <span class="ml-1 rounded-full bg-warn-bg px-1.5 py-0.5 text-[11px] text-warn">por confirmar</span>
          </span>
          <span class="tabular-nums">
            {{ dinero(p.monto) }}
            <button type="button" class="ml-2 text-ink-3 hover:text-bad" title="Quitar" aria-label="Quitar pago" @click="quitarPagoPendiente(i)">
              <CrIcon name="x" :size="13" class="inline" />
            </button>
          </span>
        </li>
      </ul>
      <p v-else class="mb-2 text-sm text-ink-3">Sin pagos. Una venta a crédito genera cuenta por cobrar por el saldo al confirmar.</p>

      <div class="flex flex-wrap items-end gap-2">
        <FormField label="Medio">
          <select v-model="fp.medio_pago" class="cr-input">
            <option value="efectivo">Efectivo</option>
            <option value="transferencia">Transferencia</option>
            <option value="cheque">Cheque</option>
            <option value="tarjeta">Tarjeta</option>
          </select>
        </FormField>
        <FormField label="Monto">
          <input v-model="fp.monto" type="number" step="0.01" min="0.01" class="cr-input w-32 tabular-nums"
                 @keydown.enter.prevent="agregarPagoPendiente" />
        </FormField>
        <FormField label="Referencia" helper="N.º de comprobante / cheque / últimos dígitos">
          <input v-model="fp.referencia" class="cr-input" @keydown.enter.prevent="agregarPagoPendiente" />
        </FormField>
        <button type="button" class="cr-btn cr-btn-ghost shrink-0" @click="agregarPagoPendiente">
          Agregar a la lista
        </button>
      </div>
      <p class="mt-1 text-xs text-ink-3">Los pagos que agregues aquí se cobran recién al confirmar la venta, junto con todo lo demás.</p>
      <p v-if="errorPago" class="mt-1 text-sm text-bad" role="alert">{{ errorPago }}</p>
    </div>

    <p v-if="errorConfirmar" class="sm:col-span-2 text-sm text-bad" role="alert">{{ errorConfirmar }}</p>

    <template #footer>
      <button type="button" class="cr-btn cr-btn-ghost" @click="emit('update:modelValue', false)">Cerrar</button>
      <button type="submit" class="cr-btn cr-btn-primary min-w-[9rem]" :disabled="confirmando">
        <span v-if="confirmando" class="inline-flex items-center gap-2"><CrIcon name="refresh-cw" :size="15" class="animate-spin" /> Confirmando…</span>
        <span v-else>Confirmar venta</span>
      </button>
    </template>
  </FormModal>
</template>
