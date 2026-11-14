import { apiClient } from '@/shared/api/client'

export const getPanel = (params) => apiClient.get('/panel', { params })
export const getIndiceReportes = () => apiClient.get('/reportes/indice')
export const getReporteAnalitico = (slug, params) => apiClient.get(`/reportes/analitico/${encodeURIComponent(slug)}`, { params })

// feature 012 — sello de frescura del warehouse + disparo manual del DAG.
export const getEstadoFrescura = () => apiClient.get('/reportes/estado-frescura')
export const actualizarAhora = () => apiClient.post('/reportes/actualizar-ahora')
