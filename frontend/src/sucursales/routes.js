import SucursalesView from '@/sucursales/components/SucursalesView.vue'

export const routes = [
  { path: '/sucursales', name: 'sucursales', component: SucursalesView, meta: { soloGerencia: true } },
]

export default routes
