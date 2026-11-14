<script setup>
import { onMounted, reactive, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { crearReglaBono, listarReglasBono } from '@/tecnicos/services/tecnicosApi'

const TIPOS = [
  { value: 'monto_por_meta', label: 'Monto fijo por meta', ayuda: 'Paga un monto fijo si el indicador supera el umbral.' },
  { value: 'porcentaje_margen', label: '% sobre el margen generado', ayuda: 'Paga un porcentaje del margen del periodo (valor como fracción: 0,05 = 5 %).' },
  { value: 'combinacion', label: 'Combinación (fijo + % margen)', ayuda: 'Paga el valor como monto fijo y, además, ese mismo valor como fracción del margen.' },
]
const INDICADORES = [
  { value: 'ot_completadas', label: 'OT completadas', unidad: 'órdenes' },
  { value: 'cumplimiento_tiempos', label: 'Cumplimiento de tiempos', unidad: '% dentro del plazo' },
  { value: 'margen_generado', label: 'Margen generado', unidad: '$ del periodo' },
  { value: 'calidad', label: 'Calidad', unidad: '% sin reprocesos' },
]

const reglas = ref([])
const loading = ref(true)
const errorMsg = ref('')

const modal = reactive({ abierto: false, guardando: false, error: '' })
const f = reactive({ nombre: '', periodicidad: 'mensual', vigente_desde: new Date().toISOString().slice(0, 10), componentes: [] })

function componenteNuevo() {
  return { tipo: 'monto_por_meta', indicador: 'ot_completadas', umbral: 0, valor: 0 }
}

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    reglas.value = await listarReglasBono()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)

function abrir() {
  Object.assign(f, { nombre: '', periodicidad: 'mensual', vigente_desde: new Date().toISOString().slice(0, 10), componentes: [componenteNuevo()] })
  modal.error = ''
  modal.abierto = true
}

const etiquetaTipo = (v) => TIPOS.find((t) => t.value === v)?.label ?? v
const etiquetaIndicador = (v) => INDICADORES.find((i) => i.value === v)?.label ?? v

