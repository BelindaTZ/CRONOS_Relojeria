<script setup>
import { onMounted, reactive, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { crearNivel, listarNiveles, setReglaNivel } from '@/clientes/services/clientesApi'

const CRITERIOS = [
  { value: 'monto_acumulado', label: 'Monto acumulado' },
  { value: 'frecuencia', label: 'Frecuencia (n.º de operaciones)' },
  { value: 'combinacion', label: 'Combinación (monto y frecuencia)' },
]

const niveles = ref([])
const loading = ref(true)
const errorMsg = ref('')

const modalNivel = reactive({ abierto: false, guardando: false, error: '' })
const fn = reactive({ nombre: '', orden: 2, beneficios: [{ clave: '', valor: '' }],
  regla: { criterio: 'monto_acumulado', ventana_meses: 12, umbral_monto: null, umbral_frecuencia: null } })

const modalRegla = reactive({ abierto: false, guardando: false, error: '', nivel: null })
const fr = reactive({ criterio: 'monto_acumulado', ventana_meses: 12, umbral_monto: null, umbral_frecuencia: null })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    niveles.value = await listarNiveles()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)

function abrirNivel() {
  Object.assign(fn, {
    nombre: '', orden: (niveles.value.at(-1)?.orden ?? 1) + 1,
    beneficios: [{ clave: '', valor: '' }],
    regla: { criterio: 'monto_acumulado', ventana_meses: 12, umbral_monto: null, umbral_frecuencia: null },
  })
  modalNivel.error = ''
  modalNivel.abierto = true
}

function abrirRegla(n) {
  modalRegla.nivel = n
  Object.assign(fr, {
    criterio: n.regla_vigente?.criterio ?? 'monto_acumulado',
    ventana_meses: n.regla_vigente?.ventana_meses ?? 12,
    umbral_monto: n.regla_vigente?.umbral_monto ?? null,
    umbral_frecuencia: n.regla_vigente?.umbral_frecuencia ?? null,
  })
  modalRegla.error = ''
  modalRegla.abierto = true
}

function beneficiosObjeto(lista) {
  const o = {}
  for (const b of lista) {
    if (!b.clave.trim()) continue
    const num = Number(b.valor)
    o[b.clave.trim()] = Number.isFinite(num) && b.valor !== '' ? num : b.valor
  }
  return o
}

async function guardarNivel() {
  modalNivel.error = ''
  if (fn.nombre.trim().length < 2) return (modalNivel.error = 'Ponle un nombre al nivel.')
  modalNivel.guardando = true
  try {
    await crearNivel({
      nombre: fn.nombre.trim(), orden: Number(fn.orden), beneficios: beneficiosObjeto(fn.beneficios),
      es_base: false,
      regla: {
        criterio: fn.regla.criterio, ventana_meses: Number(fn.regla.ventana_meses),
        umbral_monto: fn.regla.umbral_monto === null || fn.regla.umbral_monto === '' ? null : Number(fn.regla.umbral_monto),
        umbral_frecuencia: fn.regla.umbral_frecuencia === null || fn.regla.umbral_frecuencia === '' ? null : Number(fn.regla.umbral_frecuencia),
      },
    })
    toast.success('Nivel creado — se reclasificaron los clientes')
    modalNivel.abierto = false
    cargar()
  } catch (e) {
    modalNivel.error = e.message
  } finally {
    modalNivel.guardando = false
  }
}

async function guardarRegla() {
  modalRegla.guardando = true
  try {
    await setReglaNivel(modalRegla.nivel.id, {
      criterio: fr.criterio, ventana_meses: Number(fr.ventana_meses),
      umbral_monto: fr.umbral_monto === null || fr.umbral_monto === '' ? null : Number(fr.umbral_monto),
      umbral_frecuencia: fr.umbral_frecuencia === null || fr.umbral_frecuencia === '' ? null : Number(fr.umbral_frecuencia),
    })
    toast.success('Regla actualizada — recálculo masivo de niveles en curso')
    modalRegla.abierto = false
    cargar()
  } catch (e) {
    modalRegla.error = e.message
  } finally {
    modalRegla.guardando = false
  }
}

