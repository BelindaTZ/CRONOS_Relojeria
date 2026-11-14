/**
 * Capa de servicios del módulo `health` — única vía de acceso a la API de salud.
 * Módulo PLANTILLA: las features 001+ replican `services/<recurso>Api.js`.
 */
import { apiClient } from '@/shared/api/client'

export async function fetchHealth() {
  // El backend responde 200 (ok) o 503 (degraded); ambos traen el mismo payload.
  try {
    return await apiClient.get('/health')
  } catch (err) {
    if (err.status === 503 && err.data) return err.data
    throw err
  }
}
