import ListaMermas from '@/mermas/components/ListaMermas.vue'
import FichaMerma from '@/mermas/components/FichaMerma.vue'
import ReporteMermasView from '@/mermas/components/ReporteMermasView.vue'

export const routes = [
  { path: '/mermas', name: 'mermas', component: ListaMermas, meta: { modulo: 'mermas' } },
  { path: '/mermas/reporte', name: 'reporte-mermas', component: ReporteMermasView, meta: { modulo: 'mermas' } },
  { path: '/mermas/:id', name: 'merma-ficha', component: FichaMerma, meta: { modulo: 'mermas' } },
]

export default routes
