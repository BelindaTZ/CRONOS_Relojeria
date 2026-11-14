<script setup>
/**
 * Insignia de salud de la plataforma, mostrada en el shell (barra superior).
 * Verde (tertiary) = todo arriba; ámbar (warning) = degradado; rojo (danger) = sin contacto.
 */
import { computed } from 'vue'
import { useHealth } from '@/health/composables/useHealth'

const { health, error } = useHealth()

const estado = computed(() => {
  if (error.value) return { texto: 'Sin contacto', clase: 'bg-danger-600 text-white' }
  if (!health.value) return { texto: 'Comprobando…', clase: 'bg-neutral-500 text-white' }
  if (health.value.status === 'ok') return { texto: 'Operativo', clase: 'bg-tertiary-600 text-white' }
  return { texto: 'Degradado', clase: 'bg-warning-600 text-white' }
})

const detalle = computed(() => {
  if (!health.value) return ''
  return `db: ${health.value.db} · almacenamiento: ${health.value.storage}`
})
</script>

<template>
  <span
    class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold"
    :class="estado.clase"
    :title="detalle"
  >
    <span class="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
    {{ estado.texto }}
  </span>
</template>
