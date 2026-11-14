import ListaVentas from '@/ventas/components/ListaVentas.vue'
import NuevaVentaView from '@/ventas/components/NuevaVentaView.vue'
import FichaVenta from '@/ventas/components/FichaVenta.vue'
import VentasDiaView from '@/ventas/components/VentasDiaView.vue'
import CuentasPorCobrarView from '@/ventas/components/CuentasPorCobrarView.vue'
import ConfigFacturacionView from '@/ventas/components/ConfigFacturacionView.vue'

export const routes = [
  { path: '/ventas', name: 'ventas', component: ListaVentas, meta: { modulo: 'ventas' } },
  {
    path: '/ventas/nueva', name: 'venta-nueva', component: NuevaVentaView,
    // La venta la hace el Vendedor (su sucursal se deriva de él, §20.1) — el
    // portal de Gerencia General no lleva "Nueva venta" por delante, aunque
    // conserva el acceso si entra por URL directa (Const. §3, acceso total).
    meta: { modulo: 'ventas', operacion: 'crear', ocultoPortalGerencia: true },
  },
  { path: '/ventas/dia', name: 'ventas-dia', component: VentasDiaView, meta: { modulo: 'ventas' } },
  { path: '/ventas/cuentas-por-cobrar', name: 'cuentas-por-cobrar', component: CuentasPorCobrarView, meta: { modulo: 'ventas' } },
  { path: '/ventas/facturacion/configuracion', name: 'config-facturacion', component: ConfigFacturacionView, meta: { soloGerencia: true } },
  { path: '/ventas/:id', name: 'venta-ficha', component: FichaVenta, meta: { modulo: 'ventas' } },
]

export default routes
