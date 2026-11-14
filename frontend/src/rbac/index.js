/**
 * API pública del módulo RBAC. Otros módulos importan SOLO desde aquí
 * (`@/rbac`), nunca de `rbac/services/*` o `rbac/components/*` (Principio X).
 */
export { listarRoles, listarModulos } from '@/rbac/services/rbacApi'
export { routes } from '@/rbac/routes'
