import { apiClient } from '@/shared/api/client'

export const listarPiezas = (params) => apiClient.get('/piezas', { params })
export const getPieza = (id) => apiClient.get(`/piezas/${id}`)
export const crearPieza = (datos) => apiClient.post('/piezas', datos)
export const actualizarPieza = (id, datos) => apiClient.patch(`/piezas/${id}`, datos)
export const inactivarPieza = (id) => apiClient.post(`/piezas/${id}/inactivar`)

export const listarMovimientos = (id, params) => apiClient.get(`/piezas/${id}/movimientos`, { params })
export const registrarMovimiento = (id, datos) => apiClient.post(`/piezas/${id}/movimientos`, datos)
export const listarLotesPieza = (id) => apiClient.get(`/piezas/${id}/lotes`)

export const listarLotesCaducidad = (params) => apiClient.get('/piezas/lotes', { params })
export const valorPiezas = () => apiClient.get('/piezas/valor')
