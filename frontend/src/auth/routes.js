import LoginView from '@/auth/components/LoginView.vue'
import ForgotView from '@/auth/components/ForgotView.vue'
import ChangePasswordView from '@/auth/components/ChangePasswordView.vue'

export const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { publica: true, sinShell: true } },
  { path: '/olvide-contrasena', name: 'olvide-contrasena', component: ForgotView, meta: { publica: true, sinShell: true } },
  {
    path: '/cambiar-contrasena',
    name: 'cambiar-contrasena',
    component: ChangePasswordView,
    meta: { publica: true, sinShell: true },
  },
]

export default routes
