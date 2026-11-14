<script setup>
/**
 * Editor de líneas de pedido compartido por la Orden de compra y la Compra
 * programada (Principio X — no reimplementar). Cada línea es un reloj
 * (marca / referencia / calibre / año / N.º serie / observaciones) o una pieza
 * (del catálogo, o "pieza nueva" con código / descripción / tipo / marca
 * compatible / unidad de medida). El precio siempre es opcional.
 *
 *   <LineasPedidoEditor ref="editor" :inicial="lineasPrellenadas" :con-serie="false" />
 *   // luego:  const lineas = editor.value.construirLineas()   // lanza Error si algo falta
 */
import { onMounted, ref, watch } from 'vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { crearMarcaReloj, listarMarcasReloj } from '@/configuracion'
import { crearCalibre, listarCalibres } from '@/inventario'
import { listarPiezas } from '@/piezas'
import { ultimoPrecio } from '@/proveedores/services/proveedoresApi'

const props = defineProps({
  inicial: { type: Array, default: null }, // líneas para prellenar (formato API o {marca_nombre})
  conSerie: { type: Boolean, default: true }, // N.º de serie por línea (no aplica a compra programada)
  conUltimoPrecio: { type: Boolean, default: true },
})

const UNIDADES = ['unidad', 'ml', 'g', 'mm', 'par', 'juego', 'metro', 'litro']

const marcas = ref([])
const calibres = ref([])
const piezasCat = ref([])

function lineaNueva(tipo = 'reloj') {
  return {
    item_tipo: tipo,
    marca_id: null,
    item_ref: '',
    calibre_id: null,
    anio: null,
    numero_serie: '',
    _nueva: false,
    pieza_id: null,
    pieza_tipo: 'original',
    unidad_medida: 'unidad',
    marca_compatible: '',
    descripcion: '', // reloj: observaciones · pieza nueva: nombre de la pieza
    observaciones: '', // nota libre del pedido
    cantidad: 1,
    costo_unitario: null,
    es_perecedero: false,
    _ultimo: null,
  }
}

const lineas = ref([lineaNueva()])

function sembrar() {
  if (props.inicial?.length) {
    lineas.value = props.inicial.map((l) => {
      const base = { ...lineaNueva(l.item_tipo || 'reloj'), ...l }
      const nombre = l.marca_nombre || l.marca
      if (nombre) base.marca_id = marcas.value.find((m) => m.nombre === nombre)?.id ?? null
      if (l.calibre_codigo) base.calibre_id = calibres.value.find((c) => c.codigo === l.calibre_codigo)?.id ?? null
      if (l.pieza_id) base._nueva = false
      return base
    })
  } else {
    lineas.value = [lineaNueva()]
  }
}
watch(() => props.inicial, sembrar, { deep: true })

async function nuevaMarca(t) { try { const m = await crearMarcaReloj({ nombre: t }); marcas.value.push(m); return m } catch { return null } }
async function nuevoCalibre(t) { try { const c = await crearCalibre({ codigo: t }); calibres.value.push(c); return c } catch { return null } }

onMounted(async () => {
  const [mk, cal, pz] = await Promise.all([
    listarMarcasReloj(true).catch(() => []),
    listarCalibres().catch(() => []),
    listarPiezas({ page: 1, size: 100 }).catch(() => ({ items: [] })),
  ])
  marcas.value = mk
  calibres.value = cal
  piezasCat.value = pz.items
  sembrar()
})

function agregar(tipo) { lineas.value.push(lineaNueva(tipo)) }
function quitar(i) { lineas.value.splice(i, 1) }

async function consultarUltimo(l) {
  if (!props.conUltimoPrecio) return
  l._ultimo = null
  try {
    let params
    if (l.item_tipo === 'reloj') {
      const marca = marcas.value.find((m) => m.id === l.marca_id)?.nombre
      if (!marca || !l.item_ref.trim()) return
      params = { item_tipo: 'reloj', marca, referencia: l.item_ref.trim() }
    } else if (l.pieza_id) {
      params = { item_tipo: 'pieza', pieza_id: l.pieza_id }
    } else if (l.item_ref.trim()) {
      params = { item_tipo: 'pieza', referencia: l.item_ref.trim() }
    } else return
    const r = await ultimoPrecio(params)
    if (r.costo != null) l._ultimo = r
  } catch {
    /* sin dato */
  }
}
function elegirPiezaCatalogo(l) {
  const p = piezasCat.value.find((x) => x.id === l.pieza_id)
  if (p) {
    l.item_ref = p.codigo
    l.descripcion = ''
    l.es_perecedero = p.perecedera
  }
  consultarUltimo(l)
}

