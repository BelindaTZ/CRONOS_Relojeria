import RolesMatrixView from '@/rbac/components/RolesMatrixView.vue'

export const routes = [
  { path: '/roles', name: 'roles', component: RolesMatrixView, meta: { soloGerencia: true } },
]

export default routes
