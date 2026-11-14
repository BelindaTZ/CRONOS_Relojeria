import { apiClient } from '@/shared/api/client'

export const listarVentas = (params) => apiClient.get('/ventas', { params })
export const getVenta = (id) => apiClient.get(`/ventas/${id}`)
export const crearVenta = (datos) => apiClient.post('/ventas', datos)
export const aplicarDescuentoVenta = (id, datos) => apiClient.post(`/ventas/${id}/descuento`, datos)
export const registrarPagoVenta = (id, datos) => apiClient.post(`/ventas/${id}/pagos`, datos)
export const confirmarVenta = (id, datos) => apiClient.post(`/ventas/${id}/confirmar`, datos || {})
export const anularVenta = (id, motivo) => apiClient.post(`/ventas/${id}/anular`, { motivo })
export const getGarantiasVenta = (id) => apiClient.get(`/ventas/${id}/garantias`)
export const getComprobantesVenta = (id) => apiClient.get(`/ventas/${id}/comprobantes`)
export const enviarFacturaVenta = (id) => apiClient.post(`/ventas/${id}/enviar-factura`)

export const getVentasDia = (params) => apiClient.get('/ventas-dia', { params })
export const listarCuentasPorCobrar = (params) => apiClient.get('/cuentas-por-cobrar', { params })

export const getEmisorFacturacion = () => apiClient.get('/facturacion/emisor')
export const setEmisorFacturacion = (datos) => apiClient.put('/facturacion/emisor', datos)
export const listarPuntosEmision = () => apiClient.get('/facturacion/puntos-emision')
export const setPuntoEmision = (sucursalId, datos) => apiClient.put(`/facturacion/puntos-emision/${sucursalId}`, datos)