/** Valida y devuelve las líneas en el formato del API (`LineaIn`). Lanza `Error`. */
function construirLineas() {
  if (!lineas.value.length) throw new Error('Agrega al menos una línea.')
  return lineas.value.map((l) => {
    const base = {
      item_tipo: l.item_tipo,
      cantidad: Number(l.cantidad),
      costo_unitario: l.costo_unitario === null || l.costo_unitario === '' ? null : Number(l.costo_unitario),
      observaciones: (l.observaciones || '').trim() || null,
    }
    if (l.item_tipo === 'reloj') {
      if (!l.marca_id) throw new Error('Cada reloj necesita una marca.')
      if (!l.item_ref.trim()) throw new Error('Indica la referencia / modelo del reloj.')
      if (props.conSerie && l.numero_serie && Number(l.cantidad) > 1) {
        throw new Error('Solo se indica N.º de serie si la cantidad es 1.')
      }
      return {
        ...base,
        item_ref: l.item_ref.trim(),
        descripcion: (l.descripcion || '').trim() || null,
        marca: marcas.value.find((m) => m.id === l.marca_id)?.nombre ?? null,
        calibre_codigo: calibres.value.find((c) => c.id === l.calibre_id)?.codigo ?? null,
        anio: l.anio ? Number(l.anio) : null,
        numero_serie: props.conSerie ? (l.numero_serie || '').trim() || null : null,
      }
    }
    if (l._nueva) {
      if (!l.item_ref.trim() || !l.descripcion.trim()) {
        throw new Error('La pieza nueva necesita código y descripción.')
      }
      return {
        ...base,
        item_ref: l.item_ref.trim(),
        descripcion: l.descripcion.trim() || null,
        pieza_tipo: l.pieza_tipo,
        unidad_medida: l.unidad_medida,
        marca_compatible: (l.marca_compatible || '').trim() || null,
        es_perecedero: l.es_perecedero,
      }
    }
    if (!l.pieza_id) throw new Error('Elige una pieza del catálogo o marca «pieza nueva».')
    const p = piezasCat.value.find((x) => x.id === l.pieza_id)
    return { ...base, item_ref: p?.codigo ?? l.item_ref, pieza_id: l.pieza_id }
  })
}

function hayContenido() {
  return lineas.value.some((l) => l.item_ref || l.pieza_id || l.marca_id)
}

defineExpose({ construirLineas, agregar, hayContenido, lineas })
</script>

