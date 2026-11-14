import { apiClient } from '@/shared/api/client'

// --- técnicos ---
export const listarTecnicos = (params) => apiClient.get('/tecnicos', { params })
export const getTecnico = (id) => apiClient.get(`/tecnicos/${id}`)
export const crearTecnico = (datos) => apiClient.post('/tecnicos', datos)
export const actualizarTecnico = (id, datos) => apiClient.patch(`/tecnicos/${id}`, datos)
export const setEstadoTecnico = (id, estado) => apiClient.put(`/tecnicos/${id}/estado`, { estado })
export const fijarCosto = (id, datos) => apiClient.post(`/tecnicos/${id}/costo`, datos)

// --- especialidades ---
export const listarEspecialidades = () => apiClient.get('/tecnicos/especialidades')
export const crearEspecialidad = (nombre) =>
  apiClient.post('/tecnicos/especialidades', undefined, { params: { nombre } })

// --- reglas de bono ---
export const listarReglasBono = () => apiClient.get('/reglas-bono')
export const crearReglaBono = (datos) => apiClient.post('/reglas-bono', datos)

// --- periodos + bonos ---
export const listarPeriodos = () => apiClient.get('/periodos-liquidacion')
export const crearPeriodo = (datos) => apiClient.post('/periodos-liquidacion', datos)
export const cerrarPeriodo = (id) => apiClient.post(`/periodos-liquidacion/${id}/cerrar`)
export const calcularBono = (datos) => apiClient.post('/bonos/calcular', datos)
export const listarBonos = (params) => apiClient.get('/bonos', { params })

// --- productividad ---
export const listarProductividad = (params) => apiClient.get('/productividad', { params })
