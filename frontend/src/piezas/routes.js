import ListaPiezas from '@/piezas/components/ListaPiezas.vue'
import FichaPieza from '@/piezas/components/FichaPieza.vue'
import LotesCaducidad from '@/piezas/components/LotesCaducidad.vue'

export const routes = [
  { path: '/piezas', name: 'piezas', component: ListaPiezas, meta: { modulo: 'piezas' } },
  { path: '/piezas/lotes', name: 'piezas-lotes', component: LotesCaducidad, meta: { modulo: 'piezas' } },
  { path: '/piezas/:id', name: 'pieza-ficha', component: FichaPieza, meta: { modulo: 'piezas' } },
]

export default routes
