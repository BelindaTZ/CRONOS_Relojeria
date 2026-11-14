import CatalogosView from '@/configuracion/components/CatalogosView.vue'
import ParametrosView from '@/configuracion/components/ParametrosView.vue'
import AuditoriaView from '@/configuracion/components/AuditoriaView.vue'

export const routes = [
  { path: '/configuracion', name: 'configuracion', component: CatalogosView, meta: { soloGerencia: true } },
  { path: '/configuracion/parametros', name: 'parametros', component: ParametrosView, meta: { soloGerencia: true } },
  { path: '/configuracion/auditoria', name: 'auditoria', component: AuditoriaView, meta: { soloGerencia: true } },
]

export default routes