<template>
  <div class="sm:col-span-2">
    <p class="cr-label mb-2">Líneas del pedido</p>
    <div class="space-y-3">
      <div v-for="(l, i) in lineas" :key="i" class="rounded-xl border border-hairline bg-surface-sunk/40 p-3">
        <div class="mb-2 flex items-center justify-between">
          <span class="text-xs font-semibold uppercase tracking-wide text-ink-3">
            {{ l.item_tipo === 'reloj' ? 'Reloj' : 'Pieza / consumible' }}
          </span>
          <button v-if="lineas.length > 1" type="button" class="text-xs text-bad hover:underline" @click="quitar(i)">Quitar</button>
        </div>

        <!-- RELOJ -->
        <template v-if="l.item_tipo === 'reloj'">
          <div class="grid gap-2 sm:grid-cols-2">
            <ComboBox v-model="l.marca_id" :opciones="marcas" opcion-label="nombre" opcion-value="id" placeholder="Marca…" :crear="nuevaMarca" crear-label="Crear marca" @update:model-value="consultarUltimo(l)" />
            <input v-model="l.item_ref" class="cr-input" placeholder="Referencia / modelo (ej. 126334)" @blur="consultarUltimo(l)" />
            <ComboBox v-model="l.calibre_id" :opciones="calibres" opcion-label="codigo" opcion-value="id" placeholder="Calibre (opcional)…" :crear="nuevoCalibre" crear-label="Crear calibre" />
            <input v-model="l.anio" type="number" min="1900" max="2100" class="cr-input" placeholder="Año (opcional)" />
          </div>
          <input v-if="conSerie && l.cantidad == 1" v-model="l.numero_serie" class="cr-input mt-2" placeholder="N.º de serie (opcional, si ya lo conoces)" />
          <input v-model="l.descripcion" class="cr-input mt-2" placeholder="Observaciones (Full Set, caja específica, para cliente X…)" />
        </template>

        <!-- PIEZA -->
        <template v-else>
          <label class="mb-2 flex items-center gap-2 text-xs text-ink-2">
            <input v-model="l._nueva" type="checkbox" /> Es una pieza nueva (no está en el catálogo)
          </label>
          <ComboBox
            v-if="!l._nueva"
            v-model="l.pieza_id" :opciones="piezasCat" opcion-label="codigo" opcion-value="id"
            placeholder="Elegir pieza del catálogo…" @update:model-value="elegirPiezaCatalogo(l)"
          >
            <template #secundario="{ opcion }"><span class="text-ink-3"> · {{ opcion.descripcion }}</span></template>
          </ComboBox>
          <div v-else class="grid gap-2 sm:grid-cols-2">
            <input v-model="l.item_ref" class="cr-input" placeholder="Código de la pieza" />
            <input v-model="l.descripcion" class="cr-input" placeholder="Descripción de la pieza" />
            <select v-model="l.pieza_tipo" class="cr-input">
              <option value="original">Original</option>
              <option value="no_original_equivalente">No original (calidad equivalente)</option>
            </select>
            <input v-model="l.marca_compatible" class="cr-input" placeholder="Marca(s) compatible(s) — Rolex, Omega…" />
            <select v-model="l.unidad_medida" class="cr-input">
              <option v-for="u in UNIDADES" :key="u" :value="u">{{ u }}</option>
            </select>
            <label class="flex items-center gap-1.5 text-xs text-ink-3">
              <input v-model="l.es_perecedero" type="checkbox" /> Perecedero
            </label>
          </div>
          <input v-model="l.observaciones" class="cr-input mt-2" placeholder="Observaciones del pedido (urgente, para cliente X…)" />
        </template>

        <div class="mt-2 grid gap-2 sm:grid-cols-3">
          <label class="space-y-1">
            <span class="cr-label">Cantidad{{ conSerie ? '' : ' por ciclo' }}</span>
            <input v-model.number="l.cantidad" type="number" min="1" class="cr-input" />
          </label>
          <label class="space-y-1 sm:col-span-2">
            <span class="cr-label">Precio unitario de compra <span class="font-normal normal-case text-ink-3">— opcional</span></span>
            <input v-model="l.costo_unitario" type="number" min="0" step="0.01" class="cr-input" placeholder="Lo confirma el proveedor" />
          </label>
        </div>
        <p v-if="l._ultimo" class="mt-1 text-xs text-ink-3">
          Último precio de compra: <strong class="text-ink-2">$ {{ Number(l._ultimo.costo).toLocaleString() }}</strong>
          <span v-if="l._ultimo.fecha"> ({{ l._ultimo.fecha }}{{ l._ultimo.fuente === 'orden' ? ', estimado' : '' }})</span>
          <button type="button" class="ml-1 text-gold-strong underline" @click="l.costo_unitario = l._ultimo.costo">usar</button>
        </p>
      </div>
    </div>
    <div class="mt-2 flex gap-2">
      <button type="button" class="cr-btn cr-btn-ghost text-xs" @click="agregar('reloj')"><CrIcon name="plus" :size="14" /> Añadir reloj</button>
      <button type="button" class="cr-btn cr-btn-ghost text-xs" @click="agregar('pieza')"><CrIcon name="plus" :size="14" /> Añadir pieza</button>
    </div>
    <p v-if="conSerie" class="mt-2 text-sm text-ink-2">El N.º de serie de cada unidad se captura al recibir la orden.</p>
  </div>
</template>
