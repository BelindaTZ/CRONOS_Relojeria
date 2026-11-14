import { apiClient } from '@/shared/api/client'

export const listarProductosMoebius = () => apiClient.get('/productos-moebius')
export const crearProductoMoebius = (datos) => apiClient.post('/productos-moebius', datos)
export const getFichaLubricacion = (calibreId) => apiClient.get(`/calibres/${calibreId}/ficha-lubricacion`)
export const setFichaLubricacion = (calibreId, datos) =>
  apiClient.put(`/calibres/${calibreId}/ficha-lubricacion`, datos)
export const getDesviacionLubricacion = (params) =>
  apiClient.get('/reportes/desviacion-lubricacion', { params })
