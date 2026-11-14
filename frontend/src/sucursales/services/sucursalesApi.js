import { apiClient } from '@/shared/api/client'

export const listarSucursales = (params) => apiClient.get('/sucursales', { params: params || undefined })
export const crearSucursal = (datos) => apiClient.post('/sucursales', datos)
export const inactivarSucursal = (id, motivo) => apiClient.post(`/sucursales/${id}/inactivar`, { motivo })
export const getHorarioSucursal = (id) => apiClient.get(`/sucursales/${id}/horario`)
export const setHorarioSucursal = (id, dias) => apiClient.put(`/sucursales/${id}/horario`, dias)
