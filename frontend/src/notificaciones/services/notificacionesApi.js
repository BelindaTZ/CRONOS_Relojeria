import { apiClient } from '@/shared/api/client'

export const listarEnvios = (params) => apiClient.get('/envios', { params })
export const reintentarEnvio = (id) => apiClient.post(`/envios/${id}/reintentar`)

export const getPreferencias = (clienteId) => apiClient.get(`/preferencias/cliente/${clienteId}`)
export const setPreferencia = (clienteId, datos) => apiClient.put(`/preferencias/cliente/${clienteId}`, datos)

export const listarPlantillas = () => apiClient.get('/plantillas')
export const getPlantilla = (tipo) => apiClient.get(`/plantillas/${encodeURIComponent(tipo)}`)
export const setPlantilla = (tipo, datos) => apiClient.put(`/plantillas/${encodeURIComponent(tipo)}`, datos)
export const previewPlantilla = (tipo, contexto) => apiClient.post(`/plantillas/${encodeURIComponent(tipo)}/preview`, { contexto })
