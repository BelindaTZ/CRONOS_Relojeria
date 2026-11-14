<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import { listarProveedores } from '@/proveedores'
import {
  crearColor,
  crearMarcaReloj,
  crearMaterial,
  listarColores,
  listarMarcasReloj,
  listarMateriales,
} from '@/configuracion'
import { crearCalibre, crearReloj, lineasPendientesRecepcion, listarCalibres } from '@/inventario/services/inventarioApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // opcional: precargar una línea de recepción concreta (flujo "recibir y fichar")
  recepcionLinea: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'creado'])

const CRISTALES = ['zafiro', 'mineral', 'acrilico', 'otro']

function vacio() {
  return {
    recepcion_linea_id: null,
    motivo_alta_manual: '',
    numero_serie: '',
    marca_id: null,
    referencia: '',
    calibre_id: null,
    anio_fabricacion: null,
    material_caja_id: null,
    material_brazalete_id: null,
    color_esfera_id: null,
    tipo_cristal: '',
    resistencia_agua: '',
    estado_producto: 'nuevo',
    costo_adquisicion: null,
    precio_venta: null,
    fecha_ingreso: new Date().toISOString().slice(0, 10),
    proveedor_id: null,
    full_set: false,
    full_set_detalle: '',
    sucursal_actual_id: null,
  }
}

const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')
const foto = ref(null)
const fotoPreview = ref('')

const calibres = ref([])
const marcas = ref([])
const materiales = ref([])
const colores = ref([])
const proveedores = ref([])
const sucursales = ref([])
const pendientes = ref([])

const lineaSel = computed(() =>
  pendientes.value.find((l) => l.recepcion_linea_id === f.recepcion_linea_id),
)
const anclado = computed(() => Boolean(props.recepcionLinea))

async function recargar() {
  const [c, m, mat, col, p, s, pend] = await Promise.all([
    listarCalibres().catch(() => []),
    listarMarcasReloj(true).catch(() => []),
    listarMateriales(true).catch(() => []),
    listarColores(true).catch(() => []),
    listarProveedores({ estado: 'activo', page: 1 }).catch(() => ({ items: [] })),
    listarSucursales().catch(() => ({ items: [] })),
    lineasPendientesRecepcion().catch(() => []),
  ])
  calibres.value = c
  marcas.value = m
  materiales.value = mat
  colores.value = col
  proveedores.value = p.items
  sucursales.value = s.items
  pendientes.value = pend.map((l) => ({ ...l, _label: `OC #${l.orden_compra_id} · ${l.item_ref} · ${l.pendientes} pend.` }))
}
onMounted(recargar)

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    Object.assign(f, vacio())
    error.value = ''
    foto.value = null
    fotoPreview.value = ''
    if (props.recepcionLinea) {
      f.recepcion_linea_id = props.recepcionLinea.recepcion_linea_id
      prefillDesdeLinea(props.recepcionLinea)
    }
  },
)

function prefillDesdeLinea(l) {
  if (!l) return
  f.proveedor_id = l.proveedor_id
  f.sucursal_actual_id = l.sucursal_destino_id
  if (l.costo_unitario != null) f.costo_adquisicion = l.costo_unitario
  if (!f.referencia) f.referencia = l.item_ref
  if (!f.numero_serie && l.numero_serie) f.numero_serie = l.numero_serie
  if (!f.anio_fabricacion && l.anio) f.anio_fabricacion = l.anio
  if (!f.marca_id && l.marca) f.marca_id = marcas.value.find((m) => m.nombre === l.marca)?.id ?? null
  if (!f.calibre_id && l.calibre_codigo) f.calibre_id = calibres.value.find((c) => c.codigo === l.calibre_codigo)?.id ?? null
}

watch(() => f.recepcion_linea_id, () => prefillDesdeLinea(lineaSel.value))

function onFoto(ev) {
  const file = ev.target.files[0]
  foto.value = file || null
  fotoPreview.value = file ? URL.createObjectURL(file) : ''
}

