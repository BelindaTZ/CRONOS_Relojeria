/**
 * Registro central de rutas + guard de navegación por sesión (feature 001).
 * Cada feature añade su array `routes` desde `@/<modulo>/routes.js` (Principio X).
 */
import { createRouter, createWebHistory } from 'vue-router'

import { routes as healthRoutes } from '@/health/routes'
import { routes as authRoutes } from '@/auth/routes'
import { routes as perfilRoutes } from '@/perfil/routes'
import { routes as rbacRoutes } from '@/rbac/routes'
import { routes as usuariosRoutes } from '@/usuarios/routes'
import { routes as sucursalesRoutes } from '@/sucursales/routes'
import { routes as configuracionRoutes } from '@/configuracion/routes'
import { routes as proveedoresRoutes } from '@/proveedores/routes'
import { routes as inventarioRoutes } from '@/inventario/routes'
import { routes as piezasRoutes } from '@/piezas/routes'
import { routes as trasladosRoutes } from '@/traslados/routes'
import { routes as tecnicosRoutes } from '@/tecnicos/routes'
import { routes as clientesRoutes } from '@/clientes/routes'
import { routes as citasRoutes } from '@/citas/routes'
import { routes as servicioTecnicoRoutes } from '@/servicio_tecnico/routes'
import { routes as lubricacionRoutes } from '@/lubricacion/routes'
import { routes as ventasRoutes } from '@/ventas/routes'
import { routes as contabilidadRoutes } from '@/contabilidad/routes'
import { routes as mermasRoutes } from '@/mermas/routes'
import { routes as dashboardsRoutes } from '@/dashboards/routes'
import { routes as notificacionesRoutes } from '@/notificaciones/routes'
import { useSessionStore } from '@/shared/stores/session'
import { puedeEntrar } from '@/shared/rbacNav'

const routes = [
  ...healthRoutes,
  ...authRoutes,
  ...perfilRoutes,
  ...rbacRoutes,
  ...usuariosRoutes,
  ...sucursalesRoutes,
  ...configuracionRoutes,
  ...proveedoresRoutes,
  ...inventarioRoutes,
  ...piezasRoutes,
  ...trasladosRoutes,
  ...tecnicosRoutes,
  ...clientesRoutes,
  ...citasRoutes,
  ...servicioTecnicoRoutes,
  ...lubricacionRoutes,
  ...ventasRoutes,
  ...contabilidadRoutes,
  ...mermasRoutes,
  ...dashboardsRoutes,
  ...notificacionesRoutes,
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const s = useSessionStore()

  if (s.mustChangePassword && to.name !== 'cambiar-contrasena') {
    return { name: 'cambiar-contrasena' }
  }
  if (to.meta.publica) return true

  // Tras un reload el token persiste pero el perfil no: recárgalo antes de decidir.
  if (s.accessToken && !s.perfil && !s.mustChangePassword) {
    try {
      await s.cargarPerfil()
    } catch {
      await s.logout()
      return { name: 'login', query: { next: to.fullPath } }
    }
  }

  if (!s.autenticado) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  // Mismo predicado que pinta (u oculta) el nav en AppShell — Const. Ppio IV:
  // el backend sigue siendo la autoridad real vía `require_perm` en cada
  // endpoint, esto solo evita que alguien aterrice en una pantalla vacía.
  if (!puedeEntrar(s, to.meta)) {
    return { name: 'inicio' }
  }
  return true
})

export default router
