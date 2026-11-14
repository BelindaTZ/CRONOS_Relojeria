<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CheckList from '@/shared/ui/CheckList.vue'
import { toast } from '@/shared/ui/toast'
import { listarProveedores } from '@/proveedores'
import { listarCalibres } from '@/inventario'
import { actualizarPieza, crearPieza } from '@/piezas/services/piezasApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  pieza: { type: Object, default: null }, // si viene, es edición
})
const emit = defineEmits(['update:modelValue', 'guardada'])

const UNIDADES = ['unidad', 'ml', 'g', 'mm', 'par', 'juego', 'metro', 'litro']

function vacio() {
  return {
    codigo: '',
    descripcion: '',
    tipo: 'original',
    unidad_medida: 'unidad',
    marca_compatible: '',
    proveedor_id: null,
    costo_adquisicion: null,
    precio_venta_suelta: null,
    stock_minimo: 0,
    perecedera: false,
    calibres_compatibles: [],
  }
}

const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')
const proveedores = ref([])
const calibres = ref([])

onMounted(async () => {
  const [p, c] = await Promise.all([
    listarProveedores({ estado: 'activo', page: 1 }).catch(() => ({ items: [] })),
    listarCalibres().catch(() => []),
  ])
  proveedores.value = p.items
  calibres.value = c
})

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    error.value = ''
    if (props.pieza) {
      Object.assign(f, {
        codigo: props.pieza.codigo,
        descripcion: props.pieza.descripcion,
        tipo: props.pieza.tipo,
        unidad_medida: props.pieza.unidad_medida ?? 'unidad',
        marca_compatible: props.pieza.marca_compatible ?? '',
        proveedor_id: props.pieza.proveedor_id ?? null,
        costo_adquisicion: props.pieza.costo_adquisicion ?? null,
        precio_venta_suelta: props.pieza.precio_venta_suelta ?? null,
        stock_minimo: props.pieza.stock_minimo ?? 0,
        perecedera: props.pieza.perecedera,
        calibres_compatibles: [...(props.pieza.calibres_compatibles || [])],
      })
    } else {
      Object.assign(f, vacio())
    }
  },
)

async function guardar() {
  error.value = ''
  if (!props.pieza && !f.codigo.trim()) return (error.value = 'El código es obligatorio.')
  if (!f.descripcion.trim()) return (error.value = 'La descripción es obligatoria.')
  guardando.value = true
  try {
    const payload = {
      ...f,
      stock_minimo: Number(f.stock_minimo) || 0,
      marca_compatible: f.marca_compatible.trim() || null,
      costo_adquisicion: f.costo_adquisicion === '' ? null : f.costo_adquisicion,
      precio_venta_suelta: f.precio_venta_suelta === '' ? null : f.precio_venta_suelta,
    }
    if (props.pieza) {
      delete payload.codigo
      await actualizarPieza(props.pieza.id, payload)
      toast.success('Pieza actualizada')
    } else {
      await crearPieza(payload)
      toast.success(`Pieza ${f.codigo} creada`)
    }
    emit('update:modelValue', false)
    emit('guardada')
  } catch (e) {
    error.value = e.status === 409 ? 'Ya existe una pieza con ese código.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="pieza ? 'Editar pieza' : 'Nueva pieza'"
    :guardando="guardando"
    ancho="max-w-2xl"
    :sucio="!!f.descripcion"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Código" required :helper="pieza ? 'El código no se modifica.' : ''">
      <input v-model="f.codigo" class="cr-input" :disabled="!!pieza" required />
    </FormField>
    <FormField label="Tipo">
      <select v-model="f.tipo" class="cr-input">
        <option value="original">Original</option>
        <option value="no_original_equivalente">No original (calidad equivalente)</option>
      </select>
    </FormField>

    <FormField label="Descripción" required wide><input v-model="f.descripcion" class="cr-input" required /></FormField>

    <FormField label="Unidad de medida" helper="Cómo se cuenta y se pide esta pieza.">
      <select v-model="f.unidad_medida" class="cr-input">
        <option v-for="u in UNIDADES" :key="u" :value="u">{{ u }}</option>
      </select>
    </FormField>
    <FormField label="Marca(s) compatible(s)" helper="Rolex, Omega… — deja vacío si es universal.">
      <input v-model="f.marca_compatible" class="cr-input" placeholder="Rolex, Tudor" />
    </FormField>

    <FormField label="Proveedor">
      <ComboBox v-model="f.proveedor_id" :opciones="proveedores" opcion-label="razon_social" opcion-value="id" placeholder="Elegir proveedor…" />
    </FormField>
    <FormField label="Stock mínimo"><input v-model="f.stock_minimo" type="number" min="0" class="cr-input" /></FormField>

    <FormField label="Costo de adquisición" helper="Visible solo para roles administrativos.">
      <input v-model="f.costo_adquisicion" type="number" min="0" step="0.01" class="cr-input" />
    </FormField>
    <FormField label="Precio de venta suelta"><input v-model="f.precio_venta_suelta" type="number" min="0" step="0.01" class="cr-input" /></FormField>

    <FormField label="Calibres compatibles" wide>
      <CheckList v-model="f.calibres_compatibles" :opciones="calibres" opcion-label="codigo" opcion-value="id" />
    </FormField>

    <div class="sm:col-span-2">
      <label class="flex items-center gap-2 text-sm">
        <input v-model="f.perecedera" type="checkbox" /> Perecedera (insumo con caducidad)
      </label>
      <p class="mt-1 text-xs text-ink-3">
        Cada ingreso pedirá lote y fecha de caducidad; el consumo descuenta primero el lote que vence antes (FEFO).
      </p>
    </div>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
