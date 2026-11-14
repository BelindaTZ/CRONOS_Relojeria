<script setup>
/**
 * Tira de KPIs dentro de un panel (2–4 métricas). Una sola tarjeta con celdas
 * divididas por hairline — no tarjetas sueltas. La cifra "cabecera" puede ir en
 * oro (Principio XI: el oro comunica valor).
 *
 *   <KpiStrip :items="[
 *     { label: 'Proveedores activos', value: '18' },
 *     { label: 'Mejor calificado', value: 'Moebius EC', sub: '4.7 / 5' },
 *     { label: 'Cumplimiento prom.', value: '+2,1 d', gold: true },
 *   ]" />
 */
defineProps({ items: { type: Array, required: true } })
</script>

<template>
  <div class="cr-card mb-8 grid grid-cols-2 divide-hairline overflow-hidden shadow-sm sm:flex sm:divide-x">
    <div v-for="(k, i) in items" :key="i" class="flex-1 px-5 py-4" :class="{ 'border-t border-hairline sm:border-t-0': i >= 2 }">
      <p class="text-[0.66rem] font-semibold uppercase tracking-[0.13em] text-ink-3">{{ k.label }}</p>
      <p
        class="serif mt-1 text-2xl leading-none"
        :class="k.gold ? 'text-gold-strong' : 'text-ink'"
        style="font-variant-numeric: tabular-nums"
      >
        {{ k.value }}
      </p>
      <p v-if="k.sub" class="mt-1 text-xs text-ink-2">{{ k.sub }}</p>
    </div>
  </div>
</template>
