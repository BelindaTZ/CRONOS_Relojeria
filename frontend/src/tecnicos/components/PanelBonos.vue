<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import {
  calcularBono,
  cerrarPeriodo,
  crearPeriodo,
  listarBonos,
  listarPeriodos,
} from '@/tecnicos/services/tecnicosApi'

const INDICADORES = {
  ot_completadas: 'OT completadas',
  cumplimiento_tiempos: 'Cumplimiento de tiempos',
  margen_generado: 'Margen generado',
  calidad: 'Calidad',
}

const periodos = ref([])
const periodoId = ref(null)
const bonos = ref([])
const loading = ref(false)
const errorMsg = ref('')
const expandido = ref(new Set())

const modal = reactive({ abierto: false, guardando: false, error: '', fecha_inicio: '', fecha_fin: '' })

const periodo = computed(() => periodos.value.find((p) => p.id === periodoId.value) || null)

async function cargarPeriodos() {
  periodos.value = await listarPeriodos().catch(() => [])
  if (!periodoId.value && periodos.value.length) periodoId.value = periodos.value[0].id
}
async function cargarBonos() {
  if (!periodoId.value) {
    bonos.value = []
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    bonos.value = await listarBonos({ periodo_id: periodoId.value })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  await cargarPeriodos()
  cargarBonos()
})
watch(periodoId, () => {
  expandido.value = new Set()
  cargarBonos()
})

const totalBonos = computed(() =>
  bonos.value.reduce((s, b) => s + Number(b.valor_total || 0), 0),
)
const kpis = computed(() => [
  { label: 'Técnicos con bono', value: String(bonos.value.filter((b) => Number(b.valor_total) > 0).length) },
  { label: 'Estado del periodo', value: periodo.value ? periodo.value.estado : '—' },
  { label: 'Total a pagar en bonos', value: `$ ${totalBonos.value.toLocaleString()}`, gold: true, sub: 'se suma al costo de mano de obra' },
])

function toggle(id) {
  const s = new Set(expandido.value)
  s.has(id) ? s.delete(id) : s.add(id)
  expandido.value = s
}

async function nuevoPeriodo() {
  modal.error = ''
  if (!modal.fecha_inicio || !modal.fecha_fin) return (modal.error = 'Indica el rango del periodo.')
  modal.guardando = true
  try {
    const p = await crearPeriodo({ fecha_inicio: modal.fecha_inicio, fecha_fin: modal.fecha_fin })
    toast.success('Periodo de liquidación creado')
    modal.abierto = false
    await cargarPeriodos()
    periodoId.value = p.id
  } catch (e) {
    modal.error = e.message
  } finally {
    modal.guardando = false
  }
}

async function calcular() {
  try {
    const r = await calcularBono({ periodo_id: periodoId.value })
    toast.success(`Bono calculado (preview) para ${r.length} técnico(s)`)
    cargarBonos()
  } catch (e) {
    toast.error(e.message)
  }
}

