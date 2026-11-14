import ListaCitas from '@/citas/components/ListaCitas.vue'
import AgendaView from '@/citas/components/AgendaView.vue'

export const routes = [
  { path: '/citas', name: 'citas', component: ListaCitas, meta: { modulo: 'citas' } },
  { path: '/citas/agenda', name: 'citas-agenda', component: AgendaView, meta: { modulo: 'citas' } },
]

export default routes
