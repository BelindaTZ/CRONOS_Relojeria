import { apiClient } from '@/shared/api/client'

// Plan de cuentas
export const getPlanCuentas = () => apiClient.get('/plan-cuentas')
export const crearCuenta = (datos) => apiClient.post('/plan-cuentas', datos)

// Diario / mayor / balance / estado de resultados
export const listarAsientos = (params) => apiClient.get('/asientos', { params })
export const crearAsiento = (datos) => apiClient.post('/asientos', datos)
export const getMayor = (params) => apiClient.get('/mayor', { params })
export const getBalance = (params) => apiClient.get('/balance', { params })
export const getEstadoResultados = (params) => apiClient.get('/estado-resultados', { params })

// Periodos
export const listarPeriodos = () => apiClient.get('/periodos')
export const crearPeriodo = (datos) => apiClient.post('/periodos', datos)
export const cerrarPeriodo = (id) => apiClient.post(`/periodos/${id}/cerrar`)

// Caja
export const abrirSesionCaja = (sucursalId, saldoInicial) =>
  apiClient.post(`/caja/${sucursalId}/sesiones`, null, { params: { saldo_inicial: saldoInicial } })
export const getSesionActual = (sucursalId) => apiClient.get(`/caja/${sucursalId}/sesiones/actual`)
export const registrarMovimientoCaja = (sucursalId, datos) => apiClient.post(`/caja/${sucursalId}/movimientos`, datos)
export const cerrarSesionCaja = (sucursalId, efectivoContado) =>
  apiClient.post(`/caja/${sucursalId}/sesiones/actual/cerrar`, { efectivo_contado: efectivoContado })

// Cheques
export const listarCheques = (params) => apiClient.get('/cheques', { params })
export const crearCheque = (datos) => apiClient.post('/cheques', datos)
export const protestarCheque = (id) => apiClient.post(`/cheques/${id}/protestar`)

// CxC
export const listarCxc = (params) => apiClient.get('/cxc', { params })
export const registrarCobroCxc = (id, datos) => apiClient.post(`/cxc/${id}/cobros`, datos)
export const getAgingCxc = (params) => apiClient.get('/cxc/aging', { params })
export const getCxcPendientes = () => apiClient.get('/cxc-pendientes')

// Beneficiarios / CxP
export const listarBeneficiarios = (params) => apiClient.get('/beneficiarios', { params })
export const crearBeneficiario = (datos) => apiClient.post('/beneficiarios', datos)
export const listarCxp = (params) => apiClient.get('/cxp', { params })
export const registrarPagoCxp = (id, datos) => apiClient.post(`/cxp/${id}/pagos`, datos)
export const getAgingCxp = (params) => apiClient.get('/cxp/aging', { params })

// Gastos
export const listarGastos = (params) => apiClient.get('/gastos', { params })
export const registrarGasto = (datos, archivo) => {
  const fd = new FormData()
  fd.append('data', JSON.stringify(datos))
  if (archivo) fd.append('soporte', archivo)
  return apiClient.postForm('/gastos', fd)
}
export const confirmarGasto = (id, datos) => apiClient.post(`/gastos/${id}/confirmar`, datos)

// Gastos recurrentes
export const listarGastosRecurrentes = () => apiClient.get('/gastos-recurrentes')
export const crearGastoRecurrente = (datos) => apiClient.post('/gastos-recurrentes', datos)
export const setEstadoGastoRecurrente = (id, estado) => apiClient.put(`/gastos-recurrentes/${id}/estado`, { estado })

// Rentabilidad
export const getRentabilidadSucursal = (params) => apiClient.get('/rentabilidad-sucursal', { params })
