import PanelGerencia from '@/dashboards/components/PanelGerencia.vue'
import IndiceReportes from '@/dashboards/components/IndiceReportes.vue'
import ReporteAnalitico from '@/dashboards/components/ReporteAnalitico.vue'

export const routes = [
  { path: '/panel', name: 'panel-gerencia', component: PanelGerencia, meta: { soloGerencia: true } },
  { path: '/reportes', name: 'reportes-indice', component: IndiceReportes },
  { path: '/reportes/:slug', name: 'reporte-analitico', component: ReporteAnalitico, meta: { modulo: 'reportes', operacion: 'consultar' } },
]

export default routes
