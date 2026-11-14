<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { confirm } from '@/shared/ui/dialogs'
import {
  cambiarEstado,
  getCosteo,
  getDocumento,
  getOrdenTrabajo,
} from '@/servicio_tecnico/services/servicioTecnicoApi'
import AccionOtModal from './AccionOtModal.vue'
import PresupuestoModal from './PresupuestoModal.vue'
import AprobarPresupuestoModal from './AprobarPresupuestoModal.vue'
import PiezaOtModal from './PiezaOtModal.vue'
import LubricacionOtModal from './LubricacionOtModal.vue'
import { MermaFormModal } from '@/mermas'

const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)

const ot = ref(null)
const costeo = ref(null)
const cargando = ref(true)

const modalAccion = ref({ abierto: false, tipo: '' })
const modalPresu = ref(false)
const modalAprobar = ref(false)
const modalPieza = ref(false)
const modalLub = ref(false)
const modalMerma = ref(false)
const mermaPrefill = ref(null)

function abrirMermaDesdeDano(payload) {
  mermaPrefill.value = payload
  modalMerma.value = true
}

const TONO = {
  recibido: 'neutral', en_diagnostico: 'info', presupuesto: 'warn',
  en_reparacion: 'info', listo: 'good', entregado: 'good', cancelada: 'bad',
}
const ETIQ = {
  recibido: 'Recibido', en_diagnostico: 'En diagnóstico', presupuesto: 'Presupuesto',
  en_reparacion: 'En reparación', listo: 'Listo', entregado: 'Entregado', cancelada: 'Cancelada',
}

