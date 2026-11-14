import { apiClient } from '@/shared/api/client'

export const listarUsuarios = (params) => apiClient.get('/usuarios', { params })
export const crearUsuario = (datos) => apiClient.post('/usuarios', datos)
export const actualizarUsuario = (id, datos) => apiClient.patch(`/usuarios/${id}`, datos)
export const setRoles = (id, ids) => apiClient.put(`/usuarios/${id}/roles`, { ids })
export const setSucursales = (id, ids) => apiClient.put(`/usuarios/${id}/sucursales`, { ids })
