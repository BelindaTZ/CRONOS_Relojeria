import { apiClient } from '@/shared/api/client'

export const listarRoles = () => apiClient.get('/roles')
export const crearRol = (datos) => apiClient.post('/roles', datos)
export const listarModulos = () => apiClient.get('/modulos')
export const getPermisos = (rolId) => apiClient.get(`/roles/${rolId}/permisos`)
export const setPermisos = (rolId, entradas) => apiClient.put(`/roles/${rolId}/permisos`, entradas)
