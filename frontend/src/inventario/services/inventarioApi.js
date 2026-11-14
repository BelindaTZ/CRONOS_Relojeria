import { apiClient } from '@/shared/api/client'

// --- relojes ---
export const listarRelojes = (params) => apiClient.get('/relojes', { params })
export const getReloj = (serie) => apiClient.get(`/relojes/${encodeURIComponent(serie)}`)
export const historialSerie = (serie) => apiClient.get(`/relojes/${encodeURIComponent(serie)}/historial`)
export const corregirReloj = (id, datos) => apiClient.patch(`/relojes/${id}`, datos)
export const lineasPendientesRecepcion = () => apiClient.get('/relojes/pendientes-recepcion')
// Búsqueda SIN restricción de sucursal — para que el vendedor localice un modelo
// disponible en otra sucursal y, si aplica, inicie un traslado (spec §4.1/§4.4).
export const buscarDisponibilidadGlobal = (params) => apiClient.get('/relojes/buscar-global', { params })

export function crearReloj(ficha, foto) {
  const fd = new FormData()
  fd.append('data', JSON.stringify(ficha))
  if (foto) fd.append('foto', foto)
  return apiClient.postForm('/relojes', fd)
}
export function agregarFoto(id, foto) {
  const fd = new FormData()
  fd.append('foto', foto)
  return apiClient.postForm(`/relojes/${id}/fotos`, fd)
}
export function agregarDocumentoReloj(id, tipo, archivo) {
  const fd = new FormData()
  fd.append('tipo', tipo)
  fd.append('archivo', archivo)
  return apiClient.postForm(`/relojes/${id}/documentos`, fd)
}

// --- calibres ---
export const listarCalibres = (q) => apiClient.get('/calibres', { params: { q: q || undefined } })
export const crearCalibre = (datos) => apiClient.post('/calibres', datos)

// --- alertas / valor ---
export const listarAlertasStock = (params) => apiClient.get('/alertas-stock', { params })
export const valorInventario = (sucursalId) =>
  apiClient.get('/valor-inventario', { params: { sucursal_id: sucursalId || undefined } })
