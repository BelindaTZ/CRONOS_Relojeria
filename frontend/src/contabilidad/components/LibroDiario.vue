<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { crearAsiento, getPlanCuentas, listarAsientos } from '@/contabilidad/services/contabilidadApi'

const session = useSessionStore()

const columns = [
  { key: 'fecha', label: 'Fecha' },
  { key: 'glosa', label: 'Glosa' },
  { key: 'origen', label: 'Origen' },
  { key: 'total', label: 'Total', align: 'right' },
]
const rows = ref([])
const total = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const page = ref(1)
const fOrigen = ref('')
const cuentas = ref([])
const modal = ref(false)

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await listarAsientos({ origen: fOrigen.value || undefined, page: page.value })
    rows.value = res.items
    total.value = res.total
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  cuentas.value = await getPlanCuentas().then((r) => r.filter((c) => c.imputable)).catch(() => [])
  cargar()
})
watch(fOrigen, () => { page.value = 1; cargar() })
watch(page, cargar)

const kpis = computed(() => [
  { label: 'Asientos (esta página)', value: String(rows.value.length) },
  { label: 'Total registrado', value: String(total.value), gold: true },
])

function vacio() {
  return { fecha: new Date().toISOString().slice(0, 10), glosa: '', lineas: [{ cuenta: '', debe: null, haber: null }, { cuenta: '', debe: null, haber: null }] }
}
const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')
watch(modal, (v) => { if (v) Object.assign(f, vacio()) })

const agregar = () => f.lineas.push({ cuenta: '', debe: null, haber: null })
const quitar = (i) => f.lineas.splice(i, 1)
const sumaDebe = computed(() => f.lineas.reduce((s, l) => s + Number(l.debe || 0), 0))
const sumaHaber = computed(() => f.lineas.reduce((s, l) => s + Number(l.haber || 0), 0))

async function guardar() {
  error.value = ''
  if (!f.glosa.trim()) return (error.value = 'La glosa es obligatoria.')
  if (f.lineas.some((l) => !l.cuenta)) return (error.value = 'Cada línea necesita una cuenta.')
  if (sumaDebe.value !== sumaHaber.value) return (error.value = `El asiento no cuadra: debe ${sumaDebe.value} ≠ haber ${sumaHaber.value}.`)
  guardando.value = true
  try {
    await crearAsiento({
      fecha: f.fecha, glosa: f.glosa.trim(),
      lineas: f.lineas.map((l) => ({ cuenta: l.cuenta, debe: Number(l.debe) || 0, haber: Number(l.haber) || 0 })),
    })
    toast.success('Asiento registrado')
    modal.value = false
    cargar()
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Contabilidad"
      titulo="Libro diario"
      sub="Asientos de partida doble. La suma del debe siempre iguala la del haber; el mayor, el balance y el estado de resultados se derivan de aquí."
      :columns="columns"
      :rows="rows"
      :total="total"
      :loading="loading"
      :error="errorMsg"
      v-model:page="page"
      :page-size="20"
      :kpis="kpis"
      empty-title="Aún no hay asientos"
      empty-hint="Los asientos se generan automáticamente al confirmar ventas, compras, gastos y servicios; también puedes registrar uno manual."
      empty-icon="history"
      @retry="cargar"
    >
      <template #actions>
        <RouterLink :to="{ name: 'plan-cuentas' }" class="cr-btn cr-btn-ghost">Plan de cuentas</RouterLink>
        <RouterLink :to="{ name: 'balance-comprobacion' }" class="cr-btn cr-btn-ghost">Balance</RouterLink>
        <RouterLink :to="{ name: 'estado-resultados' }" class="cr-btn cr-btn-ghost">Estado de resultados</RouterLink>
        <button v-if="session.puede('contable', 'crear')" class="cr-btn cr-btn-primary" @click="modal = true">Asiento manual</button>
      </template>
      <template #toolbar>
        <select v-model="fOrigen" class="cr-input max-w-[11rem]">
          <option value="">Todos los orígenes</option>
          <option value="manual">Manual</option>
          <option value="venta">Venta</option>
          <option value="ot">Servicio técnico</option>
          <option value="compra">Compra</option>
          <option value="gasto">Gasto</option>
          <option value="cobro">Cobro</option>
          <option value="pago">Pago</option>
          <option value="ajuste">Ajuste</option>
        </select>
      </template>

      <template #cell-fecha="{ row }"><span class="tabular-nums">{{ row.fecha }}</span></template>
      <template #cell-glosa="{ row }">{{ row.glosa }}</template>
      <template #cell-origen="{ row }">
        <span class="text-xs text-ink-3">{{ row.origen }}</span>
        <span v-if="row.ajuste_de_asiento_id" class="ml-1 text-xs text-gold-strong">ajuste de #{{ row.ajuste_de_asiento_id }}</span>
      </template>
      <template #cell-total="{ row }"><span class="tabular-nums">{{ dinero(row.total_debe) }}</span></template>
    </WorkPanel>

    <FormModal
      :model-value="modal" titulo="Asiento manual" subtitulo="Partida doble: el debe debe igualar al haber."
      :guardando="guardando" ancho="max-w-2xl" :sucio="!!f.glosa" @update:model-value="modal = $event" @guardar="guardar"
    >
      <FormField label="Fecha" required>
        <input v-model="f.fecha" type="date" class="cr-input" />
      </FormField>
      <FormField label="Glosa" required>
        <input v-model="f.glosa" class="cr-input" />
      </FormField>

      <div class="sm:col-span-2">
        <div class="mb-2 flex items-center justify-between">
          <span class="text-sm font-medium text-ink">Líneas</span>
          <button type="button" class="cr-btn cr-btn-ghost text-xs" @click="agregar"><CrIcon name="plus" :size="13" /> Añadir línea</button>
        </div>
        <div v-for="(l, i) in f.lineas" :key="i" class="mb-2 grid grid-cols-[1fr_7rem_7rem_auto] gap-2">
          <select v-model="l.cuenta" class="cr-input">
            <option value="">Cuenta…</option>
            <option v-for="c in cuentas" :key="c.id" :value="c.codigo">{{ c.codigo }} — {{ c.nombre }}</option>
          </select>
          <input v-model="l.debe" type="number" step="0.01" class="cr-input tabular-nums" placeholder="Debe" />
          <input v-model="l.haber" type="number" step="0.01" class="cr-input tabular-nums" placeholder="Haber" />
          <button type="button" class="text-xs text-bad" @click="quitar(i)">✕</button>
        </div>
        <p class="text-xs text-ink-3 tabular-nums">Debe: {{ dinero(sumaDebe) }} · Haber: {{ dinero(sumaHaber) }}</p>
      </div>
      <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
    </FormModal>
  </div>
</template>