async function cerrar() {
  if (!(await confirm({
    title: 'Cerrar el periodo de liquidación',
    message: 'Los bonos quedan como DEFINITIVOS y ya no se recalculan aunque cambie la fórmula o los parámetros. Es irreversible.',
    confirmLabel: 'Cerrar periodo', tone: 'danger',
  }))) return
  try {
    await cerrarPeriodo(periodoId.value)
    toast.success('Periodo cerrado · bonos definitivos')
    await cargarPeriodos()
    cargarBonos()
  } catch (e) {
    toast.error(e.message)
  }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Técnicos"
      titulo="Bonos por periodo"
      sub="Motor de acumulación: evalúa la regla de bono vigente contra las órdenes de trabajo cerradas del periodo y prorratea el bono entre ellas."
    >
      <template #acciones>
        <button class="cr-btn cr-btn-ghost" @click="((modal.fecha_inicio = ''), (modal.fecha_fin = ''), (modal.error = ''), (modal.abierto = true))">
          Nuevo periodo
        </button>
        <button v-if="periodo && periodo.estado === 'abierto'" class="cr-btn cr-btn-primary" @click="calcular">Calcular (preview)</button>
        <button v-if="periodo && periodo.estado === 'abierto'" class="cr-btn cr-btn-danger" @click="cerrar">Cerrar periodo</button>
      </template>
    </PageHeader>

    <div class="mb-6 flex flex-wrap items-center gap-3">
      <label class="text-sm text-ink-2">Periodo</label>
      <select v-model="periodoId" class="cr-input max-w-[18rem]">
        <option v-if="!periodos.length" :value="null">— sin periodos —</option>
        <option v-for="p in periodos" :key="p.id" :value="p.id">
          {{ p.fecha_inicio }} → {{ p.fecha_fin }} ({{ p.estado }})
        </option>
      </select>
      <Pill v-if="periodo" :tone="periodo.estado === 'cerrado' ? 'good' : 'warn'" :label="periodo.estado" />
    </div>

    <KpiStrip v-if="periodo" :items="kpis" />

    <p v-if="errorMsg" class="mb-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-if="!periodo" class="cr-card p-8 text-center text-ink-3">
      Crea un periodo de liquidación (mensual o trimestral) para calcular los bonos.
    </p>
    <p v-else-if="loading" class="text-sm text-ink-3">Calculando…</p>
    <p v-else-if="!bonos.length" class="cr-card p-8 text-center text-ink-3">
      Este periodo aún no tiene bonos calculados. Usa «Calcular (preview)».
    </p>

    <div v-else class="cr-card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
            <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Técnico</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Bono</th>
            <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Estado</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Desglose</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-hairline-soft">
          <template v-for="b in bonos" :key="b.tecnico_id">
            <tr>
              <td class="px-6 py-2.5 font-medium text-ink">{{ b.tecnico_nombre || `#${b.tecnico_id}` }}</td>
              <td class="px-6 py-2.5 text-right tabular-nums" :class="Number(b.valor_total) > 0 ? 'text-gold-strong font-medium' : 'text-ink-3'">
                $ {{ Number(b.valor_total).toLocaleString() }}
              </td>
              <td class="px-6 py-2.5"><Pill :tone="b.estado === 'definitivo' ? 'good' : 'warn'" :label="b.estado" /></td>
              <td class="px-6 py-2.5 text-right">
                <button class="text-xs text-gold-strong hover:underline" @click="toggle(b.tecnico_id)">
                  {{ expandido.has(b.tecnico_id) ? 'Ocultar' : 'Ver' }}
                </button>
              </td>
            </tr>
            <tr v-if="expandido.has(b.tecnico_id)" class="bg-surface-sunk/50">
              <td colspan="4" class="px-6 py-3">
                <div class="grid gap-4 sm:grid-cols-2">
                  <div>
                    <p class="cr-label mb-1">Indicadores del periodo</p>
                    <dl class="space-y-1 text-xs">
                      <div v-for="(v, k) in (b.desglose?.indicadores || {})" :key="k" class="flex justify-between gap-4">
                        <dt class="text-ink-3">{{ INDICADORES[k] || k }}</dt>
                        <dd class="tabular-nums">{{ Number(v).toLocaleString() }}</dd>
                      </div>
                    </dl>
                  </div>
                  <div>
                    <p class="cr-label mb-1">Componentes de la regla</p>
                    <ul v-if="b.desglose?.componentes?.length" class="space-y-1 text-xs">
                      <li v-for="(c, i) in b.desglose.componentes" :key="i" class="flex items-center justify-between gap-3">
                        <span :class="c.aporta ? 'text-ink-2' : 'text-ink-3 line-through'">
                          {{ INDICADORES[c.indicador] || c.indicador }} ≥ {{ c.umbral }}
                        </span>
                        <span class="flex items-center gap-1 tabular-nums">
                          <CrIcon v-if="c.aporta" name="circle-check" :size="13" class="text-good" />
                          <CrIcon v-else name="ban" :size="13" class="text-ink-3" />
                          $ {{ Number(c.monto).toLocaleString() }}
                        </span>
                      </li>
                    </ul>
                    <p v-else class="text-xs text-ink-3">
                      {{ b.desglose?.sin_regla_vigente ? 'No hay regla de bono vigente para este periodo.'
                        : b.desglose?.sin_ot_en_el_periodo ? 'Sin órdenes de trabajo cerradas en el periodo — el bono es 0.'
                        : '—' }}
                    </p>
                  </div>
                </div>
                <p v-if="b.bono_ot?.length" class="mt-3 text-xs text-ink-3">
                  Prorrateado entre {{ b.bono_ot.length }} orden(es) de trabajo, proporcional al costo de mano de obra de cada una.
                </p>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <FormModal
      v-model="modal.abierto"
      titulo="Nuevo periodo de liquidación"
      :guardando="modal.guardando"
      @guardar="nuevoPeriodo"
    >
      <FormField label="Fecha de inicio" required><input v-model="modal.fecha_inicio" type="date" class="cr-input" required /></FormField>
      <FormField label="Fecha de fin" required><input v-model="modal.fecha_fin" type="date" class="cr-input" required /></FormField>
      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
