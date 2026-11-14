<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { prompt } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import { cancelarCita, confirmarCita, getAgenda, getConversionCitas } from '@/citas/services/citasApi'
import AtenderModal from './AtenderModal.vue'

const session = useSessionStore()
const MOTIVO = { compra: 'Compra', servicio_tecnico: 'Servicio técnico', consulta: 'Consulta' }
const TONO = { pendiente: 'neutral', confirmada: 'info', atendida: 'good' }

const rango = ref('dia')
const fecha = ref(new Date().toISOString().slice(0, 10))
const fSucursal = ref('')
const sucursales = ref([])
const citas = ref([])
const conversion = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const modalAtender = ref({ abierto: false, cita: null })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    citas.value = await getAgenda({ rango: rango.value, fecha: fecha.value, sucursal_id: fSucursal.value || undefined })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
async function refrescar() {
  conversion.value = await getConversionCitas().catch(() => null)
  cargar()
}
onMounted(async () => {
  sucursales.value = (await listarSucursales().catch(() => ({ items: [] }))).items
  refrescar()
})
watch([rango, fecha, fSucursal], cargar)

const grupos = computed(() => {
  const g = {}
  for (const c of citas.value) {
    const d = new Date(c.hora).toLocaleDateString()
    ;(g[d] ||= []).push(c)
  }
  return Object.entries(g)
})

const kpis = computed(() => [
  { label: rango.value === 'dia' ? 'Citas hoy' : 'Citas esta semana', value: String(citas.value.length) },
  { label: 'Confirmadas', value: String(citas.value.filter((c) => c.estado === 'confirmada').length) },
  {
    label: 'Conversión (histórica)',
    value: conversion.value ? `${(conversion.value.tasa * 100).toFixed(0)} %` : '—',
    sub: conversion.value ? `${conversion.value.con_transaccion}/${conversion.value.atendidas} atendidas con venta u OT` : '',
    gold: true,
  },
])

const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => citas.value.map((c) => ({
      hora: c.hora, cliente: c.cliente_nombre, motivo: c.motivo,
      canal: c.canal_nombre, sucursal: c.sucursal_nombre, estado: c.estado,
    })),
    totalFilas: citas.value.length,
    imprimirPdf: () => window.print(),
  }),
)

async function confirmar(c) {
  try {
    const r = await confirmarCita(c.id)
    toast.success(r.warning ? `Cita agendada en firme · ${r.warning}` : 'Cita agendada en firme')
    refrescar()
  } catch (e) {
    toast.error(e.message)
  }
}
async function cancelar(c) {
  const motivo = await prompt({
    title: `Cancelar la cita de ${c.cliente_nombre}`,
    message: 'Queda registrada como cancelada con el motivo.',
    label: 'Motivo de la cancelación',
  })
  if (!motivo) return
  try {
    await cancelarCita(c.id, motivo)
    toast.success('Cita cancelada')
    refrescar()
  } catch (e) {
    toast.error(e.message)
  }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Citas"
      titulo="Agenda"
      sub="Citas del día o de la semana, ordenadas por hora. Aquí el mostrador confirma las citas y marca «atendida» a medida que llegan los clientes."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'citas' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Citas</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div class="inline-flex rounded-lg border border-hairline p-0.5">
        <button
          v-for="r in ['dia', 'semana']"
          :key="r"
          class="rounded-md px-3 py-1 text-sm transition"
          :class="rango === r ? 'bg-surface-sunk font-medium text-ink' : 'text-ink-3 hover:text-ink-2'"
          @click="rango = r"
        >{{ r === 'dia' ? 'Día' : 'Semana' }}</button>
      </div>
      <input v-model="fecha" type="date" class="cr-input max-w-[11rem]" />
      <select v-model="fSucursal" class="cr-input max-w-[14rem]">
        <option value="">{{ session.esGerencia ? 'Todas las sucursales' : 'Mi sucursal' }}</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
      <p class="text-xs text-ink-3">
        <strong>Confirmar</strong>: la cita queda agendada en firme. <strong>Atender</strong>: el cliente llegó y fue atendido.
      </p>
    </div>

    <KpiStrip :items="kpis" />

    <p v-if="errorMsg" class="mb-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!citas.length" class="cr-card p-8 text-center text-ink-3">
      No hay citas para {{ rango === 'dia' ? 'este día' : 'esta semana' }} en la sucursal seleccionada.
    </p>

    <div v-else class="space-y-5">
      <section v-for="[dia, lista] in grupos" :key="dia" class="cr-card overflow-hidden p-0">
        <header class="border-b border-hairline bg-surface-sunk/50 px-6 py-2.5">
          <h2 class="serif text-base text-ink">{{ dia }}</h2>
        </header>
        <ul class="divide-y divide-hairline-soft">
          <li v-for="c in lista" :key="c.id" class="flex flex-wrap items-center gap-x-4 gap-y-2 px-6 py-3">
            <span class="serif w-14 shrink-0 text-lg text-ink tabular-nums">
              {{ new Date(c.hora).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) }}
            </span>
            <div class="min-w-[12rem] flex-1">
              <p class="text-sm font-medium text-ink">{{ c.cliente_nombre }} <span class="ml-1 text-xs font-normal text-ink-3">{{ c.cliente_afiliado }}</span></p>
              <p class="text-xs text-ink-3">{{ MOTIVO[c.motivo] || c.motivo }} · {{ c.canal_nombre }} · {{ c.sucursal_nombre }}</p>
            </div>
            <Pill :tone="TONO[c.estado] || 'neutral'" :label="c.estado" />
            <div class="flex gap-1">
              <button v-if="c.estado === 'pendiente'" class="cr-btn cr-btn-ghost text-xs" @click="confirmar(c)">Confirmar</button>
              <button v-if="['pendiente', 'confirmada'].includes(c.estado)" class="cr-btn cr-btn-ghost text-xs" @click="modalAtender = { abierto: true, cita: c }">Atender</button>
              <button v-if="['pendiente', 'confirmada'].includes(c.estado)" class="cr-btn cr-btn-ghost text-xs text-bad" @click="cancelar(c)">Cancelar</button>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <AtenderModal v-if="modalAtender.cita" v-model="modalAtender.abierto" :cita="modalAtender.cita" @atendida="refrescar" />
  </div>
</template>