const critLabel = (v) => CRITERIOS.find((x) => x.value === v)?.label ?? v
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Clientes"
      titulo="Niveles de fidelización"
      sub="La Gerencia General define nombres, criterios, umbrales y beneficios. Cambiar una regla reclasifica a todos los clientes; el historial de niveles se conserva."
    >
      <template #acciones>
        <button class="cr-btn cr-btn-primary" @click="abrirNivel">Nuevo nivel</button>
      </template>
    </PageHeader>

    <p v-if="errorMsg" class="mb-4 text-sm text-bad" role="alert">{{ errorMsg }}</p>
    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>

    <div v-else class="space-y-4">
      <article v-for="n in niveles" :key="n.id" class="cr-card p-6" :class="n.es_base ? '' : 'border-gold/40'">
        <header class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="serif text-lg text-ink">{{ n.nombre }}</span>
            <Pill :tone="n.es_base ? 'neutral' : 'good'" :label="n.es_base ? 'base' : `orden ${n.orden}`" />
            <span class="text-xs text-ink-3">{{ n.clientes }} cliente(s)</span>
          </div>
          <button v-if="!n.es_base" class="cr-btn cr-btn-ghost text-xs" @click="abrirRegla(n)">Editar regla</button>
        </header>
        <div v-if="!n.es_base" class="mt-3 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <p class="cr-label mb-1">Regla del nivel</p>
            <p v-if="n.regla_vigente" class="text-ink-2">
              {{ critLabel(n.regla_vigente.criterio) }} · ventana {{ n.regla_vigente.ventana_meses }} meses
              <span v-if="n.regla_vigente.umbral_monto"> · ≥ $ {{ Number(n.regla_vigente.umbral_monto).toLocaleString() }}</span>
              <span v-if="n.regla_vigente.umbral_frecuencia"> · ≥ {{ n.regla_vigente.umbral_frecuencia }} operaciones</span>
            </p>
            <p v-else class="text-ink-3">Sin regla — nunca se alcanza.</p>
          </div>
          <div>
            <p class="cr-label mb-1">Beneficios</p>
            <ul v-if="Object.keys(n.beneficios || {}).length" class="text-ink-2">
              <li v-for="[k, v] in Object.entries(n.beneficios)" :key="k">
                {{ k.replace(/_/g, ' ') }}: <span class="tabular-nums">{{ typeof v === 'number' && v < 1 ? `${(v * 100).toFixed(0)} %` : v }}</span>
              </li>
            </ul>
            <p v-else class="text-ink-3">—</p>
          </div>
        </div>
      </article>
    </div>

    <!-- nuevo nivel -->
    <FormModal v-model="modalNivel.abierto" titulo="Nuevo nivel de fidelización" :guardando="modalNivel.guardando" ancho="max-w-2xl" @guardar="guardarNivel">
      <FormField label="Nombre" required><input v-model="fn.nombre" class="cr-input" required /></FormField>
      <FormField label="Orden" required helper="Mayor número = nivel superior."><input v-model.number="fn.orden" type="number" min="2" class="cr-input" /></FormField>

      <div class="sm:col-span-2 rounded-xl border border-hairline bg-surface-sunk/40 p-3">
        <p class="cr-label mb-2">Regla — cómo se alcanza este nivel</p>
        <div class="grid gap-2 sm:grid-cols-2">
          <label class="space-y-1"><span class="cr-label">Criterio</span>
            <select v-model="fn.regla.criterio" class="cr-input">
              <option v-for="cr in CRITERIOS" :key="cr.value" :value="cr.value">{{ cr.label }}</option>
            </select>
          </label>
          <label class="space-y-1"><span class="cr-label">Ventana (meses)</span>
            <input v-model.number="fn.regla.ventana_meses" type="number" min="1" max="120" class="cr-input" />
          </label>
          <label v-if="fn.regla.criterio !== 'frecuencia'" class="space-y-1"><span class="cr-label">Umbral de monto ($)</span>
            <input v-model="fn.regla.umbral_monto" type="number" min="0" step="0.01" class="cr-input" />
          </label>
          <label v-if="fn.regla.criterio !== 'monto_acumulado'" class="space-y-1"><span class="cr-label">Umbral de frecuencia</span>
            <input v-model="fn.regla.umbral_frecuencia" type="number" min="0" class="cr-input" />
          </label>
        </div>
      </div>

      <div class="sm:col-span-2">
        <p class="cr-label mb-2">Beneficios (clave / valor)</p>
        <div class="space-y-2">
          <div v-for="(b, i) in fn.beneficios" :key="i" class="flex gap-2">
            <input v-model="b.clave" class="cr-input" placeholder="p. ej. desc_servicio" />
            <input v-model="b.valor" class="cr-input max-w-[10rem]" placeholder="0.10" />
            <button v-if="fn.beneficios.length > 1" type="button" class="text-xs text-bad" @click="fn.beneficios.splice(i, 1)">Quitar</button>
          </div>
        </div>
        <button type="button" class="cr-btn cr-btn-ghost mt-2 text-xs" @click="fn.beneficios.push({ clave: '', valor: '' })">
          <CrIcon name="plus" :size="14" /> Añadir beneficio
        </button>
      </div>

      <p v-if="modalNivel.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modalNivel.error }}</p>
    </FormModal>

    <!-- editar regla -->
    <FormModal
      v-model="modalRegla.abierto"
      :titulo="`Regla de «${modalRegla.nivel?.nombre}»`"
      subtitulo="Guardar dispara el recálculo masivo de niveles (proceso diferido)."
      :guardando="modalRegla.guardando"
      @guardar="guardarRegla"
    >
      <FormField label="Criterio" required>
        <select v-model="fr.criterio" class="cr-input">
          <option v-for="cr in CRITERIOS" :key="cr.value" :value="cr.value">{{ cr.label }}</option>
        </select>
      </FormField>
      <FormField label="Ventana (meses)" required><input v-model.number="fr.ventana_meses" type="number" min="1" max="120" class="cr-input" /></FormField>
      <FormField v-if="fr.criterio !== 'frecuencia'" label="Umbral de monto ($)"><input v-model="fr.umbral_monto" type="number" min="0" step="0.01" class="cr-input" /></FormField>
      <FormField v-if="fr.criterio !== 'monto_acumulado'" label="Umbral de frecuencia"><input v-model="fr.umbral_frecuencia" type="number" min="0" class="cr-input" /></FormField>
      <p v-if="modalRegla.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modalRegla.error }}</p>
    </FormModal>
  </div>
</template>
