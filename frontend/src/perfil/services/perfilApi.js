import { apiClient } from '@/shared/api/client'

export const getPerfil = () => apiClient.get('/perfil')

export function actualizarPerfil({ email, foto }) {
  const fd = new FormData()
  if (email) fd.append('email', email)
  if (foto) fd.append('foto', foto)
  return apiClient.patchForm('/perfil', fd)
}

export const cambiarContrasena = (actual, nueva) =>
  apiClient.post('/auth/cambiar-contrasena', { actual, nueva })
