<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import {
  enviarFacturaVenta,
  getComprobantesVenta,
  getVenta,
} from '@/ventas/services/ventasApi'
import FinalizarVentaModal from './FinalizarVentaModal.vue'
import PagoVentaModal from './PagoVentaModal.vue'
import AnularVentaModal from './AnularVentaModal.vue'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)

const v = ref(null)
const cargando = ref(true)
const modalFinalizar = ref(false)
const modalPago = ref(false)
const modalAnular = ref(false)

const DECISION_LABEL = {
  permitir: 'aplicado',
  requiere_autorizacion: 'aplicado · requiere autorización de Gerencia General',
}

const TONO = { borrador: 'neutral', confirmada: 'good', anulada: 'bad' }

async function cargar() {
  cargando.value = true
  try {
    v.value = await getVenta(id)
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

const kpis = computed(() => {
  if (!v.value) return []
  const k = [
    { label: 'Estado', value: v.value.estado },
    { label: 'Total', value: dinero(v.value.total) },
    { label: 'Pagado · saldo', value: `${dinero(v.value.pagado)} · ${dinero(v.value.saldo)}` },
  ]
  if (v.value.costos_visibles && v.value.margen_venta != null)
    k.push({ label: 'Margen de la venta', value: dinero(v.value.margen_venta), gold: true })
  return k
})

async function verComprobantes() {
  try {
    const docs = await getComprobantesVenta(id)
    if (!docs.length) return toast.error('Aún no hay comprobantes.')
    for (const d of docs) window.open(d.url, '_blank', 'noopener')
  } catch (e) {
    toast.error(e.message)
  }
}

async function enviarFactura() {
  try {
    const r = await enviarFacturaVenta(id)
    if (r.enviado) toast.success(`Factura enviada a ${r.email}`)
    else toast.error(r.detalle || 'No se pudo enviar la factura.')
  } catch (e) {
    toast.error(e.message)
  }
}
const dinero = (n) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: 2 }))
</script>

