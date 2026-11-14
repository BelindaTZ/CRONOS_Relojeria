import PlanCuentas from '@/contabilidad/components/PlanCuentas.vue'
import LibroDiario from '@/contabilidad/components/LibroDiario.vue'
import BalanceComprobacion from '@/contabilidad/components/BalanceComprobacion.vue'
import EstadoResultados from '@/contabilidad/components/EstadoResultados.vue'
import PanelCaja from '@/contabilidad/components/PanelCaja.vue'
import ListaCheques from '@/contabilidad/components/ListaCheques.vue'
import AgingCxcView from '@/contabilidad/components/AgingCxcView.vue'
import AgingCxpView from '@/contabilidad/components/AgingCxpView.vue'
import PanelGastos from '@/contabilidad/components/PanelGastos.vue'
import GastosRecurrentesView from '@/contabilidad/components/GastosRecurrentesView.vue'
import RentabilidadSucursalView from '@/contabilidad/components/RentabilidadSucursalView.vue'

export const routes = [
  { path: '/contabilidad/plan-cuentas', name: 'plan-cuentas', component: PlanCuentas, meta: { modulo: 'contable' } },
  { path: '/contabilidad/libro-diario', name: 'libro-diario', component: LibroDiario, meta: { modulo: 'contable' } },
  { path: '/contabilidad/balance-comprobacion', name: 'balance-comprobacion', component: BalanceComprobacion, meta: { modulo: 'contable' } },
  { path: '/contabilidad/estado-resultados', name: 'estado-resultados', component: EstadoResultados, meta: { modulo: 'contable' } },
  { path: '/contabilidad/caja', name: 'caja', component: PanelCaja, meta: { modulo: 'contable' } },
  { path: '/contabilidad/cheques', name: 'cheques', component: ListaCheques, meta: { modulo: 'contable' } },
  { path: '/contabilidad/cuentas-por-cobrar', name: 'aging-cxc', component: AgingCxcView, meta: { modulo: 'contable' } },
  { path: '/contabilidad/cuentas-por-pagar', name: 'aging-cxp', component: AgingCxpView, meta: { modulo: 'contable' } },
  { path: '/contabilidad/gastos', name: 'gastos', component: PanelGastos, meta: { modulo: 'contable' } },
  { path: '/contabilidad/gastos/recurrentes', name: 'gastos-recurrentes', component: GastosRecurrentesView, meta: { modulo: 'contable' } },
  { path: '/contabilidad/rentabilidad-sucursal', name: 'rentabilidad-sucursal', component: RentabilidadSucursalView, meta: { modulo: 'contable' } },
]

export default routes
