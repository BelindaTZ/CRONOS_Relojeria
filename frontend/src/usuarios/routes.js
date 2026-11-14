import UsuariosView from '@/usuarios/components/UsuariosView.vue'

export const routes = [
  { path: '/usuarios', name: 'usuarios', component: UsuariosView, meta: { soloGerencia: true } },
]

export default routes