// --- creación inline de valores de catálogo ---
async function nuevoCalibre(texto) {
  try {
    const c = await crearCalibre({ codigo: texto })
    calibres.value.push(c)
    toast.success(`Calibre ${c.codigo} creado`)
    return c
  } catch (e) {
    toast.error(e.message)
    return null
  }
}
async function nuevaMarca(texto) {
  try {
    const m = await crearMarcaReloj({ nombre: texto })
    marcas.value.push(m)
    toast.success(`Marca «${m.nombre}» creada. Puedes completar país y web en Configuración.`)
    return m
  } catch (e) {
    toast.error(e.message)
    return null
  }
}
async function nuevoMaterial(texto) {
  try {
    const m = await crearMaterial(texto)
    materiales.value.push(m)
    return m
  } catch (e) {
    toast.error(e.message)
    return null
  }
}
async function nuevoColor(texto) {
  try {
    const c = await crearColor({ nombre: texto })
    colores.value.push(c)
    return c
  } catch (e) {
    toast.error(e.message)
    return null
  }
}

async function guardar() {
  error.value = ''
  if (!f.numero_serie.trim()) return (error.value = 'El número de serie es obligatorio.')
  if (!f.marca_id) return (error.value = 'Elige la marca (o créala con «+»).')
  if (!f.referencia.trim()) return (error.value = 'La referencia / modelo es obligatoria.')
  if (!f.sucursal_actual_id) return (error.value = 'Elige la sucursal donde queda la unidad.')
  if (!f.recepcion_linea_id && f.motivo_alta_manual.trim().length < 3)
    return (error.value = 'Sin orden de compra: indica el motivo del alta manual (inventario inicial, recompra a cliente…).')
  guardando.value = true
  try {
    const ficha = {
      ...f,
      tipo_cristal: f.tipo_cristal || null,
      anio_fabricacion: f.anio_fabricacion ? Number(f.anio_fabricacion) : null,
      costo_adquisicion: f.costo_adquisicion === '' ? null : f.costo_adquisicion,
      precio_venta: f.precio_venta === '' ? null : f.precio_venta,
      full_set_detalle: f.full_set ? f.full_set_detalle : null,
      motivo_alta_manual: f.recepcion_linea_id ? null : f.motivo_alta_manual.trim(),
    }
    const creado = await crearReloj(ficha, foto.value)
    emit('creado', creado.numero_serie)
    await recargar()
    // Si quedan líneas de recepción pendientes de fichar, seguimos en el modal.
    if (pendientes.value.length) {
      const restantes = pendientes.value.reduce((s, l) => s + l.pendientes, 0)
      toast.success(`Unidad ${creado.numero_serie} registrada · quedan ${restantes} por fichar`)
      Object.assign(f, vacio())
      // encadena con la siguiente línea pendiente
      f.recepcion_linea_id = pendientes.value[0].recepcion_linea_id
      prefillDesdeLinea(pendientes.value[0])
      foto.value = null
      fotoPreview.value = ''
    } else {
      toast.success(`Unidad ${creado.numero_serie} registrada`)
      emit('update:modelValue', false)
    }
  } catch (e) {
    error.value =
      e.status === 409 ? 'Ya existe una unidad con ese número de serie.' :
      e.status === 403 ? 'No tienes permiso para registrar unidades.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    titulo="Registrar unidad de reloj"
    subtitulo="Lo normal es que las unidades entren al recibir una orden de compra. Un alta suelta exige un motivo."
    :guardando="guardando"
    ancho="max-w-3xl"
    :sucio="!!f.numero_serie"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <div v-if="anclado" class="sm:col-span-2 rounded-lg bg-good-bg px-3 py-2 text-xs text-good">
      Unidad anclada a la recepción de la OC #{{ recepcionLinea.orden_compra_id }} — hereda proveedor, costo y sucursal.
    </div>
    <FormField
      v-else-if="pendientes.length"
      label="Vincular a una recepción de compra"
      wide
      helper="Hereda proveedor, sucursal y costo. Si la eliges, no hace falta motivo."
    >
      <ComboBox
        v-model="f.recepcion_linea_id"
        :opciones="pendientes"
        opcion-label="_label"
        opcion-value="recepcion_linea_id"
        placeholder="Elegir línea recibida pendiente de fichar…"
      />
    </FormField>

    <FormField
      v-if="!f.recepcion_linea_id && !anclado"
      label="Motivo del alta manual"
      required
      wide
      helper="Inventario inicial, recompra a un cliente, consignación, regularización…"
    >
      <input v-model="f.motivo_alta_manual" class="cr-input" />
    </FormField>

    <FormField label="Número de serie" required>
      <input v-model="f.numero_serie" class="cr-input" required />
    </FormField>
    <FormField label="Estado del producto">
      <select v-model="f.estado_producto" class="cr-input">
        <option value="nuevo">Nuevo</option>
        <option value="usado">Usado</option>
      </select>
    </FormField>

    <FormField label="Marca" required helper="Escribe y pulsa «+ Crear» si no está en la lista.">
      <ComboBox
        v-model="f.marca_id" :opciones="marcas" opcion-label="nombre" opcion-value="id"
        placeholder="Elegir marca…" :crear="nuevaMarca" crear-label="Crear marca"
      />
    </FormField>
    <FormField label="Referencia / modelo" required><input v-model="f.referencia" class="cr-input" required /></FormField>

    <FormField label="Calibre / movimiento">
      <ComboBox
        v-model="f.calibre_id" :opciones="calibres" opcion-label="codigo" opcion-value="id"
        placeholder="Elegir calibre…" :crear="nuevoCalibre" crear-label="Crear calibre"
      />
    </FormField>
    <FormField label="Año de fabricación">
      <input v-model="f.anio_fabricacion" type="number" min="1900" max="2100" class="cr-input" />
    </FormField>

    <FormField label="Material de la caja">
      <ComboBox v-model="f.material_caja_id" :opciones="materiales" opcion-label="nombre" opcion-value="id"
        placeholder="Elegir material…" :crear="nuevoMaterial" crear-label="Crear material" />
    </FormField>
    <FormField label="Material del brazalete">
      <ComboBox v-model="f.material_brazalete_id" :opciones="materiales" opcion-label="nombre" opcion-value="id"
        placeholder="Elegir material…" :crear="nuevoMaterial" crear-label="Crear material" />
    </FormField>
    <FormField label="Color de esfera">
      <ComboBox v-model="f.color_esfera_id" :opciones="colores" opcion-label="nombre" opcion-value="id"
        placeholder="Elegir color…" :crear="nuevoColor" crear-label="Crear color" />
    </FormField>
    <FormField label="Tipo de cristal">
      <select v-model="f.tipo_cristal" class="cr-input">
        <option value="">—</option>
        <option v-for="c in CRISTALES" :key="c" :value="c">{{ c }}</option>
      </select>
    </FormField>
    <FormField label="Resistencia al agua"><input v-model="f.resistencia_agua" class="cr-input" placeholder="p. ej. 300 m" /></FormField>

    <FormField label="Costo de adquisición" helper="Visible solo para roles administrativos.">
      <input v-model="f.costo_adquisicion" type="number" min="0" step="0.01" class="cr-input" />
    </FormField>
    <FormField label="Precio de venta"><input v-model="f.precio_venta" type="number" min="0" step="0.01" class="cr-input" /></FormField>

    <FormField label="Proveedor">
      <ComboBox v-model="f.proveedor_id" :opciones="proveedores" opcion-label="razon_social" opcion-value="id" placeholder="Elegir proveedor…" />
    </FormField>
    <FormField label="Sucursal actual" required>
      <ComboBox v-model="f.sucursal_actual_id" :opciones="sucursales" opcion-label="nombre" opcion-value="id" placeholder="Elegir sucursal…" />
    </FormField>
    <FormField label="Fecha de ingreso a stock"><input v-model="f.fecha_ingreso" type="date" class="cr-input" /></FormField>

    <div class="sm:col-span-2">
      <label class="flex items-center gap-2 text-sm">
        <input v-model="f.full_set" type="checkbox" /> Full Set (caja, papeles, garantía, eslabones extra…)
      </label>
      <input v-if="f.full_set" v-model="f.full_set_detalle" class="cr-input mt-2" placeholder="Detalle del Full Set" />
    </div>

    <FormField label="Foto principal" wide helper="Se sube a reloj-imagenes al guardar. Puedes añadir más desde la ficha.">
      <div class="flex items-center gap-3">
        <label class="cr-btn cr-btn-ghost cursor-pointer text-xs">
          <CrIcon name="camera" :size="14" /> Elegir imagen
          <input type="file" accept="image/*" class="hidden" @change="onFoto" />
        </label>
        <img v-if="fotoPreview" :src="fotoPreview" alt="Vista previa" class="h-14 w-14 rounded-lg border border-hairline object-cover" />
      </div>
    </FormField>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
