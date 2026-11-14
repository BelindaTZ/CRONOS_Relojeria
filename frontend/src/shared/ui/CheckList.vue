<script setup>
/** Lista de selección múltiple (checkboxes) para asignar roles / sucursales. */
const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  opciones: { type: Array, default: () => [] },
  opcionLabel: { type: String, default: 'nombre' },
  opcionValue: { type: String, default: 'id' },
})
const emit = defineEmits(['update:modelValue'])

function toggle(v) {
  const set = new Set(props.modelValue)
  set.has(v) ? set.delete(v) : set.add(v)
  emit('update:modelValue', [...set])
}
</script>

<template>
  <div class="max-h-44 space-y-1 overflow-y-auto rounded-xl border border-hairline p-2">
    <label
      v-for="o in opciones"
      :key="o[opcionValue]"
      class="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-surface-sunk"
    >
      <input
        type="checkbox"
        :checked="modelValue.includes(o[opcionValue])"
        @change="toggle(o[opcionValue])"
      />
      {{ o[opcionLabel] }}
    </label>
    <p v-if="!opciones.length" class="px-2 py-1 text-sm text-ink-3">Sin opciones.</p>
  </div>
</template>
