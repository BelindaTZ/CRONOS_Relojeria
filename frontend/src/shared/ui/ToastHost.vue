<script setup>
import { toastState, dismiss } from './toast'
import CrIcon from './CrIcon.vue'

const ICON = { success: 'circle-check', error: 'alert-triangle', info: 'info' }
const ACCENT = {
  success: 'var(--good)',
  error: 'var(--bad)',
  info: 'var(--color-primary-500)',
}
</script>

<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2">
      <TransitionGroup
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="translate-x-4 opacity-0"
        leave-active-class="transition duration-150 ease-in"
        leave-to-class="translate-x-4 opacity-0"
      >
        <div
          v-for="t in toastState.items"
          :key="t.id"
          class="pointer-events-auto flex items-start gap-3 rounded-xl border border-hairline bg-surface p-3.5 shadow-md"
          role="status"
          :aria-live="t.tipo === 'error' ? 'assertive' : 'polite'"
        >
          <span class="mt-0.5 h-full w-0.5 shrink-0 self-stretch rounded-full" :style="{ background: ACCENT[t.tipo] }" />
          <CrIcon :name="ICON[t.tipo]" :size="18" class="mt-0.5 shrink-0" :style="{ color: ACCENT[t.tipo] }" />
          <p class="flex-1 text-sm text-ink">{{ t.mensaje }}</p>
          <button class="shrink-0 text-ink-3 hover:text-ink" aria-label="Cerrar" @click="dismiss(t.id)">
            <CrIcon name="x" :size="16" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
