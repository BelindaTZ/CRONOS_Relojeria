<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import {
  cambiarEstadoMerma, getMerma, subirDocumentoMerma,
} from '@/mermas/services/mermasApi'
import AutorizarBajaModal from './AutorizarBajaModal.vue'
import ReclamoModal from './ReclamoModal.vue'

const route = useRoute()
const router = useRouter()
const mid = Number(route.params.id)

const CAUSAS = {
  dano_tienda: 'Daño en tienda', dano_transito: 'Daño en tránsito', robo_perdida: 'Robo / pérdida',
  defecto_fabrica: 'Defecto de fábrica', dano_servicio: 'Daño durante servicio técnico',
  insumo_caducado: 'Insumo / repuesto caducado',
}
const ESTADOS = {
  en_evaluacion: 'En evaluación', dado_de_baja: 'Dado de baja', en_reclamo_proveedor: 'En reclamo — proveedor',
  en_reclamo_seguro: 'En reclamo — seguro', reparado_reingresado: 'Reparado y reingresado',
}
const TONO = {
  en_evaluacion: 'warn', dado_de_baja: 'bad', en_reclamo_proveedor: 'info',
  en_reclamo_seguro: 'info', reparado_reingresado: 'good',
}

const merma = ref(null)
const loading = ref(true)
const modalAutorizar = ref(false)
const modalReclamo = ref(false)
const subiendo = ref(false)

async function cargar() {
  loading.value = true
  merma.value = await getMerma(mid).catch(() => null)
  loading.value = false
}
onMounted(cargar)

const esTerminal = computed(() => ['dado_de_baja', 'reparado_reingresado'].includes(merma.value?.estado))
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })

async function darDeBaja() {
  if (!(await confirm({
    title: 'Dar de baja definitivamente',
    message: 'El bien sale del inventario activo y se genera el asiento de pérdida extraordinaria en Contabilidad. No es reversible desde aquí.',
    confirmLabel: 'Dar de baja', tone: 'danger',
  }))) return
  try {
    merma.value = await cambiarEstadoMerma(mid, 'dado_de_baja')
    toast.success('Merma dada de baja')
  } catch (e) {
    toast.error(e.status === 409 ? 'Supera el umbral — necesita autorización de Gerencia General primero.' : e.message)
  }
}

async function reingresar() {
  if (!(await confirm({
    title: 'Marcar como reparado y reingresado',
    message: 'El bien vuelve al inventario activo. La merma queda en el historial.',
    confirmLabel: 'Reingresar',
  }))) return
  try {
    merma.value = await cambiarEstadoMerma(mid, 'reparado_reingresado')
    toast.success('Bien reingresado al stock')
  } catch (e) {
    toast.error(e.message)
  }
}

async function subirArchivo(e) {
  const archivo = e.target.files?.[0]
  if (!archivo) return
  subiendo.value = true
  try {
    await subirDocumentoMerma(mid, 'acta', archivo)
    toast.success('Documento adjuntado')
    await cargar()
  } catch (err) {
    toast.error(err.message)
  } finally {
    subiendo.value = false
    e.target.value = ''
  }
}
</script>

