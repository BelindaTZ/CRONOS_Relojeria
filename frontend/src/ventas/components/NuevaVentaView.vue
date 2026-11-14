<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarClientes, ClienteFormModal } from '@/clientes'
import { listarRelojes, buscarDisponibilidadGlobal, listarCalibres } from '@/inventario'
import { listarMarcasReloj } from '@/configuracion'
import { listarSucursales } from '@/sucursales'
import { TransferenciaFormModal, costoReferencialTraslado } from '@/traslados'
import { crearVenta } from '@/ventas/services/ventasApi'

const router = useRouter()
const route = useRoute()
const session = useSessionStore()

// Llegada desde "Atender cita" (007): cliente y cita ya vienen resueltos.
const citaId = ref(route.query.cita_id ? Number(route.query.cita_id) : null)

// La venta se registra en la sucursal del vendedor (no es un campo libre): si tiene
// una sola sucursal asignada, se usa automáticamente; si tiene varias (o ninguna,
// como Gerencia General), elige entre las suyas / todas.
const misSucursales = computed(() => session.perfil?.sucursal_ids || [])
const necesitaElegirSucursal = computed(() => misSucursales.value.length !== 1)

const f = reactive({ cliente_id: null, sucursal_id: null, identificacion_fiscal: '', lineas: [] })
const clientes = ref([])
const sucursales = ref([])
const relojes = ref([])
const guardando = ref(false)
const error = ref('')

// Solo se venden relojes (Principio de la venta): las piezas/componentes de
// inventario nunca se venden sueltas a un cliente, solo las consume el
// técnico durante una reparación (servicio_tecnico).
// Los filtros son opcionales (ninguno se graba en la venta) pero deben elegirse
// del catálogo real — no texto libre — igual que al fichar un reloj en
// Inventario (Principio XI: "escribir para filtrar, no adivinar un valor").
const CRISTALES = ['zafiro', 'mineral', 'acrilico', 'otro']
const filtros = reactive({ marca: '', calibre: '', tipo_cristal: '', presupuesto: '' })
const marcasCatalogo = ref([])
const calibresCatalogo = ref([])

const opcionesSucursal = computed(() =>
  session.esGerencia || !misSucursales.value.length
    ? sucursales.value
    : sucursales.value.filter((s) => misSucursales.value.includes(s.id)),
)
const nombreMiSucursal = computed(() => sucursales.value.find((s) => s.id === misSucursales.value[0])?.nombre)

async function cargarRelojes() {
  const items = await listarRelojes({
    disponibilidad: 'disponible',
    marca: filtros.marca.trim() || undefined,
    calibre: filtros.calibre.trim() || undefined,
    tipo_cristal: filtros.tipo_cristal.trim() || undefined,
    page: 1,
    size: 100,
  })
    .then((r) => r.items)
    .catch(() => [])
  // El precio lo fija el catálogo, nunca el vendedor (no se ofrece una unidad
  // sin precio para que alguien se lo "invente" al vender — bug 2026-09-11).
  const presupuesto = Number(filtros.presupuesto) || null
  relojes.value = items
    .filter((x) => x.precio_venta != null && (presupuesto == null || Number(x.precio_venta) <= presupuesto))
    .map((x) => ({ ...x, _label: `${x.marca} ${x.referencia} · ${x.numero_serie}` }))
}
let tFiltro
function onFiltro() {
  clearTimeout(tFiltro)
  tFiltro = setTimeout(cargarRelojes, 250)
}

onMounted(async () => {
  ;[clientes.value, sucursales.value, marcasCatalogo.value, calibresCatalogo.value] = await Promise.all([
    listarClientes({ page: 1, size: 100 }).then((r) => r.items.map((c) => ({ ...c, _label: `${c.nombre} · ${c.numero_afiliado}` }))).catch(() => []),
    listarSucursales().then((r) => r.items).catch(() => []),
    listarMarcasReloj(true).catch(() => []),
    listarCalibres().catch(() => []),
    cargarRelojes(),
  ])
  if (!necesitaElegirSucursal.value) f.sucursal_id = misSucursales.value[0]
  else if (opcionesSucursal.value.length === 1) f.sucursal_id = opcionesSucursal.value[0].id
  if (route.query.cliente_id) f.cliente_id = Number(route.query.cliente_id)
})

// --- búsqueda global (otras sucursales) + traslado desde venta ---
const busquedaGlobalAbierta = ref(false)
const qGlobal = ref('')
const buscandoGlobal = ref(false)
const resultadosGlobales = ref([])
const costoTraslado = ref(null)

