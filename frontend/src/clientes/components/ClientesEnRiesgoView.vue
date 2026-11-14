<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import KpiStrip from '@/shared/ui/KpiStrip.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { opcionesExportacion } from '@/shared/exportar'
import { toast } from '@/shared/ui/toast'
import { emitirCuponReactivacion, reporteClientesEnRiesgo } from '@/clientes/services/clientesApi'

const router = useRouter()
const filas = ref([])
const loading = ref(true)
const errorMsg = ref('')

const modal = reactive({ abierto: false, guardando: false, error: '', cliente: null })
const f = reactive({ tipo: 'porcentaje', valor: 0.15, vigencia_fin: '' })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    filas.value = await reporteClientesEnRiesgo()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)

const kpis = computed(() => [
  { label: 'Clientes en riesgo', value: String(filas.value.length) },
  { label: 'Críticos', value: String(filas.value.filter((x) => x.severidad === 'critico').length) },
  { label: 'Silencio máximo', value: filas.value.length ? `${Math.max(...filas.value.map((x) => x.dias_silencio))} d` : '—', gold: true },
])

const exportOpts = computed(() =>
  opcionesExportacion({
    filas: () => filas.value.map((x) => ({
      cliente: x.nombre, afiliado: x.numero_afiliado, nivel: x.nivel_nombre,
      ultima_compra: x.ultima_compra, dias_silencio: x.dias_silencio,
      cadencia_dias: x.cadencia_dias, ratio: x.ratio, severidad: x.severidad,
    })),
    totalFilas: filas.value.length,
    imprimirPdf: () => window.print(),
  }),
)

function abrirCupon(c) {
  modal.cliente = c
  Object.assign(f, { tipo: 'porcentaje', valor: 0.15, vigencia_fin: '' })
  modal.error = ''
  modal.abierto = true
}

async function emitir() {
  modal.error = ''
  if (!f.valor || Number(f.valor) <= 0) return (modal.error = 'Indica el valor del cupón.')
  if (f.tipo === 'porcentaje' && Number(f.valor) > 1) return (modal.error = 'El porcentaje va como fracción (0,15 = 15 %).')
  modal.guardando = true
  try {
    const cu = await emitirCuponReactivacion({
      cliente_id: modal.cliente.cliente_id, tipo: f.tipo, valor: Number(f.valor),
      vigencia_fin: f.vigencia_fin || null,
    })
    toast.success(`Cupón ${cu.codigo} emitido para ${modal.cliente.nombre}`)
    modal.abierto = false
  } catch (e) {
    modal.error = e.message
  } finally {
    modal.guardando = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Clientes · Retención"
      titulo="Clientes en riesgo de abandono"
      sub="Miembros Plata y Oro cuyo silencio supera su propio patrón de compra. Los umbrales (piso de días, factor, historial mínimo, ventana) se editan en Sistema · Parámetros."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'reportes-clientes' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Reportes</RouterLink>
        <div class="flex gap-1">
          <button v-for="o in exportOpts" :key="o.formato" class="cr-btn cr-btn-ghost text-xs" :disabled="!o.disponible" @click="o.ejecutar">{{ o.etiqueta }}</button>
        </div>
      </template>
    </PageHeader>

    <KpiStrip v-if="filas.length" :items="kpis" />

    <p v-if="errorMsg" class="mb-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-if="loading" class="text-sm text-ink-3">Analizando patrones de compra…</p>
    <p v-else-if="!filas.length" class="cr-card p-8 text-center text-ink-3">
      Ningún cliente Plata u Oro está en riesgo según los umbrales actuales. (El análisis necesita transacciones de 008 / 009.)
    </p>

    <div v-else class="cr-card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
            <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Cliente</th>
            <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Nivel</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Última compra</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Silencio</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Cadencia propia</th>
            <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Severidad</th>
            <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-hairline-soft">
          <tr v-for="x in filas" :key="x.cliente_id" class="cursor-pointer hover:bg-surface-sunk/40" @click="router.push({ name: 'cliente-ficha', params: { id: x.cliente_id } })">
            <td class="px-6 py-2.5">
              <span class="font-medium text-ink">{{ x.nombre }}</span>
              <span class="ml-1 text-xs text-ink-3">{{ x.numero_afiliado }}</span>
            </td>
            <td class="px-6 py-2.5">
              <span class="inline-flex rounded-full border border-gold/50 bg-gold-pale px-2 py-0.5 text-xs text-gold-strong">{{ x.nivel_nombre }}</span>
            </td>
            <td class="px-6 py-2.5 text-right tabular-nums">{{ x.ultima_compra }}</td>
            <td class="px-6 py-2.5 text-right tabular-nums" :class="x.severidad === 'critico' ? 'font-semibold text-bad' : 'text-ink'">
              {{ x.dias_silencio }} d <span class="text-ink-3">({{ x.ratio }}×)</span>
            </td>
            <td class="px-6 py-2.5 text-right tabular-nums text-ink-2">{{ x.cadencia_dias }} d · {{ x.transacciones }} tx</td>
            <td class="px-6 py-2.5">
              <Pill :tone="x.severidad === 'critico' ? 'bad' : 'warn'" :label="x.severidad === 'critico' ? 'crítico' : 'atención'" />
            </td>
            <td class="px-6 py-2.5 text-right">
              <button class="cr-btn cr-btn-ghost text-xs" @click.stop="abrirCupon(x)">Emitir cupón de reactivación</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <FormModal
      v-model="modal.abierto"
      :titulo="`Cupón de reactivación · ${modal.cliente?.nombre}`"
      subtitulo="Cupón puntual de uso único asignado a este cliente. El envío por correo lo gestiona Notificaciones (014)."
      :guardando="modal.guardando"
      @guardar="emitir"
    >
      <FormField label="Tipo" required>
        <select v-model="f.tipo" class="cr-input"><option value="porcentaje">Porcentaje</option><option value="monto">Monto fijo</option></select>
      </FormField>
      <FormField :label="f.tipo === 'porcentaje' ? 'Valor (fracción: 0,15 = 15 %)' : 'Monto ($)'" required>
        <input v-model="f.valor" type="number" min="0" step="0.01" class="cr-input" required />
      </FormField>
      <FormField label="Vencimiento" wide helper="Si se deja vacío: 60 días desde hoy.">
        <input v-model="f.vigencia_fin" type="date" class="cr-input" />
      </FormField>
      <p class="sm:col-span-2 text-xs text-ink-3">El código se genera como <span class="tabular-nums">REACT-{{ modal.cliente?.numero_afiliado?.split('-').pop() }}</span>.</p>
      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
