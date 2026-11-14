/**
 * Feedback efímero. `<ToastHost>` (montado una vez en App.vue) los pinta.
 *   import { toast } from '@/shared/ui/toast'
 *   toast.success('Proveedor creado')
 *   toast.error('No se pudo guardar')
 */
import { reactive } from 'vue'

let seq = 0
export const toastState = reactive({ items: [] })

function push(tipo, mensaje, { duracion } = {}) {
  const id = ++seq
  const ttl = duracion ?? (tipo === 'error' ? 6000 : 4000)
  toastState.items.push({ id, tipo, mensaje })
  if (toastState.items.length > 3) toastState.items.shift()
  const timer = setTimeout(() => dismiss(id), ttl)
  toastState.items[toastState.items.length - 1]._timer = timer
  return id
}

export function dismiss(id) {
  const i = toastState.items.findIndex((t) => t.id === id)
  if (i !== -1) {
    clearTimeout(toastState.items[i]._timer)
    toastState.items.splice(i, 1)
  }
}

export const toast = {
  success: (m, o) => push('success', m, o),
  error: (m, o) => push('error', m, o),
  info: (m, o) => push('info', m, o),
}
