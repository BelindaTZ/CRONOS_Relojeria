<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { prompt } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarSucursales } from '@/sucursales'
import {
  abrirSesionCaja,
  cerrarSesionCaja,
  getSesionActual,
  registrarMovimientoCaja,
} from '@/contabilidad/services/contabilidadApi'

const session = useSessionStore()
const sucursales = ref([])
const sucursalId = ref(null)
const sesion = ref(null)
const loading = ref(true)
const modalMov = ref(false)

async function cargar() {
  if (!sucursalId.value) return
  loading.value = true
  sesion.value = await getSesionActual(sucursalId.value).catch(() => null)
  loading.value = false
}
onMounted(async () => {
  sucursales.value = await listarSucursales().then((r) => r.items).catch(() => [])
  const mias = session.perfil?.sucursal_ids || []
  sucursalId.value = mias.length ? mias[0] : sucursales.value[0]?.id || null
  cargar()
})
watch(sucursalId, cargar)

async function abrir() {
  const saldo = await prompt({ title: 'Abrir sesión de caja', message: 'Saldo inicial en efectivo con el que empieza el turno.', label: 'Saldo inicial' })
  if (saldo === null) return
  try {
    await abrirSesionCaja(sucursalId.value, Number(saldo) || 0)
    toast.success('Caja abierta')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const fMov = reactive({ tipo: 'entrada', monto: null, medio_pago: 'efectivo', nota: '' })
async function guardarMov() {
  if (!fMov.monto || Number(fMov.monto) <= 0) return toast.error('Indica el monto.')
  try {
    await registrarMovimientoCaja(sucursalId.value, { tipo: fMov.tipo, monto: Number(fMov.monto), medio_pago: fMov.medio_pago, nota: fMov.nota.trim() || null })
    toast.success('Movimiento registrado')
    modalMov.value = false
    Object.assign(fMov, { tipo: 'entrada', monto: null, medio_pago: 'efectivo', nota: '' })
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

async function cerrar() {
  const contado = await prompt({ title: 'Cerrar sesión de caja (arqueo)', message: 'Efectivo contado al cierre del turno.', label: 'Efectivo contado' })
  if (contado === null) return
  try {
    const r = await cerrarSesionCaja(sucursalId.value, Number(contado) || 0)
    toast.success(`Caja cerrada · diferencia ${r.diferencia}`)
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const kpis = computed(() => sesion.value ? [
  { label: 'Saldo inicial', value: dinero(sesion.value.saldo_inicial) },
  { label: 'Movimientos', value: String(sesion.value.movimientos.length) },
  { label: 'Estado', value: sesion.value.estado, gold: true },
] : [])
const dinero = (n) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: 2 }))
</script>

<template>
  <div>
    <PageHeader eyebrow="Contabilidad" titulo="Caja y bancos" sub="Apertura, movimientos y cierre con arqueo (diferencia entre efectivo esperado y contado) por sucursal.">
      <template #acciones>
        <template v-if="session.puede('contable', 'crear')">
          <button v-if="sesion" class="cr-btn cr-btn-ghost" @click="modalMov = true">Registrar movimiento</button>
          <button v-if="sesion" class="cr-btn cr-btn-danger" @click="cerrar">Cerrar caja (arqueo)</button>
          <button v-else class="cr-btn cr-btn-primary" @click="abrir">Abrir caja</button>
        </template>
      </template>
    </PageHeader>

    <select v-model="sucursalId" class="cr-input mb-4 max-w-[14rem]">
      <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
    </select>

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!sesion" class="cr-card p-8 text-center text-ink-3">Sin sesión de caja abierta para esta sucursal.</p>
    <template v-else>
      <KpiStrip :items="kpis" />
      <ul class="cr-card mt-4 divide-y divide-hairline-soft p-0">
        <li v-for="m in sesion.movimientos" :key="m.id" class="flex items-center justify-between gap-3 px-6 py-3 text-sm">
          <span :class="m.tipo === 'entrada' ? 'text-good' : 'text-bad'">{{ m.tipo === 'entrada' ? '+ ' : '− ' }}{{ dinero(m.monto) }}</span>
          <span class="flex-1 text-ink-3">{{ m.medio_pago }} <span v-if="m.nota">· {{ m.nota }}</span></span>
          <span class="tabular-nums text-xs text-ink-3">{{ new Date(m.creado_en).toLocaleTimeString() }}</span>
        </li>
        <li v-if="!sesion.movimientos.length" class="px-6 py-6 text-center text-ink-3">Sin movimientos todavía.</li>
      </ul>
    </template>

    <FormModal
      :model-value="modalMov" titulo="Registrar movimiento de caja" :guardando="false" ancho="max-w-md" :sucio="true"
      @update:model-value="modalMov = $event" @guardar="guardarMov"
    >
      <FormField label="Tipo">
        <select v-model="fMov.tipo" class="cr-input">
          <option value="entrada">Entrada</option>
          <option value="salida">Salida</option>
        </select>
      </FormField>
      <FormField label="Monto" required>
        <input v-model="fMov.monto" type="number" step="0.01" min="0.01" class="cr-input tabular-nums" />
      </FormField>
      <FormField label="Medio">
        <select v-model="fMov.medio_pago" class="cr-input">
          <option value="efectivo">Efectivo</option>
          <option value="transferencia">Transferencia</option>
          <option value="tarjeta">Tarjeta</option>
        </select>
      </FormField>
      <FormField label="Nota" wide>
        <input v-model="fMov.nota" class="cr-input" />
      </FormField>
    </FormModal>
  </div>
</template>
