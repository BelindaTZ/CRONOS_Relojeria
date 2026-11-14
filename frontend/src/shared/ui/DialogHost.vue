<script setup>
/**
 * Pinta el diálogo activo de la cola de `shared/ui/dialogs.js`. Se monta UNA sola
 * vez en App.vue (Principio XI). Soporta confirm (con tono danger) y prompt.
 */
import { computed, ref, watch, nextTick } from 'vue'
import { dialogQueue, resolveCurrent } from './dialogs'
import CrIcon from './CrIcon.vue'

const dlg = computed(() => dialogQueue.current)
const inputValue = ref('')
const inputEl = ref(null)

watch(dlg, async (value) => {
  if (value?.type === 'prompt') {
    inputValue.value = value.initialValue ?? ''
    await nextTick()
    inputEl.value?.focus()
  }
})

const promptInvalid = computed(
  () => dlg.value?.type === 'prompt' && dlg.value.required && inputValue.value.trim() === '',
)
const esDanger = computed(() => dlg.value?.tone === 'danger')

function onConfirm() {
  if (!dlg.value) return
  if (dlg.value.type === 'confirm') resolveCurrent(true)
  else {
    if (promptInvalid.value) return
    resolveCurrent(inputValue.value.trim())
  }
}
function onCancel() {
  if (!dlg.value) return
  resolveCurrent(dlg.value.type === 'confirm' ? false : null)
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-if="dlg"
        class="fixed inset-0 z-[55] flex items-center justify-center bg-primary-950/55 p-4"
        @keydown.esc="onCancel"
      >
        <div
          class="w-full max-w-md rounded-2xl bg-surface shadow-md ring-1 ring-hairline"
          role="alertdialog"
          aria-modal="true"
          :aria-label="dlg.title"
        >
          <div class="flex gap-4 p-6">
            <span
              v-if="esDanger"
              class="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-bad-bg text-bad"
            >
              <CrIcon name="alert-triangle" :size="20" />
            </span>
            <div class="min-w-0 flex-1">
              <h2 class="serif text-lg text-ink">{{ dlg.title }}</h2>
              <p v-if="dlg.message" class="mt-1 text-sm text-ink-2">{{ dlg.message }}</p>

              <label v-if="dlg.type === 'prompt'" class="mt-3 block space-y-1">
                <span v-if="dlg.label" class="cr-label">{{ dlg.label }}</span>
                <input
                  ref="inputEl"
                  v-model="inputValue"
                  type="text"
                  :placeholder="dlg.placeholder"
                  class="cr-input"
                  @keydown.enter="onConfirm"
                />
              </label>
            </div>
          </div>

          <footer class="flex justify-end gap-2 border-t border-hairline px-6 py-4">
            <button type="button" class="cr-btn cr-btn-ghost" @click="onCancel">{{ dlg.cancelLabel }}</button>
            <button
              type="button"
              :disabled="promptInvalid"
              class="cr-btn"
              :class="esDanger ? 'cr-btn-danger' : 'cr-btn-primary'"
              @click="onConfirm"
            >
              {{ dlg.confirmLabel }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
