import { apiClient } from '@/shared/api/client'

export const listarCitas = (params) => apiClient.get('/citas', { params })
export const getCita = (id) => apiClient.get(`/citas/${id}`)
export const crearCita = (datos) => apiClient.post('/citas', datos)
export const actualizarCita = (id, datos) => apiClient.patch(`/citas/${id}`, datos)
export const getHistorialCita = (id) => apiClient.get(`/citas/${id}/historial`)

export const confirmarCita = (id, datos) => apiClient.post(`/citas/${id}/confirmar`, datos || {})
export const cancelarCita = (id, motivo) => apiClient.post(`/citas/${id}/cancelar`, { motivo })
export const atenderCita = (id, datos) => apiClient.post(`/citas/${id}/atender`, datos || {})

export const getAgenda = (params) => apiClient.get('/agenda', { params })
export const getConversionCitas = (params) => apiClient.get('/citas/conversion', { params })
