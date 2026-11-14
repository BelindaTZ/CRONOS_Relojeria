import { apiClient } from '@/shared/api/client'

export const listarTransferencias = (params) => apiClient.get('/transferencias', { params })
export const getTransferencia = (id) => apiClient.get(`/transferencias/${id}`)
export const crearTransferencia = (datos) => apiClient.post('/transferencias', datos)
export const enviarTransferencia = (id, responsableEnvioId) =>
  apiClient.post(`/transferencias/${id}/enviar`, { responsable_envio_id: responsableEnvioId ?? null })
export const recibirTransferencia = (id, datos) => apiClient.post(`/transferencias/${id}/recibir`, datos)
export const cancelarTransferencia = (id, motivo) => apiClient.post(`/transferencias/${id}/cancelar`, { motivo })
export const listarDiscrepancias = (id) => apiClient.get(`/transferencias/${id}/discrepancias`)

export const sucursalesActivasTraslado = () => apiClient.get('/transferencias/sucursales-activas')
export const costoReferencialTraslado = () => apiClient.get('/transferencias/costo-referencial')
export const itemsDisponiblesTraslado = (sucursalId, itemTipo, q) =>
  apiClient.get('/transferencias/items-disponibles', {
    params: { sucursal_id: sucursalId, item_tipo: itemTipo, q: q || undefined },
  })
