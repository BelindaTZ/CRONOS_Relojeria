/**
 * API pública de enrutado del módulo `health`. El registro central de rutas
 * (`src/router/index.js`) importa SOLO desde aquí — nunca de los componentes
 * internos del módulo (Principio X). Patrón a replicar por las features 001+.
 */
import HealthView from '@/health/components/HealthView.vue'

export const routes = [{ path: '/', name: 'inicio', component: HealthView }]

export default routes
