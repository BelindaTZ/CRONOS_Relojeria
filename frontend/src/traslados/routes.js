import ListaTransferencias from '@/traslados/components/ListaTransferencias.vue'

export const routes = [
  { path: '/traslados', name: 'traslados', component: ListaTransferencias, meta: { modulo: 'multisucursal' } },
]

export default routes
