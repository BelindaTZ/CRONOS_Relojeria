<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import {
  crearColor,
  crearMarcaReloj,
  crearMaterial,
  listarColores,
  listarMarcasReloj,
  listarMateriales,
} from '@/configuracion'
import {
  agregarDocumentoReloj,
  agregarFoto,
  corregirReloj,
  getReloj,
  historialSerie,
  listarCalibres,
} from '@/inventario/services/inventarioApi'

const route = useRoute()
const router = useRouter()
const serie = computed(() => route.params.serie)

const r = ref(null)
const historial = ref([])
const sucursales = ref([])
const calibres = ref([])
const marcas = ref([])
const materiales = ref([])
const colores = ref([])
const ampliada = ref('')

async function nuevaMarca(t) {
  try { const m = await crearMarcaReloj({ nombre: t }); marcas.value.push(m); return m } catch (e) { toast.error(e.message); return null }
}
async function nuevoMaterial(t) {
  try { const m = await crearMaterial(t); materiales.value.push(m); return m } catch (e) { toast.error(e.message); return null }
}
async function nuevoColor(t) {
  try { const c = await crearColor({ nombre: t }); colores.value.push(c); return c } catch (e) { toast.error(e.message); return null }
}

const EVENTO_ICONO = {
  ingreso: 'inbox',
  venta: 'tag',
  servicio: 'refresh-cw',
  transferencia: 'truck',
  baja: 'ban',
  reingreso: 'inbox',
  correccion: 'edit',
}
const DISP_TONO = {
  disponible: 'good', reservado: 'warn', en_transito: 'warn',
  en_servicio: 'info', vendido: 'neutral', dado_de_baja: 'bad',
}

const sucursalNombre = (id) => sucursales.value.find((s) => s.id === id)?.nombre ?? (id ? `#${id}` : '—')
const calibreCodigo = computed(() => r.value?.calibre_codigo || '—')

async function cargar() {
  r.value = await getReloj(serie.value)
  historial.value = await historialSerie(serie.value).catch(() => [])
}
onMounted(async () => {
  const [s, c, m, mat, col] = await Promise.all([
    listarSucursales().catch(() => ({ items: [] })),
    listarCalibres().catch(() => []),
    listarMarcasReloj(true).catch(() => []),
    listarMateriales(true).catch(() => []),
    listarColores(true).catch(() => []),
  ])
  sucursales.value = s.items
  calibres.value = c
  marcas.value = m
  materiales.value = mat
  colores.value = col
  cargar()
})

