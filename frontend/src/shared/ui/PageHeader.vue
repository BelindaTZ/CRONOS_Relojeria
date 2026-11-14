<script setup>
/** Encabezado de página estándar (Principio XI): eyebrow de oro + título serif. */
defineProps({
  eyebrow: { type: String, default: '' },
  titulo: { type: String, required: true },
  sub: { type: String, default: '' },
})
</script>

<template>
  <div class="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-hairline pb-4">
    <div>
      <p v-if="eyebrow" class="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-gold">
        {{ eyebrow }}
      </p>
      <h1 class="serif text-2xl leading-tight text-ink">{{ titulo }}</h1>
      <p v-if="sub" class="mt-1 text-sm text-ink-2">{{ sub }}</p>
    </div>
    <div class="flex items-center gap-2">
      <slot name="acciones" />
    </div>
  </div>
</template>
