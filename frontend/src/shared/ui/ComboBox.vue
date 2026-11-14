<script setup>
/**
 * Escribir para filtrar y seleccionar de opciones existentes (Principio XI:
 * "escribir para filtrar, no para crear un valor nuevo"). Nunca deja un valor
 * inexistente: al perder foco sin selección, revierte.
 *
 *   <ComboBox v-model="proveedorId" :opciones="proveedores"
 *             opcion-label="razon_social" opcion-value="id" placeholder="Proveedor…" />
 */
import { computed, ref, watch } from 'vue'
import CrIcon from './CrIcon.vue'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  opciones: { type: Array, default: () => [] },
  opcionLabel: { type: String, default: 'nombre' },
  opcionValue: { type: String, default: 'id' },
  placeholder: { type: String, default: 'Buscar…' },
  clearable: { type: Boolean, default: true },
  // Si se pasa, aparece un "＋ Crear «texto»" al final: `crear(texto) => nuevaOpcion|null`.
  crear: { type: Function, default: null },
  crearLabel: { type: String, default: 'Crear' },
  // Búsqueda remota (catálogos grandes, cientos+ de filas): en vez de filtrar
  // `opciones` en el cliente, emite `buscar` con lo tecleado (debounced por el
  // padre) y pinta `opciones` tal cual — el padre es quien la llena. El padre debe
  // incluir la opción ya elegida en `opciones` para que la etiqueta se siga viendo
  // cerrado el desplegable.
  remoto: { type: Boolean, default: false },
  // Solo con `remoto`: el padre pone esto en true mientras espera la respuesta.
  buscando: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'creado', 'buscar'])
const creando = ref(false)

const puedeCrear = computed(() => {
  const q = consulta.value.trim()
  if (!props.crear || !q) return false
  return !props.opciones.some((o) => String(o[props.opcionLabel]).toLowerCase() === q.toLowerCase())
})

async function crearNuevo() {
  if (creando.value) return
  creando.value = true
  try {
    const nueva = await props.crear(consulta.value.trim())
    if (nueva) {
      emit('creado', nueva)
      emit('update:modelValue', nueva[props.opcionValue])
      abierto.value = false
      consulta.value = ''
    }
  } finally {
    creando.value = false
  }
}

const abierto = ref(false)
const consulta = ref('')
const idx = ref(0)
const root = ref(null)

const seleccion = computed(() =>
  props.opciones.find((o) => o[props.opcionValue] === props.modelValue),
)
const etiquetaSel = computed(() => (seleccion.value ? seleccion.value[props.opcionLabel] : ''))

const filtradas = computed(() => {
  if (props.remoto) return props.opciones
  const q = consulta.value.trim().toLowerCase()
  if (!q) return props.opciones
  return props.opciones.filter((o) => String(o[props.opcionLabel]).toLowerCase().includes(q))
})

watch(abierto, (v) => {
  if (v) {
    consulta.value = ''
    idx.value = 0
    if (props.remoto) emit('buscar', '')
  }
})
watch(consulta, (q) => {
  if (props.remoto) emit('buscar', q.trim())
})

function elegir(o) {
  emit('update:modelValue', o[props.opcionValue])
  abierto.value = false
}
function limpiar() {
  emit('update:modelValue', null)
}
function onKey(e) {
  if (!abierto.value && (e.key === 'ArrowDown' || e.key === 'Enter')) {
    abierto.value = true
    return
  }
  if (e.key === 'ArrowDown') idx.value = Math.min(idx.value + 1, filtradas.value.length - 1)
  else if (e.key === 'ArrowUp') idx.value = Math.max(idx.value - 1, 0)
  else if (e.key === 'Enter') {
    e.preventDefault()
    if (filtradas.value[idx.value]) elegir(filtradas.value[idx.value])
  } else if (e.key === 'Escape') abierto.value = false
}
function onBlur() {
  // cierra al siguiente tick para permitir el click en una opción
  setTimeout(() => {
    if (creando.value) return
    abierto.value = false
    consulta.value = ''
  }, 150)
}
</script>

<template>
  <div ref="root" class="relative">
    <div class="relative">
      <input
        class="cr-input pr-16"
        :value="abierto ? consulta : etiquetaSel"
        :placeholder="placeholder"
        @focus="abierto = true"
        @input="((consulta = $event.target.value), (abierto = true), (idx = 0))"
        @keydown="onKey"
        @blur="onBlur"
      />
      <div class="absolute inset-y-0 right-2 flex items-center gap-1 text-ink-3">
        <button
          v-if="clearable && modelValue != null"
          type="button"
          class="rounded p-0.5 hover:text-ink"
          aria-label="Limpiar"
          @mousedown.prevent="limpiar"
        >
          <CrIcon name="x" :size="14" />
        </button>
        <CrIcon name="chevron-down" :size="16" />
      </div>
    </div>

    <ul
      v-if="abierto"
      class="absolute z-30 mt-1 max-h-60 w-full overflow-y-auto rounded-xl border border-hairline bg-surface py-1 shadow-md"
    >
      <li
        v-for="(o, i) in filtradas"
        :key="o[opcionValue]"
        class="cursor-pointer px-3 py-2 text-sm"
        :class="i === idx ? 'bg-surface-sunk text-ink' : 'text-ink-2'"
        @mousedown.prevent="elegir(o)"
        @mouseenter="idx = i"
      >
        {{ o[opcionLabel] }}
        <slot name="secundario" :opcion="o" />
      </li>
      <li v-if="remoto && buscando" class="px-3 py-2 text-sm text-ink-3">Buscando…</li>
      <li v-else-if="!filtradas.length && !puedeCrear" class="px-3 py-2 text-sm text-ink-3">Sin coincidencias</li>
      <li
        v-if="puedeCrear"
        class="sticky bottom-0 flex cursor-pointer items-center gap-2 border-t border-hairline bg-surface px-3 py-2 text-sm font-medium text-gold-strong hover:bg-surface-sunk"
        @mousedown.prevent="crearNuevo"
      >
        <CrIcon name="plus" :size="14" />
        {{ crearLabel }} «{{ consulta.trim() }}»
      </li>
    </ul>
  </div>
</template>
<!-- botón "+" también fuera del dropdown para cuando ya hay una selección -->

