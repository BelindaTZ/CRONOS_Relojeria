/**
 * Helper compartido de diálogos in-app (Principio XI).
 *
 * Prohibido `window.confirm` / `window.prompt` / `window.alert` en toda la app.
 * `<DialogHost>` (montado una vez en App.vue) escucha esta cola y pinta el modal
 * del design-system.
 *
 *   import { confirm, prompt } from '@/shared/ui/dialogs'
 *   if (await confirm({ title: 'Eliminar', message: '¿Seguro?' })) { ... }
 *   const motivo = await prompt({ title: 'Motivo de la merma' })  // null si cancela
 */
import { reactive } from 'vue'

let seq = 0

/** Estado reactivo observado por <DialogHost>. */
export const dialogQueue = reactive({ current: null })

function open(config) {
  return new Promise((resolve) => {
    dialogQueue.current = { id: ++seq, ...config, resolve }
  })
}

/** Resuelve el diálogo activo (lo llama <DialogHost>). */
export function resolveCurrent(value) {
  const dlg = dialogQueue.current
  dialogQueue.current = null
  if (dlg) dlg.resolve(value)
}

/**
 * Confirmación (aceptar / cancelar). Resuelve a `true` / `false`.
 */
export function confirm({
  title = 'Confirmar',
  message = '',
  confirmLabel = 'Aceptar',
  cancelLabel = 'Cancelar',
  tone = 'primary', // 'primary' | 'danger'
} = {}) {
  return open({ type: 'confirm', title, message, confirmLabel, cancelLabel, tone })
}

/**
 * Entrada de un dato puntual. Resuelve al texto, o `null` si se cancela.
 */
export function prompt({
  title = 'Ingresar dato',
  message = '',
  label = '',
  placeholder = '',
  initialValue = '',
  confirmLabel = 'Aceptar',
  cancelLabel = 'Cancelar',
  required = true,
} = {}) {
  return open({
    type: 'prompt',
    title,
    message,
    label,
    placeholder,
    initialValue,
    confirmLabel,
    cancelLabel,
    required,
  })
}
