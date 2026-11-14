/**
 * Composable del módulo `health`. Encapsula la carga reactiva del estado de la
 * plataforma. Módulo PLANTILLA: patrón `use<Recurso>()` para las features 001+.
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchHealth } from '@/health/services/healthApi'

export function useHealth({ pollMs = 15000 } = {}) {
  const health = ref(null)
  const loading = ref(false)
  const error = ref(null)
  let timer = null

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      health.value = await fetchHealth()
    } catch (err) {
      error.value = err
      health.value = null
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    refresh()
    if (pollMs > 0) timer = setInterval(refresh, pollMs)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return { health, loading, error, refresh }
}
