import ListaClientes from '@/clientes/components/ListaClientes.vue'
import FichaCliente from '@/clientes/components/FichaCliente.vue'
import HistorialCliente from '@/clientes/components/HistorialCliente.vue'
import ConfigNivelesView from '@/clientes/components/ConfigNivelesView.vue'
import PanelDescuentos from '@/clientes/components/PanelDescuentos.vue'
import PanelCupones from '@/clientes/components/PanelCupones.vue'
import MargenMinimoView from '@/clientes/components/MargenMinimoView.vue'
import ReportesClientes from '@/clientes/components/ReportesClientes.vue'
import ClientesEnRiesgoView from '@/clientes/components/ClientesEnRiesgoView.vue'

export const routes = [
  { path: '/clientes', name: 'clientes', component: ListaClientes, meta: { modulo: 'clientes_fidelizacion' } },
  { path: '/clientes/niveles', name: 'niveles-fidelizacion', component: ConfigNivelesView, meta: { soloGerencia: true } },
  { path: '/clientes/descuentos', name: 'descuentos', component: PanelDescuentos, meta: { soloGerencia: true } },
  { path: '/clientes/cupones', name: 'cupones', component: PanelCupones, meta: { soloGerencia: true } },
  { path: '/clientes/margen-minimo', name: 'margen-minimo', component: MargenMinimoView, meta: { soloGerencia: true } },
  { path: '/clientes/reportes', name: 'reportes-clientes', component: ReportesClientes, meta: { modulo: 'clientes_fidelizacion' } },
  { path: '/clientes/en-riesgo', name: 'clientes-en-riesgo', component: ClientesEnRiesgoView, meta: { modulo: 'clientes_fidelizacion' } },
  { path: '/clientes/:id', name: 'cliente-ficha', component: FichaCliente, meta: { modulo: 'clientes_fidelizacion' } },
  { path: '/clientes/:id/historial', name: 'cliente-historial', component: HistorialCliente, meta: { modulo: 'clientes_fidelizacion' } },
]

export default routes
