import { apiClient } from '@/shared/api/client'

// --- clientes ---
export const listarClientes = (params) => apiClient.get('/clientes', { params })
export const getCliente = (id) => apiClient.get(`/clientes/${id}`)
export const crearCliente = (datos) => apiClient.post('/clientes', datos)
export const actualizarCliente = (id, datos) => apiClient.patch(`/clientes/${id}`, datos)
export const setEstadoCliente = (id, estado) => apiClient.put(`/clientes/${id}/estado`, { estado })
export const getHistorialCliente = (id) => apiClient.get(`/clientes/${id}/historial`)
export const getTextoConsentimiento = () => apiClient.get('/clientes/texto-consentimiento')

// --- niveles de fidelización ---
export const listarNiveles = () => apiClient.get('/niveles')
export const crearNivel = (datos) => apiClient.post('/niveles', datos)
export const setReglaNivel = (id, datos) => apiClient.put(`/niveles/${id}/regla`, datos)

// --- descuentos ---
export const listarDescuentos = () => apiClient.get('/descuentos')
export const crearDescuento = (datos) => apiClient.post('/descuentos', datos)
export const actualizarDescuento = (id, datos) => apiClient.patch(`/descuentos/${id}`, datos)

// --- cupones ---
export const listarCupones = (params) => apiClient.get('/cupones', { params })
export const crearCupon = (datos) => apiClient.post('/cupones', datos)

// --- margen mínimo ---
export const getMargenMinimo = (params) => apiClient.get('/margen-minimo', { params })
export const setMargenMinimo = (datos) => apiClient.put('/margen-minimo', datos)

// --- reportes ---
export const reporteClientesPorNivel = () => apiClient.get('/reportes/clientes-por-nivel')
export const reporteMejoresClientes = (params) => apiClient.get('/reportes/mejores-clientes', { params })
export const reporteClientesEnRiesgo = () => apiClient.get('/reportes/clientes-en-riesgo')
export const emitirCuponReactivacion = (datos) => apiClient.post('/cupones/reactivacion', datos)
