/**
 * API pública del módulo `mermas` (Principio X).
 *
 * `MermaFormModal` se reexporta para que 008 (daño en servicio) y 004
 * (discrepancia de transferencia) abran el mismo formulario prellenado con
 * `causa`/`reloj_id|numero_serie`/`pieza_id`/`cantidad` — en vez de duplicar
 * un formulario propio o dejar un botón deshabilitado esperando esta feature.
 */
export { default as MermaFormModal } from '@/mermas/components/MermaFormModal.vue'
export { routes } from '@/mermas/routes'
