import ListaTecnicos from '@/tecnicos/components/ListaTecnicos.vue'
import FichaTecnico from '@/tecnicos/components/FichaTecnico.vue'
import ReglasBonoView from '@/tecnicos/components/ReglasBonoView.vue'
import PanelBonos from '@/tecnicos/components/PanelBonos.vue'
import PanelProductividad from '@/tecnicos/components/PanelProductividad.vue'

export const routes = [
  { path: '/tecnicos', name: 'tecnicos', component: ListaTecnicos, meta: { modulo: 'tecnicos' } },
  {
    path: '/tecnicos/reglas-bono', name: 'reglas-bono', component: ReglasBonoView,
    meta: { modulo: 'tecnicos', roles: ['Gerencia General', 'Técnico Jefe'] },
  },
  {
    path: '/tecnicos/bonos', name: 'bonos-periodo', component: PanelBonos,
    meta: { modulo: 'tecnicos', roles: ['Gerencia General', 'Gerente de Sucursal', 'Contador', 'Técnico Jefe'] },
  },
  { path: '/tecnicos/productividad', name: 'productividad', component: PanelProductividad, meta: { modulo: 'tecnicos' } },
  { path: '/tecnicos/:id', name: 'tecnico-ficha', component: FichaTecnico, meta: { modulo: 'tecnicos' } },
]

export default routes
