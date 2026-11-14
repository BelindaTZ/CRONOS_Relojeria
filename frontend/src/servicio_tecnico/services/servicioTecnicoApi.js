import { apiClient } from '@/shared/api/client'

export const listarOrdenesTrabajo = (params) => apiClient.get('/ordenes-trabajo', { params })
export const getOrdenTrabajo = (id) => apiClient.get(`/ordenes-trabajo/${id}`)
export const crearOrdenTrabajo = (datos) => apiClient.post('/ordenes-trabajo', datos)
export const tecnicoSugerido = (numero_serie, sucursal_id) =>
  apiClient.get('/ordenes-trabajo/tecnico-sugerido', { params: { numero_serie, sucursal_id } })
export const relojesElegiblesOt = (q) => apiClient.get('/ordenes-trabajo/relojes-elegibles', { params: { q } })
export const actualizarOrdenTrabajo = (id, datos) => apiClient.patch(`/ordenes-trabajo/${id}`, datos)

export const registrarDiagnostico = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/diagnostico`, datos)
export const registrarTrabajo = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/trabajo`, datos)
export const registrarHoras = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/horas`, datos)
export const crearPresupuesto = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/presupuesto`, datos)
export const aprobarPresupuesto = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/presupuesto/aprobar`, datos)
export const agregarPieza = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/piezas`, datos)
export const solicitarCompraUrgente = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/piezas/solicitar-compra-urgente`, datos)
export const registrarLubricacion = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/lubricacion`, datos)
export const getCosteo = (id) => apiClient.get(`/ordenes-trabajo/${id}/costeo`)
export const aplicarDescuento = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/descuento`, datos)
export const registrarPago = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/pagos`, datos)
export const cambiarEstado = (id, estado) => apiClient.post(`/ordenes-trabajo/${id}/estado`, { estado })
export const entregar = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/entregar`, datos || {})
export const reabrirGarantia = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/reabrir-garantia`, datos)
export const reportarDano = (id, datos) => apiClient.post(`/ordenes-trabajo/${id}/reportar-dano`, datos)
export const getDocumento = (id, tipo) => apiClient.get(`/ordenes-trabajo/${id}/documento/${tipo}`)

export const getOrdenesEnCurso = () => apiClient.get('/ordenes-trabajo-en-curso')
export const getInformeServicios = (params) => apiClient.get('/informe-servicios', { params })
