<script setup>
/**
 * Menú de acciones por fila (kebab "⋮"). Las acciones destructivas van al final,
 * separadas por una línea y en color danger.
 *
 *   <RowMenu :acciones="[
 *     { label: 'Editar', icon: 'edit', onClick: () => editar(row) },
 *     { label: 'Inactivar', icon: 'ban', danger: true, onClick: () => inactivar(row) },
 *   ]" />
 */
import { ref } from 'vue'
import CrIcon from './CrIcon.vue'

defineProps({ acciones: { type: Array, required: true } })
const abierto = ref(false)

function ejecutar(a) {
  abierto.value = false
  a.onClick?.()
}
</script>

<template>
  <div class="relative inline-block text-left" @focusout="abierto = false">
    <button
      class="rounded-lg p-1.5 text-ink-3 hover:bg-surface-sunk hover:text-ink"
      aria-haspopup="true"
      :aria-expanded="abierto"
      aria-label="Acciones"
      @click.stop="abierto = !abierto"
    >
      <CrIcon name="more-vertical" :size="18" />
    </button>
    <div
      v-if="abierto"
      class="absolute right-0 z-30 mt-1 w-48 overflow-hidden rounded-xl border border-hairline bg-surface py-1 shadow-md"
    >
      <template v-for="(a, i) in acciones" :key="i">
        <hr v-if="a.danger && i > 0 && !acciones[i - 1].danger" class="my-1 border-hairline-soft" />
        <button
          class="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm hover:bg-surface-sunk"
          :class="a.danger ? 'text-bad' : 'text-ink-2 hover:text-ink'"
          :disabled="a.disabled"
          @click.stop="ejecutar(a)"
        >
          <CrIcon v-if="a.icon" :name="a.icon" :size="15" class="shrink-0" />
          {{ a.label }}
        </button>
      </template>
    </div>
  </div>
</template>