<template>
  <div>
    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <template v-else-if="merma">
      <PageHeader :eyebrow="`Mermas · ${CAUSAS[merma.causa] || merma.causa}`" :titulo="merma.numero" :sub="`${merma.bien_tipo === 'reloj' ? 'Reloj ' + (merma.reloj_serie || '') : merma.pieza_codigo + ' × ' + merma.cantidad} — ${merma.sucursal_nombre}`">
        <template #acciones>
          <Pill :tone="TONO[merma.estado] || 'neutral'" :label="ESTADOS[merma.estado] || merma.estado" />
          <button class="cr-btn cr-btn-ghost" @click="router.push({ name: 'mermas' })"><CrIcon name="arrow-left" :size="15" /> Mermas</button>
          <template v-if="!esTerminal">
            <button class="cr-btn cr-btn-ghost" @click="modalAutorizar = true">Autorizar baja</button>
            <button class="cr-btn cr-btn-ghost" @click="modalReclamo = true">Reclamo</button>
            <button class="cr-btn cr-btn-ghost" @click="reingresar">Reparado y reingresado</button>
            <button class="cr-btn cr-btn-danger" @click="darDeBaja">Dar de baja</button>
          </template>
        </template>
      </PageHeader>

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="cr-card p-6">
          <p class="mb-3 text-xs uppercase tracking-wide text-ink-3">Datos del hecho</p>
          <dl class="space-y-2 text-sm">
            <div v-if="merma.categoria_merma_nombre" class="flex justify-between"><dt class="text-ink-3">Categoría</dt><dd>{{ merma.categoria_merma_nombre }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-3">Fecha del evento</dt><dd class="tabular-nums">{{ merma.fecha_evento }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-3">Responsable</dt><dd>{{ merma.responsable_nombre }}</dd></div>
            <div v-if="merma.costo_visible" class="flex justify-between"><dt class="text-ink-3">Costo de la pérdida</dt><dd class="tabular-nums text-gold-strong">{{ dinero(merma.costo_perdida) }}</dd></div>
            <div v-if="merma.tecnico_nombre" class="flex justify-between"><dt class="text-ink-3">Técnico (OT #{{ merma.orden_trabajo_id }})</dt><dd>{{ merma.tecnico_nombre }}</dd></div>
            <div v-if="merma.transferencia_id" class="flex justify-between"><dt class="text-ink-3">Transferencia</dt><dd>#{{ merma.transferencia_id }}</dd></div>
          </dl>
          <p v-if="merma.descripcion" class="mt-4 text-sm text-ink-2">{{ merma.descripcion }}</p>
          <div v-if="merma.autorizacion" class="mt-4 rounded-lg border border-hairline-soft bg-surface-2 p-3 text-sm">
            <p class="font-medium">Baja autorizada</p>
            <p class="text-ink-3">{{ merma.autorizacion.autorizador_nombre }} · {{ new Date(merma.autorizacion.fecha).toLocaleString() }}</p>
            <p v-if="merma.autorizacion.observacion" class="mt-1 text-ink-2">{{ merma.autorizacion.observacion }}</p>
          </div>
        </div>

        <div class="cr-card p-6">
          <div class="mb-3 flex items-center justify-between">
            <p class="text-xs uppercase tracking-wide text-ink-3">Documentos de soporte</p>
            <label class="cr-btn cr-btn-ghost cursor-pointer text-xs">
              <CrIcon name="upload" :size="14" /> Adjuntar
              <input type="file" class="hidden" :disabled="subiendo" @change="subirArchivo" />
            </label>
          </div>
          <ul v-if="merma.documentos.length" class="space-y-2 text-sm">
            <li v-for="d in merma.documentos" :key="d.id" class="flex items-center justify-between">
              <span>{{ d.nombre }} <span class="text-ink-3">({{ d.tipo }})</span></span>
              <a :href="d.url" target="_blank" rel="noopener" class="text-gold-strong hover:underline">Ver</a>
            </li>
          </ul>
          <p v-else class="text-sm text-ink-3">Sin documentos adjuntos (acta, fotografías, denuncia).</p>
        </div>
      </div>

      <div v-if="merma.reclamos.length" class="cr-card mt-4 p-6">
        <p class="mb-3 text-xs uppercase tracking-wide text-ink-3">Reclamo</p>
        <div v-for="r in merma.reclamos" :key="r.id" class="text-sm">
          <p>{{ r.destino === 'proveedor' ? `Proveedor: ${r.proveedor_nombre || '—'}` : `Aseguradora: ${r.aseguradora || '—'}` }}</p>
          <p class="text-ink-3">Estado: {{ r.estado }} · Recuperado: {{ dinero(r.monto_recuperado) }}</p>
        </div>
      </div>

      <div class="cr-card mt-4 p-6">
        <p class="mb-3 text-xs uppercase tracking-wide text-ink-3">Historial</p>
        <ul class="space-y-2 text-sm">
          <li v-for="(h, i) in merma.historial" :key="i" class="flex items-center justify-between">
            <span>{{ ESTADOS[h.estado] || h.estado }}</span>
            <span class="text-ink-3">{{ h.actor_nombre }} · {{ new Date(h.creado_en).toLocaleString() }}</span>
          </li>
        </ul>
      </div>
    </template>
    <p v-else class="cr-card p-8 text-center text-ink-3">Merma no encontrada.</p>

    <AutorizarBajaModal v-model="modalAutorizar" :merma-id="mid" @autorizado="(m) => (merma = m)" />
    <ReclamoModal v-model="modalReclamo" :merma-id="mid" @guardado="(m) => (merma = m)" />
  </div>
</template>
