import CatalogoMoebiusView from '@/lubricacion/components/CatalogoMoebiusView.vue'
import FichasLubricacionView from '@/lubricacion/components/FichasLubricacionView.vue'
import DesviacionLubricacionView from '@/lubricacion/components/DesviacionLubricacionView.vue'

export const routes = [
  { path: '/taller/lubricacion/fichas', name: 'fichas-lubricacion', component: FichasLubricacionView, meta: { modulo: 'lubricacion' } },
  { path: '/taller/lubricacion/moebius', name: 'moebius', component: CatalogoMoebiusView, meta: { modulo: 'lubricacion' } },
  { path: '/taller/lubricacion/desviaciones', name: 'desviacion-lubricacion', component: DesviacionLubricacionView, meta: { modulo: 'lubricacion' } },
]

export default routes