// --- fotos ---
async function subirFoto(ev) {
  const file = ev.target.files[0]
  if (!file) return
  try {
    await agregarFoto(r.value.id, file)
    toast.success('Foto añadida')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
  ev.target.value = ''
}

// --- documentos ---
async function adjuntar(ev) {
  const file = ev.target.files[0]
  if (!file) return
  const ok = await confirm({
    title: 'Adjuntar documento',
    message: `¿Adjuntar «${file.name}» como papeles del Full Set?`,
    confirmLabel: 'Adjuntar',
  })
  if (ok) {
    try {
      await agregarDocumentoReloj(r.value.id, 'papeles_full_set', file)
      toast.success('Documento adjuntado')
      cargar()
    } catch (e) {
      toast.error(e.message)
    }
  }
  ev.target.value = ''
}

// --- corregir ---
const modal = reactive({ abierto: false, guardando: false, error: '' })
const form = reactive({})
function abrirCorreccion() {
  Object.assign(form, {
    motivo: '',
    numero_serie: r.value.numero_serie,
    marca_id: r.value.marca_id,
    referencia: r.value.referencia,
    calibre_id: r.value.calibre_id,
    material_caja_id: r.value.material_caja_id,
    material_brazalete_id: r.value.material_brazalete_id,
    color_esfera_id: r.value.color_esfera_id,
    precio_venta: r.value.precio_venta,
    sucursal_actual_id: r.value.sucursal_actual_id,
  })
  modal.error = ''
  modal.abierto = true
}
async function guardarCorreccion() {
  modal.error = ''
  if (!form.motivo || form.motivo.trim().length < 5) return (modal.error = 'Explica el motivo de la corrección (mín. 5 caracteres).')
  modal.guardando = true
  try {
    const cambios = { motivo: form.motivo.trim() }
    for (const k of ['numero_serie', 'marca_id', 'referencia', 'calibre_id', 'material_caja_id',
                     'material_brazalete_id', 'color_esfera_id', 'precio_venta', 'sucursal_actual_id']) {
      if (form[k] !== r.value[k]) cambios[k] = form[k]
    }
    const nueva = form.numero_serie
    await corregirReloj(r.value.id, cambios)
    toast.success('Ficha corregida · queda registrado en el historial')
    modal.abierto = false
    if (nueva !== serie.value) router.replace({ name: 'reloj-ficha', params: { serie: nueva } })
    else cargar()
  } catch (e) {
    modal.error = e.status === 403 ? 'Corregir la ficha requiere rol elevado (Gerencia / Gerente de Sucursal).' : e.message
  } finally {
    modal.guardando = false
  }
}

function fmtMoneda(v) {
  return v != null ? `$ ${Number(v).toLocaleString()}` : '—'
}
</script>

<template>
  <div v-if="r">
    <PageHeader
      eyebrow="Inventario · Unidad"
      :titulo="`${r.marca} ${r.referencia}`"
      :sub="`N.º de serie ${r.numero_serie}`"
    >
      <template #acciones>
        <RouterLink :to="{ name: 'inventario' }" class="cr-btn cr-btn-ghost">
          <CrIcon name="arrow-left" :size="15" /> Inventario
        </RouterLink>
        <button class="cr-btn cr-btn-ghost" @click="abrirCorreccion">Corregir ficha</button>
      </template>
    </PageHeader>

    <div class="mb-6 flex flex-wrap items-center gap-3">
      <Pill :tone="DISP_TONO[r.disponibilidad] || 'neutral'" :label="r.disponibilidad.replace(/_/g, ' ')" />
      <Pill v-if="r.full_set" tone="info" label="Full Set" />
    </div>

    <div class="grid gap-5 lg:grid-cols-3">
      <!-- galería -->
      <section class="cr-card p-6 lg:col-span-1">
        <div class="flex items-center justify-between">
          <h2 class="serif text-lg text-ink">Galería</h2>
          <label class="cr-btn cr-btn-ghost cursor-pointer text-xs">
            <CrIcon name="camera" :size="14" /> Añadir
            <input type="file" accept="image/*" class="hidden" @change="subirFoto" />
          </label>
        </div>
        <div v-if="r.fotos.length" class="mt-4 grid grid-cols-3 gap-2">
          <button
            v-for="ft in r.fotos"
            :key="ft.id"
            type="button"
            class="aspect-square overflow-hidden rounded-lg border border-hairline"
            @click="ampliada = ft.url"
          >
            <img :src="ft.url" alt="Foto del reloj" loading="lazy" class="h-full w-full object-cover" />
          </button>
        </div>
        <div v-else class="mt-4 grid place-items-center rounded-xl border border-dashed border-hairline py-10 text-center text-sm text-ink-3">
          <CrIcon name="image" :size="30" class="mb-2" />
          Sin fotos todavía. Añade la primera.
        </div>
      </section>

      <!-- ficha técnica -->
      <section class="cr-card p-6 lg:col-span-2">
        <h2 class="serif text-lg text-ink">Ficha técnica</h2>
        <dl class="mt-4 grid gap-x-8 gap-y-2.5 text-sm sm:grid-cols-2">
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Calibre</dt><dd>{{ calibreCodigo }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Año</dt><dd>{{ r.anio_fabricacion ?? '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Material de caja</dt><dd>{{ r.material_caja || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Brazalete</dt><dd>{{ r.material_brazalete || '—' }}</dd></div>
          <div class="flex justify-between gap-4">
            <dt class="text-ink-3">Color de esfera</dt>
            <dd class="flex items-center gap-1.5">
              <span v-if="r.color_esfera_hex" class="h-3 w-3 rounded-full border border-hairline" :style="{ background: r.color_esfera_hex }"></span>
              {{ r.color_esfera || '—' }}
            </dd>
          </div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Cristal</dt><dd>{{ r.tipo_cristal || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Resistencia al agua</dt><dd>{{ r.resistencia_agua || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Estado</dt><dd class="capitalize">{{ r.estado_producto }}</dd></div>
        </dl>
        <p v-if="r.full_set_detalle" class="mt-3 border-t border-hairline-soft pt-3 text-sm text-ink-2">
          <span class="text-ink-3">Full Set:</span> {{ r.full_set_detalle }}
        </p>
      </section>

      <!-- comercial -->
      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Datos comerciales</h2>
        <dl class="mt-4 space-y-2.5 text-sm">
          <div class="flex justify-between gap-4">
            <dt class="text-ink-3">Costo de adquisición</dt>
            <dd v-if="r.costos_visibles" class="tabular-nums">{{ fmtMoneda(r.costo_adquisicion) }}</dd>
            <dd v-else class="flex items-center gap-1 text-ink-3"><CrIcon name="lock" :size="12" /> restringido</dd>
          </div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Precio de venta</dt><dd class="serif text-lg text-gold-strong tabular-nums">{{ fmtMoneda(r.precio_venta) }}</dd></div>
          <div v-if="r.costos_visibles" class="flex justify-between gap-4"><dt class="text-ink-3">Margen</dt><dd class="tabular-nums">{{ fmtMoneda(r.margen) }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Fecha de ingreso</dt><dd>{{ r.fecha_ingreso || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Proveedor</dt><dd>{{ r.proveedor_id ? `#${r.proveedor_id}` : '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Origen</dt><dd>{{ r.recepcion_linea_id ? `Recepción de compra (línea #${r.recepcion_linea_id})` : 'Alta manual' }}</dd></div>
        </dl>
      </section>

      <!-- ubicación -->
      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Ubicación y estado</h2>
        <dl class="mt-4 space-y-2.5 text-sm">
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Sucursal actual</dt><dd>{{ sucursalNombre(r.sucursal_actual_id) }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Disponibilidad</dt><dd class="capitalize">{{ r.disponibilidad.replace(/_/g, ' ') }}</dd></div>
        </dl>
        <p class="mt-3 border-t border-hairline-soft pt-3 text-xs text-ink-3">
          Las transferencias entre sucursales se registran en Multisucursal (feature 004).
        </p>
      </section>

      <!-- documentos -->
      <section class="cr-card p-6">
        <div class="flex items-center justify-between">
          <h2 class="serif text-lg text-ink">Documentos</h2>
          <label class="cr-btn cr-btn-ghost cursor-pointer text-xs">
            Adjuntar<input type="file" class="hidden" @change="adjuntar" />
          </label>
        </div>
        <ul class="mt-4 space-y-2 text-sm">
          <li v-for="d in r.documentos" :key="d.id" class="flex items-center gap-2">
            <CrIcon name="archive" :size="15" class="text-ink-3" />
            <a :href="d.url" target="_blank" rel="noopener" class="text-gold-strong hover:underline">{{ d.nombre }}</a>
            <span class="text-ink-3">· {{ d.tipo.replace(/_/g, ' ') }}</span>
          </li>
          <li v-if="!r.documentos.length" class="text-ink-3">Sin documentos (papeles del Full Set, factura de compra…).</li>
        </ul>
      </section>

      <!-- historial -->
      <section class="cr-card p-6 lg:col-span-3">
        <h2 class="serif text-lg text-ink">Historial de la unidad</h2>
        <p class="mt-1 text-xs text-ink-3">Inalterable — cada evento se registra y no se edita ni se borra.</p>
        <ol class="mt-5 space-y-4 border-l border-hairline pl-5">
          <li v-for="(e, i) in historial" :key="i" class="relative">
            <span class="absolute -left-[27px] grid h-5 w-5 place-items-center rounded-full border border-hairline bg-surface text-ink-3">
              <CrIcon :name="EVENTO_ICONO[e.tipo] || 'clock'" :size="12" />
            </span>
            <p class="text-sm font-medium capitalize text-ink">{{ e.tipo }}</p>
            <p class="text-xs text-ink-3">
              {{ new Date(e.fecha).toLocaleString() }}
              <template v-if="e.documento_tipo"> · {{ e.documento_tipo.replace(/_/g, ' ') }} <span v-if="e.documento_id">#{{ e.documento_id }}</span></template>
            </p>
            <p v-if="e.detalle && e.detalle.motivo" class="mt-1 text-xs text-ink-2">Motivo: {{ e.detalle.motivo }}</p>
          </li>
          <li v-if="!historial.length" class="text-sm text-ink-3">Sin eventos aún.</li>
        </ol>
      </section>
    </div>

    <!-- lightbox -->
    <div v-if="ampliada" class="fixed inset-0 z-50 flex items-center justify-center bg-primary-950/80 p-6" @click="ampliada = ''">
      <img :src="ampliada" alt="Foto ampliada" class="max-h-full max-w-3xl rounded-xl" />
    </div>

    <FormModal
      v-model="modal.abierto"
      titulo="Corregir ficha de la unidad"
      subtitulo="Solo un rol elevado. El cambio queda en el historial y en la auditoría."
      :guardando="modal.guardando"
      ancho="max-w-2xl"
      @guardar="guardarCorreccion"
    >
      <FormField label="Motivo de la corrección" required wide>
        <input v-model="form.motivo" class="cr-input" placeholder="p. ej. error de digitación en la recepción" required />
      </FormField>
      <FormField label="Número de serie"><input v-model="form.numero_serie" class="cr-input" /></FormField>
      <FormField label="Marca">
        <ComboBox v-model="form.marca_id" :opciones="marcas" opcion-label="nombre" opcion-value="id" placeholder="Marca…" :crear="nuevaMarca" crear-label="Crear marca" />
      </FormField>
      <FormField label="Referencia"><input v-model="form.referencia" class="cr-input" /></FormField>
      <FormField label="Calibre">
        <ComboBox v-model="form.calibre_id" :opciones="calibres" opcion-label="codigo" opcion-value="id" placeholder="Calibre…" />
      </FormField>
      <FormField label="Material de la caja">
        <ComboBox v-model="form.material_caja_id" :opciones="materiales" opcion-label="nombre" opcion-value="id" placeholder="Material…" :crear="nuevoMaterial" crear-label="Crear material" />
      </FormField>
      <FormField label="Material del brazalete">
        <ComboBox v-model="form.material_brazalete_id" :opciones="materiales" opcion-label="nombre" opcion-value="id" placeholder="Material…" :crear="nuevoMaterial" crear-label="Crear material" />
      </FormField>
      <FormField label="Color de esfera">
        <ComboBox v-model="form.color_esfera_id" :opciones="colores" opcion-label="nombre" opcion-value="id" placeholder="Color…" :crear="nuevoColor" crear-label="Crear color" />
      </FormField>
      <FormField label="Precio de venta"><input v-model="form.precio_venta" type="number" min="0" step="0.01" class="cr-input" /></FormField>
      <FormField label="Sucursal actual">
        <ComboBox v-model="form.sucursal_actual_id" :opciones="sucursales" opcion-label="nombre" opcion-value="id" placeholder="Sucursal…" />
      </FormField>
      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