async function abrirBusquedaGlobal() {
  busquedaGlobalAbierta.value = true
  if (costoTraslado.value === null) {
    costoTraslado.value = await costoReferencialTraslado().then((r) => r.costo_traslado_venta).catch(() => null)
  }
  buscarGlobal()
}
async function buscarGlobal() {
  buscandoGlobal.value = true
  try {
    resultadosGlobales.value = await buscarDisponibilidadGlobal({
      q: qGlobal.value.trim() || undefined,
      marca: filtros.marca.trim() || undefined,
      calibre: filtros.calibre.trim() || undefined,
      tipo_cristal: filtros.tipo_cristal.trim() || undefined,
    }).catch(() => [])
    // El vendedor ya ve su propia sucursal en la búsqueda normal de arriba.
    if (f.sucursal_id) resultadosGlobales.value = resultadosGlobales.value.filter((r) => r.sucursal_id !== f.sucursal_id)
  } finally {
    buscandoGlobal.value = false
  }
}
let tGlobal
function onBuscarGlobal() {
  clearTimeout(tGlobal)
  tGlobal = setTimeout(buscarGlobal, 250)
}

const modalCliente = ref(false)
function onClienteCreado(c) {
  if (!c) return
  clientes.value.push({ ...c, _label: `${c.nombre} · ${c.numero_afiliado}` })
  f.cliente_id = c.id
}

const trasladoModal = reactive({ abierto: false, prefill: null })
function iniciarTraslado(r) {
  if (!f.sucursal_id) {
    error.value = 'Elige primero la sucursal de la venta: el traslado llega ahí.'
    return
  }
  trasladoModal.prefill = {
    sucursal_origen_id: r.sucursal_id,
    sucursal_destino_id: f.sucursal_id,
    reloj: { id: r.id, etiqueta: `${r.marca} ${r.referencia}`, detalle: r.numero_serie },
    motivo: `Traslado solicitado por venta — cliente pidió ${r.marca} ${r.referencia}`,
  }
  trasladoModal.abierto = true
}
function dinero2(n) {
  return Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
}

const addReloj = () => f.lineas.push({ reloj_id: null, precio_lista: null })
const quitar = (i) => f.lineas.splice(i, 1)
function agregarDesdeResultado(r) {
  if (f.lineas.some((l) => l.reloj_id === r.id)) return
  f.lineas.push({ reloj_id: r.id, precio_lista: null })
}

const totalEstimado = computed(() =>
  f.lineas.reduce((s, l) => {
    if (l.precio_lista != null) return s + Number(l.precio_lista)
    return s + Number(relojes.value.find((r) => r.id === l.reloj_id)?.precio_venta || 0)
  }, 0),
)

