import { apiClient } from '@/shared/api/client'

// --- proveedores ---
export const listarProveedores = (params) => apiClient.get('/proveedores', { params })
export const getProveedor = (id) => apiClient.get(`/proveedores/${id}`)
export const crearProveedor = (datos) => apiClient.post('/proveedores', datos)
export const actualizarProveedor = (id, datos) => apiClient.patch(`/proveedores/${id}`, datos)
export const inactivarProveedor = (id) => apiClient.post(`/proveedores/${id}/inactivar`)
export const calificarProveedor = (id, datos) => apiClient.post(`/proveedores/${id}/calificaciones`, datos)
export const listarDocumentos = (id) => apiClient.get(`/proveedores/${id}/documentos`)
export function subirDocumento(id, tipo, archivo) {
  const fd = new FormData()
  fd.append('tipo', tipo)
  fd.append('archivo', archivo)
  return apiClient.postForm(`/proveedores/${id}/documentos`, fd)
}

// --- órdenes de compra ---
export const listarOrdenes = (params) => apiClient.get('/ordenes-compra', { params })
export const crearOrden = (datos) => apiClient.post('/ordenes-compra', datos)
export const emitirOrden = (id) => apiClient.post(`/ordenes-compra/${id}/emitir`)
export const confirmarOrden = (id) => apiClient.post(`/ordenes-compra/${id}/confirmar`)
export const cancelarOrden = (id, motivo) => apiClient.post(`/ordenes-compra/${id}/cancelar`, { motivo })
export const registrarRecepcion = (id, datos) => apiClient.post(`/ordenes-compra/${id}/recepciones`, datos)
export const corregirOrden = (id, datos) => apiClient.patch(`/ordenes-compra/${id}`, datos)
export const prellenarOrden = (datos) => apiClient.post('/ordenes-compra/prellenar', datos)
export const ultimoPrecio = (params) => apiClient.get('/ordenes-compra/ultimo-precio', { params })

// --- compras programadas ---
export const listarProgramadas = () => apiClient.get('/compras-programadas')
export const crearProgramada = (datos) => apiClient.post('/compras-programadas', datos)
export const setEstadoProgramada = (id, estado) => apiClient.put(`/compras-programadas/${id}/estado`, { estado })
