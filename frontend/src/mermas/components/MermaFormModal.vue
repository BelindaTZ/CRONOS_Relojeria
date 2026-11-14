<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { listarCategoriasMerma, crearCategoriaMerma } from '@/configuracion'
import { listarSucursales } from '@/sucursales'
import { listarPiezas } from '@/piezas'
import { crearMerma } from '@/mermas/services/mermasApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // prellenado desde 008 (daño en servicio) o 004 (discrepancia de transferencia)
  prefill: { type: Object, default: null },
  discrepanciaId: { type: Number, default: null },
})
const emit = defineEmits(['update:modelValue', 'guardado'])

const session = useSessionStore()

const CAUSAS = [
  ['dano_tienda', 'Daño en tienda'], ['dano_transito', 'Daño en tránsito/transporte'],
  ['robo_perdida', 'Robo o pérdida'], ['defecto_fabrica', 'Defecto de fábrica'],
  ['dano_servicio', 'Daño durante servicio técnico'], ['insumo_caducado', 'Insumo / repuesto caducado'],
]

function vacio() {
  return {
    bien_tipo: 'reloj', numero_serie: '', pieza_id: null, cantidad: 1,
    causa: 'dano_tienda', categoria_merma_id: null, descripcion: '',
    fecha_evento: new Date().toISOString().slice(0, 10), sucursal_id: null,
    orden_trabajo_id: null, tecnico_id: null, transferencia_id: null,
  }
}
const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')
const piezas = ref([])
const sucursales = ref([])
const categorias = ref([])

const misSucursales = computed(() => session.perfil?.sucursal_ids || [])
const mostrarSelectorSucursal = computed(() => misSucursales.value.length !== 1)

async function cargarCategorias(causa) {
  categorias.value = await listarCategoriasMerma(causa).catch(() => [])
}
async function nuevaCategoria(nombre) {
  try {
    const c = await crearCategoriaMerma({ nombre, causa: f.causa })
    categorias.value.push(c)
    return c
  } catch (e) {
    toast.error(e.message)
    return null
  }
}
watch(() => f.causa, (causa, anterior) => {
  cargarCategorias(causa)
  if (anterior !== undefined) f.categoria_merma_id = null
})

onMounted(async () => {
  ;[piezas.value, sucursales.value] = await Promise.all([
    listarPiezas({ size: 100 }).then((r) => r.items).catch(() => []),
    listarSucursales().then((r) => r.items).catch(() => []),
  ])
  cargarCategorias(f.causa)
})

watch(() => props.modelValue, (abierto) => {
  if (!abierto) return
  Object.assign(f, vacio())
  if (misSucursales.value.length === 1) f.sucursal_id = misSucursales.value[0]
  if (props.prefill) {
    f.causa = props.prefill.causa || f.causa
    f.numero_serie = props.prefill.reloj_serie || ''
    if (props.prefill.reloj_id && !props.prefill.reloj_serie) f.bien_tipo = 'reloj'
    if (props.prefill.pieza_id) { f.bien_tipo = 'pieza'; f.pieza_id = props.prefill.pieza_id }
    if (props.prefill.cantidad) f.cantidad = props.prefill.cantidad
    f.orden_trabajo_id = props.prefill.orden_trabajo_id || null
    f.tecnico_id = props.prefill.tecnico_id || null
    f.transferencia_id = props.prefill.transferencia_id || null
    if (props.prefill.sucursal_id) f.sucursal_id = props.prefill.sucursal_id
  }
})

async function guardar() {
  if (f.bien_tipo === 'reloj' && !f.numero_serie.trim()) {
    return (error.value = 'Indica el número de serie del reloj.')
  }
  if (f.bien_tipo === 'pieza' && !f.pieza_id) {
    return (error.value = 'Elige la pieza.')
  }
  if (!f.sucursal_id) return (error.value = 'Indica la sucursal.')
  error.value = ''
  guardando.value = true
  try {
    const body = {
      bien_tipo: f.bien_tipo,
      numero_serie: f.bien_tipo === 'reloj' ? f.numero_serie.trim() : null,
      pieza_id: f.bien_tipo === 'pieza' ? f.pieza_id : null,
      cantidad: f.bien_tipo === 'pieza' ? Number(f.cantidad) || 1 : 1,
      causa: f.causa, categoria_merma_id: f.categoria_merma_id, descripcion: f.descripcion.trim() || null,
      fecha_evento: f.fecha_evento, sucursal_id: f.sucursal_id,
      orden_trabajo_id: f.orden_trabajo_id, tecnico_id: f.tecnico_id, transferencia_id: f.transferencia_id,
    }
    const m = await crearMerma(body, props.discrepanciaId)
    toast.success(`Merma ${m.numero} registrada`)
    emit('update:modelValue', false)
    emit('guardado', m)
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue" titulo="Reportar merma" :guardando="guardando" ancho="max-w-lg"
    :sucio="true" @update:model-value="$emit('update:modelValue', $event)" @guardar="guardar"
  >
    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>

    <FormField label="Bien afectado" required>
      <select v-model="f.bien_tipo" class="cr-input" :disabled="!!prefill">
        <option value="reloj">Reloj (por N.º de serie)</option>
        <option value="pieza">Pieza / repuesto</option>
      </select>
    </FormField>

    <FormField v-if="f.bien_tipo === 'reloj'" label="Número de serie" required>
      <input v-model="f.numero_serie" class="cr-input tabular-nums" placeholder="Ej. RLX-3235-001" :disabled="!!prefill?.reloj_serie" />
    </FormField>
    <template v-else>
      <FormField label="Pieza" required>
        <ComboBox
          v-model="f.pieza_id" :opciones="piezas" opcion-label="codigo" opcion-value="id"
          placeholder="Buscar por código o descripción…"
        />
      </FormField>
      <FormField label="Cantidad" required helper="No puede superar el stock disponible de la sucursal.">
        <input v-model="f.cantidad" type="number" min="1" step="1" class="cr-input tabular-nums" />
      </FormField>
    </template>

    <FormField label="Causa" required>
      <select v-model="f.causa" class="cr-input" :disabled="!!prefill?.causa">
        <option v-for="[c, l] in CAUSAS" :key="c" :value="c">{{ l }}</option>
      </select>
    </FormField>

    <FormField label="Categoría / motivo específico" helper="Ej. «Caída accidental», «Robo con violencia»… precisa la causa elegida.">
      <ComboBox
        v-model="f.categoria_merma_id" :opciones="categorias" opcion-label="nombre" opcion-value="id"
        placeholder="Buscar o crear…" :crear="nuevaCategoria" crear-label="Crear categoría"
      />
    </FormField>

    <FormField label="Descripción del hecho" wide helper="Qué pasó exactamente — el relato del incidente.">
      <textarea v-model="f.descripcion" rows="2" class="cr-input" maxlength="500" />
    </FormField>

    <FormField label="Fecha del evento" required>
      <input v-model="f.fecha_evento" type="date" class="cr-input" />
    </FormField>

    <FormField v-if="mostrarSelectorSucursal" label="Sucursal" required>
      <select v-model="f.sucursal_id" class="cr-input">
        <option :value="null" disabled>Elige una sucursal</option>
        <option
          v-for="s in sucursales.filter((x) => !misSucursales.length || misSucursales.includes(x.id))"
          :key="s.id" :value="s.id"
        >{{ s.nombre }}</option>
      </select>
    </FormField>
  </FormModal>
</template>
