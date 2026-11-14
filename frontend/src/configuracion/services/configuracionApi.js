import { apiClient } from '@/shared/api/client'

// --- catálogos ---
export const listarMediosPago = () => apiClient.get('/catalogos/medio-pago')
export const crearMedioPago = (nombre) => apiClient.post('/catalogos/medio-pago', { nombre })
export const setActivoMedioPago = (id, activo) => apiClient.put(`/catalogos/medio-pago/${id}/activo`, { activo })

export const listarCategoriasGasto = () => apiClient.get('/catalogos/categoria-gasto')
export const crearCategoriaGasto = (datos) => apiClient.post('/catalogos/categoria-gasto', datos)

export const listarCategoriasMerma = (causa) => apiClient.get('/catalogos/categoria-merma', { params: { causa: causa || undefined } })
export const crearCategoriaMerma = (datos) => apiClient.post('/catalogos/categoria-merma', datos)

export const listarCanalesCita = () => apiClient.get('/catalogos/canal-cita')

// --- catálogos de la ficha de reloj ---
export const listarMarcasReloj = (soloActivas = false) =>
  apiClient.get('/catalogos/marca-reloj', { params: { solo_activas: soloActivas || undefined } })
export const crearMarcaReloj = (datos) => apiClient.post('/catalogos/marca-reloj', datos)
export const actualizarMarcaReloj = (id, datos) => apiClient.patch(`/catalogos/marca-reloj/${id}`, datos)
export const setActivoMarcaReloj = (id, activo) => apiClient.put(`/catalogos/marca-reloj/${id}/activo`, { activo })

export const listarMateriales = (soloActivas = false) =>
  apiClient.get('/catalogos/material', { params: { solo_activas: soloActivas || undefined } })
export const crearMaterial = (nombre) => apiClient.post('/catalogos/material', { nombre })
export const setActivoMaterial = (id, activo) => apiClient.put(`/catalogos/material/${id}/activo`, { activo })

export const listarColores = (soloActivas = false) =>
  apiClient.get('/catalogos/color', { params: { solo_activas: soloActivas || undefined } })
export const crearColor = (datos) => apiClient.post('/catalogos/color', datos)
export const setActivoColor = (id, activo) => apiClient.put(`/catalogos/color/${id}/activo`, { activo })

export const listarCondicionesPago = (soloActivas = false) =>
  apiClient.get('/catalogos/condicion-pago', { params: { solo_activas: soloActivas || undefined } })
export const crearCondicionPago = (datos) => apiClient.post('/catalogos/condicion-pago', datos)
export const setActivoCondicionPago = (id, activo) =>
  apiClient.put(`/catalogos/condicion-pago/${id}/activo`, { activo })

// --- parámetros ---
export const getParametro = (clave) => apiClient.get(`/parametros/${encodeURIComponent(clave)}`)
export const setParametro = (clave, datos) => apiClient.put(`/parametros/${encodeURIComponent(clave)}`, datos)

// --- auditoría ---
export const listarAuditoria = (params) => apiClient.get('/auditoria', { params })