<template>
  <div v-if="v">
    <PageHeader
      eyebrow="Ventas · Orden de venta"
      :titulo="v.numero_factura || v.numero"
      :sub="`${v.cliente_nombre} (${v.cliente_afiliado}) · ${v.sucursal_nombre}${v.numero_factura ? ` · interno ${v.numero}` : ''}`"
    >
      <template #acciones>
        <RouterLink :to="{ name: 'ventas' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Ventas</RouterLink>
        <button v-if="v.estado === 'borrador'" class="cr-btn cr-btn-primary" @click="modalFinalizar = true">Finalizar venta</button>
        <button v-if="v.estado === 'confirmada'" class="cr-btn cr-btn-ghost" @click="modalPago = true">Registrar pago</button>
        <button v-if="v.estado === 'confirmada'" class="cr-btn cr-btn-ghost" @click="verComprobantes">Factura (PDF)</button>
        <button v-if="v.estado === 'confirmada' && v.cliente_email" class="cr-btn cr-btn-ghost" @click="enviarFactura">Enviar por correo</button>
        <button v-if="v.estado === 'confirmada'" class="cr-btn cr-btn-danger" @click="modalAnular = true">Anular</button>
      </template>
    </PageHeader>

    <div class="mb-5 flex flex-wrap items-center gap-3">
      <Pill :tone="TONO[v.estado] || 'neutral'" :label="v.estado" />
      <span class="text-xs text-ink-3">{{ new Date(v.fecha).toLocaleString() }}</span>
      <span v-if="v.descuento_aplicado" class="rounded-full bg-warn-bg px-2 py-0.5 text-xs text-warn">
        {{ v.descuento_aplicado.es_cupon ? `Cupón ${v.descuento_aplicado.cupon_codigo}` : 'Descuento general' }}
        — {{ dinero(v.descuento_aplicado.monto_descontado) }} ·
        {{ DECISION_LABEL[v.descuento_aplicado.decision] || v.descuento_aplicado.decision }}
      </span>
    </div>

    <KpiStrip :items="kpis" />

    <div class="mt-6 grid gap-5 lg:grid-cols-2">
      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Líneas</h2>
        <ul class="mt-3 divide-y divide-hairline-soft text-sm">
          <li v-for="ln in v.lineas" :key="ln.id" class="flex flex-wrap justify-between gap-2 py-2">
            <span>
              {{ ln.descripcion }}
              <span v-if="ln.numero_serie" class="ml-1 text-xs text-ink-3 tabular-nums">{{ ln.numero_serie }}</span>
              <span v-if="ln.cantidad > 1" class="ml-1 text-xs text-ink-3">×{{ ln.cantidad }}</span>
            </span>
            <span class="tabular-nums text-ink-2">
              <span v-if="Number(ln.precio_lista) !== Number(ln.precio_final)" class="mr-1 text-ink-3 line-through">{{ dinero(ln.precio_lista) }}</span>
              {{ dinero(ln.precio_final) }}
              <span v-if="ln.margen != null" class="ml-1 text-xs text-gold-strong">m. {{ dinero(ln.margen) }}</span>
            </span>
          </li>
        </ul>
        <div class="mt-3 border-t border-hairline pt-2 text-sm">
          <div class="flex justify-between"><span class="text-ink-3">Subtotal (PVP)</span><span class="tabular-nums">{{ dinero(v.subtotal) }}</span></div>
          <template v-if="v.subtotal_sin_impuestos != null">
            <div class="flex justify-between text-ink-3"><span>Subtotal sin impuestos</span><span class="tabular-nums">{{ dinero(v.subtotal_sin_impuestos) }}</span></div>
            <div v-if="Number(v.total_descuento) > 0" class="flex justify-between text-ink-3"><span>Descuento</span><span class="tabular-nums">−{{ dinero(v.total_descuento) }}</span></div>
            <div class="flex justify-between text-ink-3"><span>IVA {{ v.iva_porcentaje != null ? (Number(v.iva_porcentaje) * 100).toFixed(0) : '' }}%</span><span class="tabular-nums">{{ dinero(v.iva_monto) }}</span></div>
          </template>
          <div class="flex justify-between font-medium"><span>Total</span><span class="tabular-nums">{{ dinero(v.total) }}</span></div>
        </div>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Pagos y garantías</h2>
        <p class="cr-label mt-2">Pagos</p>
        <ul v-if="v.pagos.length" class="text-sm">
          <li v-for="p in v.pagos" :key="p.pago_id" class="flex justify-between py-0.5">
            <span>{{ p.medio_pago }} <span v-if="p.referencia" class="text-ink-3">· {{ p.referencia }}</span></span>
            <span class="tabular-nums">{{ dinero(p.monto) }}</span>
          </li>
        </ul>
        <p v-else class="text-sm text-ink-3">Sin pagos.</p>
        <p class="mt-1 text-sm">Saldo: <strong class="tabular-nums">{{ dinero(v.saldo) }}</strong></p>

        <p class="cr-label mt-3">Garantías</p>
        <ul v-if="v.garantias.length" class="text-sm">
          <li v-for="(g, i) in v.garantias" :key="i" class="flex justify-between py-0.5">
            <span>{{ g.tipo === 'fabrica' ? 'Fábrica' : 'Tienda' }} — {{ g.periodo_dias }} días</span>
            <span class="tabular-nums text-ink-3">hasta {{ g.fecha_fin }}</span>
          </li>
        </ul>
        <p v-else class="text-sm text-ink-3">Se registran al confirmar.</p>

        <p v-if="v.comprobantes.length" class="cr-label mt-3">Documentos</p>
        <div class="mt-1 flex flex-wrap gap-2">
          <button v-for="c in v.comprobantes" :key="c.objeto" class="cr-btn cr-btn-ghost text-xs" @click="verComprobantes">
            <CrIcon name="image" :size="13" /> {{ c.tipo === 'comprobante' ? 'Comprobante' : 'Certificado' }}
          </button>
        </div>
      </section>
    </div>

    <FinalizarVentaModal v-model="modalFinalizar" :venta="v" @hecho="cargar" />
    <PagoVentaModal v-model="modalPago" :venta="v" @hecho="cargar" />
    <AnularVentaModal v-model="modalAnular" :venta="v" @hecho="() => router.push({ name: 'ventas' })" />
  </div>
  <p v-else-if="cargando" class="p-8 text-sm text-ink-3">Cargando…</p>
</template>