async function guardar() {
  modal.error = ''
  if (!f.nombre.trim() || f.nombre.trim().length < 2) return (modal.error = 'Ponle un nombre a la regla.')
  if (!f.componentes.length) return (modal.error = 'Agrega al menos un componente.')
  modal.guardando = true
  try {
    await crearReglaBono({
      nombre: f.nombre.trim(),
      periodicidad: f.periodicidad,
      vigente_desde: f.vigente_desde,
      componentes: f.componentes.map((c) => ({
        tipo: c.tipo, indicador: c.indicador,
        umbral: Number(c.umbral) || 0, valor: Number(c.valor) || 0,
      })),
    })
    toast.success('Regla de bono vigente — reemplaza a la anterior y recalcula los periodos abiertos')
    modal.abierto = false
    cargar()
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
      eyebrow="Técnicos"
      titulo="Reglas de bono por productividad"
      sub="La Gerencia General define la fórmula y los umbrales. Solo una regla está vigente a la vez; la nueva reemplaza a la anterior desde su fecha de vigencia."
    >
      <template #acciones>
        <button class="cr-btn cr-btn-primary" @click="abrir">Nueva regla</button>
      </template>
    </PageHeader>

    <p v-if="errorMsg" class="mb-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!reglas.length" class="cr-card p-8 text-center text-ink-3">
      Aún no hay reglas de bono. Hasta que definas una, el bono de todos los técnicos es 0.
    </p>

    <div v-else class="space-y-4">
      <article v-for="r in reglas" :key="r.id" class="cr-card p-6" :class="r.activa ? 'border-gold/50' : ''">
        <header class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 class="serif text-lg text-ink">{{ r.nombre }}</h2>
            <p class="text-xs text-ink-3">{{ r.periodicidad }} · vigente desde {{ r.vigente_desde }}</p>
          </div>
          <Pill :tone="r.activa ? 'good' : 'neutral'" :label="r.activa ? 'vigente' : 'reemplazada'" />
        </header>
        <table class="mt-4 w-full text-sm">
          <thead>
            <tr class="border-b border-hairline text-left text-[0.7rem] uppercase text-ink-2">
              <th class="py-1.5">Indicador</th><th class="py-1.5">Cómo paga</th>
              <th class="py-1.5 text-right">Umbral</th><th class="py-1.5 text-right">Valor</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-hairline-soft">
            <tr v-for="c in r.componentes" :key="c.id">
              <td class="py-1.5">{{ etiquetaIndicador(c.indicador) }}</td>
              <td class="py-1.5 text-ink-2">{{ etiquetaTipo(c.tipo) }}</td>
              <td class="py-1.5 text-right tabular-nums">{{ Number(c.umbral) }}</td>
              <td class="py-1.5 text-right tabular-nums">{{ Number(c.valor) }}</td>
            </tr>
          </tbody>
        </table>
      </article>
    </div>

    <FormModal
      v-model="modal.abierto"
      titulo="Nueva regla de bono"
      subtitulo="El bono del técnico = suma de los componentes cuyo indicador supera su umbral en el periodo. Nunca es negativo."
      :guardando="modal.guardando"
      ancho="max-w-3xl"
      @guardar="guardar"
    >
      <FormField label="Nombre" required><input v-model="f.nombre" class="cr-input" required /></FormField>
      <FormField label="Periodicidad" required>
        <select v-model="f.periodicidad" class="cr-input">
          <option value="mensual">Mensual</option>
          <option value="trimestral">Trimestral</option>
        </select>
      </FormField>
      <FormField label="Vigente desde" required><input v-model="f.vigente_desde" type="date" class="cr-input" required /></FormField>

      <div class="sm:col-span-2">
        <p class="cr-label mb-2">Componentes del bono</p>
        <div class="space-y-3">
          <div v-for="(c, i) in f.componentes" :key="i" class="rounded-xl border border-hairline bg-surface-sunk/40 p-3">
            <div class="mb-2 flex items-center justify-between">
              <span class="text-xs font-semibold uppercase tracking-wide text-ink-3">Componente {{ i + 1 }}</span>
              <button v-if="f.componentes.length > 1" type="button" class="text-xs text-bad hover:underline" @click="f.componentes.splice(i, 1)">Quitar</button>
            </div>
            <div class="grid gap-2 sm:grid-cols-2">
              <label class="space-y-1">
                <span class="cr-label">Indicador</span>
                <select v-model="c.indicador" class="cr-input">
                  <option v-for="ind in INDICADORES" :key="ind.value" :value="ind.value">{{ ind.label }}</option>
                </select>
              </label>
              <label class="space-y-1">
                <span class="cr-label">Cómo paga</span>
                <select v-model="c.tipo" class="cr-input">
                  <option v-for="tp in TIPOS" :key="tp.value" :value="tp.value">{{ tp.label }}</option>
                </select>
              </label>
              <label class="space-y-1">
                <span class="cr-label">Umbral <span class="font-normal normal-case text-ink-3">— {{ INDICADORES.find((x) => x.value === c.indicador)?.unidad }}</span></span>
                <input v-model.number="c.umbral" type="number" step="0.01" class="cr-input" />
              </label>
              <label class="space-y-1">
                <span class="cr-label">Valor <span class="font-normal normal-case text-ink-3">— {{ c.tipo === 'monto_por_meta' ? '$' : 'fracción (0,05 = 5 %)' }}</span></span>
                <input v-model.number="c.valor" type="number" step="0.0001" class="cr-input" />
              </label>
            </div>
            <p class="mt-1.5 text-xs text-ink-3">{{ TIPOS.find((x) => x.value === c.tipo)?.ayuda }}</p>
          </div>
        </div>
        <button type="button" class="cr-btn cr-btn-ghost mt-2 text-xs" @click="f.componentes.push(componenteNuevo())">
          <CrIcon name="plus" :size="14" /> Añadir componente
        </button>
      </div>

      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
