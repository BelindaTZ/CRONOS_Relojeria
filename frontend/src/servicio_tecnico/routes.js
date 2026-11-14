import ListaOrdenesTrabajo from '@/servicio_tecnico/components/ListaOrdenesTrabajo.vue'
import FichaOrdenTrabajo from '@/servicio_tecnico/components/FichaOrdenTrabajo.vue'
import OrdenesEnCursoView from '@/servicio_tecnico/components/OrdenesEnCursoView.vue'
import InformeServiciosView from '@/servicio_tecnico/components/InformeServiciosView.vue'

export const routes = [
  { path: '/taller/ordenes', name: 'ordenes-trabajo', component: ListaOrdenesTrabajo, meta: { modulo: 'ordenes_trabajo' } },
  { path: '/taller/ordenes/:id', name: 'ot-ficha', component: FichaOrdenTrabajo, meta: { modulo: 'ordenes_trabajo' } },
  { path: '/taller/ordenes-en-curso', name: 'ot-en-curso', component: OrdenesEnCursoView, meta: { modulo: 'ordenes_trabajo' } },
  {
    path: '/taller/informe-servicios', name: 'informe-servicios', component: InformeServiciosView,
    meta: { modulo: 'ordenes_trabajo', roles: ['Gerencia General', 'Gerente de Sucursal', 'Contador', 'Técnico Jefe'] },
  },
]

export default routes
