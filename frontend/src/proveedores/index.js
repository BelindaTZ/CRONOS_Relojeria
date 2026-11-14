/**
 * API pública del módulo `proveedores`. Otros módulos importan desde `@/proveedores`
 * (nunca de `proveedores/services/*` o `proveedores/components/*` — Principio X).
 */
export { listarProveedores, prellenarOrden } from '@/proveedores/services/proveedoresApi'
export { routes } from '@/proveedores/routes'
