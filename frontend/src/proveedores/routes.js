import ProveedoresView from '@/proveedores/components/ProveedoresView.vue'
import FichaProveedor from '@/proveedores/components/FichaProveedor.vue'
import OrdenesView from '@/proveedores/components/OrdenesView.vue'
import ProgramadasView from '@/proveedores/components/ProgramadasView.vue'

export const routes = [
  { path: '/proveedores', name: 'proveedores', component: ProveedoresView, meta: { modulo: 'proveedores' } },
  { path: '/proveedores/:id', name: 'proveedor-ficha', component: FichaProveedor, meta: { modulo: 'proveedores' } },
  { path: '/compras', name: 'compras', component: OrdenesView, meta: { modulo: 'proveedores' } },
  { path: '/compras/programadas', name: 'compras-programadas', component: ProgramadasView, meta: { modulo: 'proveedores' } },
]

export default routes
