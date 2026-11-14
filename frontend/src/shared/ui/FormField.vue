<script setup>
/** Campo de formulario: label micro + slot del control + helper/error. */
defineProps({
  label: { type: String, required: true },
  required: { type: Boolean, default: false },
  helper: { type: String, default: '' },
  error: { type: String, default: '' },
  wide: { type: Boolean, default: false }, // ocupa las 2 columnas del grid
})
</script>

<template>
  <label class="block space-y-1" :class="{ 'sm:col-span-2': wide }">
    <span class="cr-label">{{ label }}<span v-if="required" class="text-bad"> *</span></span>
    <slot />
    <span v-if="error" class="block text-xs text-bad" role="alert">{{ error }}</span>
    <span v-else-if="helper" class="block text-xs text-ink-3">{{ helper }}</span>
  </label>
</template>
