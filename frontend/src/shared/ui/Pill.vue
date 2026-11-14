<script setup>
/** Insignia de estado. `tone`: neutral | good | warn | bad | info. */
defineProps({
  tone: { type: String, default: 'neutral' },
  label: { type: String, required: true },
})
const CLASS = {
  neutral: 'bg-surface-sunk text-ink-2',
  good: 'bg-good-bg text-good',
  warn: 'bg-warn-bg text-warn',
  bad: 'bg-bad-bg text-bad',
  info: 'bg-primary-100 text-primary-700',
}
</script>

<template>
  <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-semibold" :class="CLASS[tone]">
    <span class="h-1.5 w-1.5 rounded-full bg-current opacity-70"></span>{{ label }}
  </span>
</template>
