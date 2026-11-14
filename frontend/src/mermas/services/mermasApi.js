import { apiClient } from '@/shared/api/client'

export const listarMermas = (params) => apiClient.get('/mermas', { params })
export const getMerma = (id) => apiClient.get(`/mermas/${id}`)
export const crearMerma = (datos, discrepanciaId) =>
  apiClient.post('/mermas', datos, { params: discrepanciaId ? { discrepancia_id: discrepanciaId } : undefined })

export function subirDocumentoMerma(id, tipo, archivo) {
  const fd = new FormData()
  fd.append('tipo', tipo)
  fd.append('archivo', archivo)
  return apiClient.postForm(`/mermas/${id}/documentos`, fd)
}

export const autorizarBaja = (id, datos) => apiClient.post(`/mermas/${id}/autorizar-baja`, datos)
export const cambiarEstadoMerma = (id, estado) => apiClient.post(`/mermas/${id}/estado`, { estado })
export const crearReclamoMerma = (id, datos) => apiClient.post(`/mermas/${id}/reclamo`, datos)
export const actualizarReclamoMerma = (id, datos) => apiClient.patch(`/mermas/${id}/reclamo`, datos)

export const getReporteMermas = (params) => apiClient.get('/reportes/mermas', { params })
