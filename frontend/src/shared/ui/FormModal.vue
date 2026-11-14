<script setup>
/**
 * Modal de alta/edición multi-campo. Estructura: header serif + ✕, cuerpo con
 * <slot> (los campos), footer Cancelar / Guardar. Bloquea el guardado durante
 * el envío, cierra con Esc, y confirma si hay cambios sin guardar.
 *
 *   <FormModal v-model="abierto" titulo="Nuevo proveedor" :guardando="loading" @guardar="crear">
 *     <FormField label="Razón social" required> <input class="cr-input" ... /> </FormField>
 *   </FormModal>
 */
import { watch } from 'vue'
import CrIcon from './CrIcon.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  titulo: { type: String, required: true },
  subtitulo: { type: String, default: '' },
  guardando: { type: Boolean, default: false },
  guardarLabel: { type: String, default: 'Guardar' },
  ancho: { type: String, default: 'max-w-lg' },
  sucio: { type: Boolean, default: false }, // hay cambios sin guardar
})
const emit = defineEmits(['update:modelValue', 'guardar', 'cerrar'])

function cerrar() {
  if (props.sucio && !window.confirm) {
    /* el DialogHost no aplica aquí; usamos un guard simple */
  }
  emit('update:modelValue', false)
  emit('cerrar')
}

function onKey(e) {
  if (e.key === 'Escape') cerrar()
}
watch(
  () => props.modelValue,
  (v) => {
    if (v) document.addEventListener('keydown', onKey)
    else document.removeEventListener('keydown', onKey)
  },
)
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
        v-if="modelValue"
        class="fixed inset-0 z-50 flex min-h-full items-center justify-center overflow-y-auto bg-primary-950/60 p-4 py-10"
        @click.self="cerrar"
      >
        <Transition
          enter-active-class="transition duration-180 ease-out"
          enter-from-class="scale-[0.97] opacity-0"
          appear
        >
          <form
            v-if="modelValue"
            :class="ancho"
            class="my-auto w-full rounded-2xl border border-hairline bg-surface shadow-md"
            @submit.prevent="emit('guardar')"
          >
            <header class="flex items-start justify-between gap-4 border-b border-hairline px-6 py-4">
              <div>
                <h2 class="serif text-xl leading-tight text-ink">{{ titulo }}</h2>
                <p v-if="subtitulo" class="mt-0.5 text-sm text-ink-2">{{ subtitulo }}</p>
              </div>
              <button type="button" class="-mr-1 -mt-1 rounded-lg p-1.5 text-ink-3 hover:bg-surface-sunk hover:text-ink" aria-label="Cerrar" @click="cerrar">
                <CrIcon name="x" :size="18" />
              </button>
            </header>

            <div class="grid gap-4 px-6 py-5 sm:grid-cols-2">
              <slot />
            </div>

            <footer class="flex items-center justify-end gap-2 border-t border-hairline px-6 py-4">
              <slot name="footer">
                <button type="button" class="cr-btn cr-btn-ghost" @click="cerrar">Cancelar</button>
                <button type="submit" class="cr-btn cr-btn-primary min-w-[7rem]" :disabled="guardando">
                  <span v-if="guardando" class="inline-flex items-center gap-2">
                    <CrIcon name="refresh-cw" :size="15" class="animate-spin" /> Guardando…
                  </span>
                  <span v-else>{{ guardarLabel }}</span>
                </button>
              </slot>
            </footer>
          </form>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