async function cargar() {
  cargando.value = true
  try {
    ot.value = await getOrdenTrabajo(id)
    costeo.value = ot.value.costos_visibles ? await getCosteo(id).catch(() => null) : null
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

function abrir(tipo) {
  modalAccion.value = { abierto: true, tipo }
}

const kpis = computed(() => {
  if (!ot.value) return []
  const k = [
    { label: 'Estado', value: ETIQ[ot.value.estado] || ot.value.estado },
    { label: 'Ingreso', value: new Date(ot.value.fecha_ingreso).toLocaleDateString() },
    {
      label: 'Entrega estimada',
      value: ot.value.fecha_estimada_entrega ? new Date(ot.value.fecha_estimada_entrega).toLocaleDateString() : '— tras diagnóstico',
    },
  ]
  if (ot.value.precio_cobrado != null) {
    k.push({ label: 'Precio · saldo', value: `${ot.value.precio_cobrado} · ${ot.value.saldo ?? 0}`, gold: true })
  }
  return k
})

async function pasarA(estado, label) {
  if (!(await confirm({ title: `Mover a «${label}»`, message: '¿Confirmas el cambio de estado de la orden?', confirmLabel: label }))) return
  try {
    await cambiarEstado(id, estado)
    toast.success(`Orden en «${label}»`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

async function verDocumento(tipo) {
  try {
    const { url } = await getDocumento(id, tipo)
    window.open(url, '_blank', 'noopener')
  } catch (e) {
    toast.error(e.message)
  }
}
const dinero = (v) => (v == null ? '—' : Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 }))
</script>

<template>
  <div v-if="ot">
    <PageHeader
      eyebrow="Taller · Orden de trabajo"
      :titulo="`${ot.numero} — ${ot.reloj_marca} ${ot.reloj_referencia}`"
      :sub="`N.º de serie ${ot.reloj_serie} · ${ot.cliente_nombre} (${ot.cliente_afiliado})`"
    >
      <template #acciones>
        <RouterLink :to="{ name: 'ordenes-trabajo' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Órdenes</RouterLink>
        <button v-if="ot.estado === 'recibido' || ot.estado === 'en_diagnostico'" class="cr-btn cr-btn-ghost" @click="abrir('diagnostico')">Diagnóstico</button>
        <button v-if="['en_diagnostico', 'presupuesto'].includes(ot.estado)" class="cr-btn cr-btn-ghost" @click="modalPresu = true">Presupuesto</button>
        <button v-if="ot.estado === 'presupuesto'" class="cr-btn cr-btn-primary" @click="modalAprobar = true">Registrar aprobación</button>
        <button v-if="ot.estado === 'en_reparacion'" class="cr-btn cr-btn-ghost" @click="modalPieza = true">Añadir pieza</button>
        <button v-if="ot.estado === 'en_reparacion'" class="cr-btn cr-btn-ghost" @click="modalLub = true">Lubricación</button>
        <button v-if="ot.estado === 'en_reparacion'" class="cr-btn cr-btn-ghost" @click="abrir('horas')">Horas</button>
        <button v-if="ot.estado === 'en_reparacion'" class="cr-btn cr-btn-ghost" @click="abrir('trabajo')">Trabajo realizado</button>
        <button v-if="ot.estado === 'en_reparacion'" class="cr-btn cr-btn-primary" @click="pasarA('listo', 'Listo')">Marcar listo</button>
        <button v-if="['en_reparacion', 'listo'].includes(ot.estado)" class="cr-btn cr-btn-ghost" @click="abrir('descuento')">Descuento</button>
        <button v-if="['en_reparacion', 'listo'].includes(ot.estado)" class="cr-btn cr-btn-ghost" @click="abrir('pago')">Registrar pago</button>
        <button v-if="ot.estado === 'listo'" class="cr-btn cr-btn-primary" @click="abrir('entregar')">Entregar</button>
        <button v-if="ot.estado === 'entregado'" class="cr-btn cr-btn-ghost" @click="abrir('reabrir')">Reabrir por garantía</button>
        <button v-if="['en_reparacion', 'listo'].includes(ot.estado)" class="cr-btn cr-btn-ghost" @click="abrir('dano')">Reportar daño</button>
      </template>
    </PageHeader>

    <div class="mb-5 flex flex-wrap items-center gap-3">
      <Pill :tone="TONO[ot.estado] || 'neutral'" :label="ETIQ[ot.estado] || ot.estado" />
      <span v-if="ot.reproceso" class="rounded-full bg-warn-bg px-2 py-0.5 text-xs text-warn">Reproceso / reclamo</span>
      <span v-if="ot.ot_original_id" class="text-xs text-ink-3">Reapertura de la OT #{{ ot.ot_original_id }}</span>
      <span class="text-xs text-ink-3">Técnico: {{ ot.tecnico_nombre || '— sin asignar' }}</span>
    </div>

    <KpiStrip :items="kpis" />

    <div class="mt-6 grid gap-5 lg:grid-cols-2">
      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Motivo y diagnóstico</h2>
        <p class="mt-3 text-sm"><span class="cr-label">Motivo</span><br />{{ ot.motivo }}</p>
        <p class="mt-3 text-sm"><span class="cr-label">Diagnóstico</span><br />{{ ot.diagnostico || '— pendiente' }}</p>
        <p class="mt-3 text-sm"><span class="cr-label">Trabajo realizado</span><br />{{ ot.trabajo_realizado || '—' }}</p>
        <p class="mt-3 text-sm"><span class="cr-label">Garantía</span><br />{{ ot.garantia_cobertura }} · {{ ot.garantia_periodo_dias }} días</p>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Costeo del servicio</h2>
        <template v-if="ot.costos_visibles && costeo">
          <dl class="mt-3 space-y-1.5 text-sm">
            <div class="flex justify-between"><dt class="text-ink-3">Mano de obra</dt><dd class="tabular-nums">{{ dinero(costeo.costo_mano_obra) }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-3">Bono prorrateado</dt><dd class="tabular-nums">{{ dinero(costeo.bono_prorrateado) }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-3">Piezas</dt><dd class="tabular-nums">{{ dinero(costeo.costo_piezas) }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-3">Insumos</dt><dd class="tabular-nums">{{ dinero(costeo.costo_insumos) }}</dd></div>
            <div class="flex justify-between border-t border-hairline-soft pt-1.5 font-medium"><dt>Costo interno</dt><dd class="tabular-nums">{{ dinero(costeo.costo_interno) }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-3">Precio sugerido ({{ (Number(costeo.margen_objetivo) * 100).toFixed(0) }} % margen)</dt><dd class="tabular-nums">{{ dinero(costeo.precio_sugerido) }}</dd></div>
            <div class="flex justify-between text-gold-strong"><dt>Margen real</dt><dd class="tabular-nums">{{ dinero(costeo.margen_real) }}</dd></div>
          </dl>
          <p class="mt-3 text-xs text-ink-3">El costo de mano de obra y el margen nunca aparecen en el documento del cliente.</p>
        </template>
        <p v-else class="mt-4 flex items-center gap-2 text-sm text-ink-3"><CrIcon name="lock" :size="14" /> Restringido a roles administrativos.</p>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Presupuesto</h2>
        <template v-if="ot.presupuesto">
          <p class="mt-2 text-sm">Precio del servicio: <strong class="tabular-nums">{{ dinero(ot.presupuesto.precio_servicio) }}</strong> · estado: {{ ot.presupuesto.estado }}</p>
          <p v-if="ot.presupuesto.confirmado_por" class="text-xs text-ink-3">Confirmado por {{ ot.presupuesto.confirmado_por }} ({{ ot.presupuesto.medio_confirmacion }})</p>
          <ul class="mt-3 divide-y divide-hairline-soft text-sm">
            <li v-for="l in ot.presupuesto.lineas" :key="l.id" class="flex flex-wrap justify-between gap-2 py-1.5">
              <span>{{ l.pieza_original }} <span v-if="l.pieza_no_original" class="text-ink-3">/ {{ l.pieza_no_original }}</span> ×{{ l.cantidad }}</span>
              <span class="tabular-nums text-ink-3">
                {{ dinero(l.precio_original) }}<span v-if="l.precio_no_original"> / {{ dinero(l.precio_no_original) }}</span>
                <span v-if="l.preferencia_cliente" class="ml-1 text-gold-strong">→ {{ l.preferencia_cliente }}</span>
              </span>
            </li>
          </ul>
        </template>
        <p v-else class="mt-3 text-sm text-ink-3">Sin presupuesto todavía.</p>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Piezas y lubricación</h2>
        <p class="cr-label mt-2">Piezas usadas</p>
        <ul v-if="ot.piezas.length" class="text-sm">
          <li v-for="p in ot.piezas" :key="p.id" class="flex justify-between py-0.5">
            <span>{{ p.pieza_codigo }} — {{ p.descripcion }} ({{ p.tipo_elegido }}) ×{{ p.cantidad }}</span>
            <span v-if="p.costo != null" class="tabular-nums text-ink-3">{{ dinero(p.costo) }}</span>
          </li>
        </ul>
        <p v-else class="text-sm text-ink-3">—</p>
        <p class="cr-label mt-3">Lubricación (recomendado → usado)</p>
        <ul v-if="ot.lubricacion.length" class="text-sm">
          <li v-for="r in ot.lubricacion" :key="r.id" class="flex justify-between py-0.5">
            <span>{{ r.punto_nombre }}</span>
            <span class="tabular-nums" :class="r.desviacion ? 'text-warn' : 'text-ink-3'">
              {{ r.producto_recomendado || '—' }} → {{ r.producto_usado }}<span v-if="r.desviacion"> ⚠</span>
            </span>
          </li>
        </ul>
        <p v-else class="text-sm text-ink-3">—</p>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Pagos</h2>
        <ul v-if="ot.pagos.length" class="text-sm">
          <li v-for="p in ot.pagos" :key="p.pago_id" class="flex justify-between py-0.5">
            <span>{{ p.medio_pago }} <span v-if="p.referencia" class="text-ink-3">· {{ p.referencia }}</span></span>
            <span class="tabular-nums">{{ dinero(p.monto) }}</span>
          </li>
        </ul>
        <p v-else class="text-sm text-ink-3">Sin pagos registrados.</p>
        <p class="mt-2 text-sm">Saldo pendiente: <strong class="tabular-nums">{{ ot.saldo ?? '—' }}</strong></p>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Historial y documentos</h2>
        <ol class="mt-2 space-y-1 text-sm">
          <li v-for="(h, i) in ot.historial" :key="i" class="flex justify-between text-ink-2">
            <span>{{ ETIQ[h.estado] || h.estado }}</span>
            <span class="tabular-nums text-ink-3">{{ new Date(h.timestamp).toLocaleString() }}</span>
          </li>
        </ol>
        <div v-if="ot.documentos.length" class="mt-3 flex flex-wrap gap-2">
          <button v-for="d in ot.documentos" :key="d.tipo" class="cr-btn cr-btn-ghost text-xs" @click="verDocumento(d.tipo)">
            <CrIcon name="image" :size="13" /> {{ d.tipo === 'orden_trabajo' ? 'Documento de la OT' : 'Certificado de garantía' }}
          </button>
        </div>
        <p v-else-if="ot.estado === 'entregado'" class="mt-3 text-xs text-ink-3">Los documentos se generan al entregar.</p>
      </section>
    </div>

    <AccionOtModal
      v-model="modalAccion.abierto" :tipo="modalAccion.tipo" :ot="ot" @hecho="cargar"
      @merma-pendiente="abrirMermaDesdeDano"
    />
    <MermaFormModal
      v-model="modalMerma" :prefill="mermaPrefill"
      @guardado="(m) => { toast.success('Merma registrada'); router.push({ name: 'merma-ficha', params: { id: m.id } }) }"
    />
    <PresupuestoModal v-model="modalPresu" :ot="ot" @hecho="cargar" />
    <AprobarPresupuestoModal v-model="modalAprobar" :ot="ot" :presupuesto="ot.presupuesto" @hecho="cargar" />
    <PiezaOtModal v-model="modalPieza" :ot="ot" @hecho="cargar" />
    <LubricacionOtModal v-model="modalLub" :ot="ot" @hecho="cargar" />
  </div>
  <p v-else-if="cargando" class="p-8 text-sm text-ink-3">Cargando…</p>
</template>
