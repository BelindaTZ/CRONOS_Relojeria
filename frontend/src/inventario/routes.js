import ListaRelojes from '@/inventario/components/ListaRelojes.vue'
import FichaReloj from '@/inventario/components/FichaReloj.vue'
import CatalogoCalibres from '@/inventario/components/CatalogoCalibres.vue'
import PanelAlertasStock from '@/inventario/components/PanelAlertasStock.vue'
import ValorInventario from '@/inventario/components/ValorInventario.vue'

export const routes = [
  { path: '/inventario', name: 'inventario', component: ListaRelojes, meta: { modulo: 'inventario_relojes' } },
  { path: '/inventario/calibres', name: 'calibres', component: CatalogoCalibres, meta: { modulo: 'inventario_relojes' } },
  { path: '/inventario/alertas', name: 'alertas-stock', component: PanelAlertasStock, meta: { modulo: 'inventario_relojes' } },
  {
    path: '/inventario/valor', name: 'valor-inventario', component: ValorInventario,
    meta: { modulo: 'inventario_relojes', roles: ['Gerencia General', 'Gerente de Sucursal', 'Contador'] },
  },
  { path: '/inventario/:serie', name: 'reloj-ficha', component: FichaReloj, meta: { modulo: 'inventario_relojes' } },
]

export default routes