async function guardar() {
  error.value = ''
  if (!f.sucursal_id) return (error.value = 'Selecciona la sucursal.')
  if (!f.lineas.length) return (error.value = 'Agrega al menos un reloj.')
  if (f.lineas.some((l) => !l.reloj_id)) return (error.value = 'Completa cada línea.')
  guardando.value = true
  try {
    const v = await crearVenta({
      cliente_id: f.cliente_id || null,
      sucursal_id: f.sucursal_id,
      cita_id: citaId.value || null,
      identificacion_fiscal: f.identificacion_fiscal.trim() || null,
      lineas: f.lineas.map((l) => ({
        item_tipo: 'reloj',
        reloj_id: l.reloj_id,
        cantidad: 1,
        precio_lista: l.precio_lista != null ? Number(l.precio_lista) : null,
      })),
    })
    toast.success(`Venta ${v.numero} creada en borrador`)
    router.push({ name: 'venta-ficha', params: { id: v.id } })
  } catch (e) {
    error.value = e.status === 422 ? e.message : e.message
  } finally {
    guardando.value = false
  }
}
const dinero = (n) => Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Ventas"
      titulo="Nueva venta"
      sub="Arma el borrador con el cliente y los relojes. El descuento, los pagos y la confirmación se resuelven juntos en «Finalizar venta», dentro de la ficha."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'ventas' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Ventas</RouterLink>
      </template>
    </PageHeader>

    <p v-if="citaId" class="mb-4 flex items-center gap-2 rounded-lg border border-hairline bg-surface-sunk px-3 py-2 text-xs text-ink-2">
      <CrIcon name="check" :size="14" /> Venta iniciada desde la cita atendida — quedará vinculada a ella al confirmarse.
    </p>

    <div class="grid gap-5 lg:grid-cols-3">
      <section class="cr-card p-6 lg:col-span-1">
        <h2 class="serif text-lg text-ink">Datos</h2>
        <FormField label="Cliente" wide helper="Obligatorio para vender un reloj o un monto alto.">
          <div class="flex gap-2">
            <div class="min-w-0 flex-1">
              <ComboBox v-model="f.cliente_id" :opciones="clientes" opcion-label="_label" opcion-value="id" placeholder="Consumidor final" />
            </div>
            <button
              type="button" class="cr-btn cr-btn-ghost shrink-0 px-2.5"
              title="Registrar cliente nuevo" aria-label="Registrar cliente nuevo"
              @click="modalCliente = true"
            >
              <CrIcon name="plus" :size="16" />
            </button>
          </div>
        </FormField>
        <FormField v-if="necesitaElegirSucursal" label="Sucursal" wide required helper="Elige entre las sucursales asignadas a tu usuario.">
          <select v-model="f.sucursal_id" class="cr-input">
            <option :value="null">Elige…</option>
            <option v-for="s in opcionesSucursal" :key="s.id" :value="s.id">{{ s.nombre }}</option>
          </select>
        </FormField>
        <FormField v-else label="Sucursal" wide helper="Se registra en tu sucursal asignada.">
          <p class="cr-input flex items-center bg-surface-sunk text-ink-2">{{ nombreMiSucursal || '—' }}</p>
        </FormField>
        <FormField label="Identificación fiscal" wide helper="Opcional; para el comprobante (compatible con SRI).">
          <input v-model="f.identificacion_fiscal" class="cr-input" />
        </FormField>
        <div class="mt-4 border-t border-hairline-soft pt-3">
          <p class="cr-label">Total estimado</p>
          <p class="serif text-2xl text-gold-strong tabular-nums">{{ dinero(totalEstimado) }}</p>
        </div>
      </section>

      <section class="cr-card p-6 lg:col-span-2">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="serif text-lg text-ink">Líneas</h2>
          <button type="button" class="cr-btn cr-btn-ghost text-xs" @click="addReloj"><CrIcon name="watch" :size="13" /> Reloj</button>
        </div>

        <div class="mb-3 grid gap-2 rounded-lg bg-surface-sunk p-3 sm:grid-cols-2 lg:grid-cols-4">
          <FormField label="Marca">
            <ComboBox
              :model-value="filtros.marca || null"
              :opciones="marcasCatalogo" opcion-label="nombre" opcion-value="nombre"
              placeholder="Todas" @update:model-value="(v) => { filtros.marca = v || ''; onFiltro() }"
            />
          </FormField>
          <FormField label="Calibre">
            <ComboBox
              :model-value="filtros.calibre || null"
              :opciones="calibresCatalogo" opcion-label="codigo" opcion-value="codigo"
              placeholder="Todos" @update:model-value="(v) => { filtros.calibre = v || ''; onFiltro() }"
            />
          </FormField>
          <FormField label="Tipo de cristal">
            <select v-model="filtros.tipo_cristal" class="cr-input" @change="onFiltro">
              <option value="">Todos</option>
              <option v-for="c in CRISTALES" :key="c" :value="c">{{ c }}</option>
            </select>
          </FormField>
          <FormField label="Presupuesto máx." helper="Precio de catálogo; no editable por el vendedor.">
            <input
              v-model="filtros.presupuesto" type="number" min="0" step="0.01" class="cr-input tabular-nums"
              placeholder="Sin límite" @input="onFiltro"
            />
          </FormField>
        </div>
        <p class="mb-2 text-xs text-ink-3">
          {{ relojes.length }} reloj{{ relojes.length === 1 ? '' : 'es' }} disponible{{ relojes.length === 1 ? '' : 's' }}<span v-if="filtros.marca || filtros.calibre || filtros.tipo_cristal || filtros.presupuesto"> con ese filtro</span>.
        </p>
        <div v-if="relojes.length" class="mb-4 grid max-h-[26rem] gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
          <div v-for="r in relojes" :key="r.id" class="flex gap-3 rounded-lg border border-hairline p-2.5">
            <div class="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-md bg-surface-sunk">
              <img v-if="r.foto_url" :src="r.foto_url" :alt="`${r.marca} ${r.referencia}`" class="h-full w-full object-cover" />
              <CrIcon v-else name="watch" :size="22" class="text-ink-3" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-ink">{{ r.marca }} {{ r.referencia }}</p>
              <p class="truncate text-xs text-ink-3">{{ r.numero_serie }}<span v-if="r.calibre_codigo"> · Cal. {{ r.calibre_codigo }}</span></p>
              <p v-if="r.precio_venta != null" class="text-sm text-gold-strong tabular-nums">{{ dinero2(r.precio_venta) }}</p>
              <div class="mt-1 flex items-center gap-3">
                <RouterLink :to="{ name: 'reloj-ficha', params: { serie: r.numero_serie } }" target="_blank" class="text-xs text-ink-3 underline hover:text-ink">Ver ficha</RouterLink>
                <button
                  type="button" class="cr-btn cr-btn-ghost ml-auto text-xs"
                  :disabled="f.lineas.some((l) => l.reloj_id === r.id)"
                  @click="agregarDesdeResultado(r)"
                >
                  {{ f.lineas.some((l) => l.reloj_id === r.id) ? 'Agregada ✓' : 'Agregar' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <p v-if="!f.lineas.length" class="rounded-md bg-surface-sunk px-3 py-2 text-xs text-ink-3">Agrega un reloj (por N.º de serie, marca, referencia o calibre) o elige "Agregar" en la lista de arriba.</p>
        <div v-for="(l, i) in f.lineas" :key="i" class="mb-2 grid gap-2 rounded-lg border border-hairline p-3 sm:grid-cols-2">
          <FormField label="Unidad" required>
            <ComboBox v-model="l.reloj_id" :opciones="relojes" opcion-label="_label" opcion-value="id" placeholder="Buscar por serie…" />
          </FormField>
          <FormField label="Precio" helper="Fijado por la ficha del reloj; el vendedor no puede modificarlo.">
            <p class="cr-input flex items-center bg-surface-sunk text-ink-2 tabular-nums">
              {{ relojes.find((r) => r.id === l.reloj_id)?.precio_venta != null ? dinero2(relojes.find((r) => r.id === l.reloj_id).precio_venta) : '—' }}
            </p>
          </FormField>
          <button type="button" class="text-xs text-bad sm:col-span-2" @click="quitar(i)">Quitar línea</button>
        </div>

        <div class="mt-3 border-t border-hairline-soft pt-3">
          <button type="button" class="cr-btn cr-btn-ghost text-xs" @click="abrirBusquedaGlobal">
            <CrIcon name="search" :size="13" /> ¿No está en tu sucursal? Buscar en toda la red
          </button>

          <div v-if="busquedaGlobalAbierta" class="mt-3 rounded-lg border border-hairline p-3">
            <input v-model="qGlobal" class="cr-input mb-2" placeholder="Serie, marca o referencia…" @input="onBuscarGlobal" />
            <p v-if="costoTraslado" class="mb-2 rounded-md bg-surface-sunk px-3 py-2 text-xs text-ink-3">
              Si el cliente pide expresamente traer una unidad de otra sucursal, se sugiere cobrar un cargo de traslado de
              <strong class="text-ink-2 tabular-nums">{{ dinero2(costoTraslado) }}</strong> (configurable en Sistema → Parámetros ·
              <code class="text-[11px]">costo_traslado_venta</code>). El reabastecimiento rutinario entre sucursales sigue siendo gratuito.
            </p>
            <p v-if="buscandoGlobal" class="text-xs text-ink-3">Buscando…</p>
            <ul v-else class="max-h-56 divide-y divide-hairline-soft overflow-y-auto">
              <li v-for="r in resultadosGlobales" :key="r.id" class="flex items-center justify-between gap-2 py-2 text-sm">
                <span>
                  <strong class="text-ink">{{ r.marca }} {{ r.referencia }}</strong>
                  <span class="text-ink-3"> · {{ r.numero_serie }} · {{ r.sucursal_nombre }}</span>
                </span>
                <button type="button" class="cr-btn cr-btn-ghost text-xs shrink-0" @click="iniciarTraslado(r)">
                  <CrIcon name="truck" :size="13" /> Iniciar traslado
                </button>
              </li>
              <li v-if="!resultadosGlobales.length" class="py-2 text-xs text-ink-3">Sin coincidencias en otras sucursales.</li>
            </ul>
          </div>
        </div>

        <p v-if="error" class="mt-2 text-sm text-bad" role="alert">{{ error }}</p>
        <div class="mt-4 flex justify-end">
          <button class="cr-btn cr-btn-primary" :disabled="guardando" @click="guardar">
            {{ guardando ? 'Creando…' : 'Crear borrador' }}
          </button>
        </div>
      </section>
    </div>

    <TransferenciaFormModal v-model="trasladoModal.abierto" :prefill="trasladoModal.prefill" />
    <ClienteFormModal v-model="modalCliente" @guardado="onClienteCreado" />
  </div>
</template>
