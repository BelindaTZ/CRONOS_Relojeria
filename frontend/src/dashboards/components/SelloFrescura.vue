<script setup>
/**
 * "Actualizado a HH:MM" — consume el estado de frescura del warehouse (012) y
 * ofrece el disparo manual ("Actualizar ahora") de una corrida del DAG.
 */
import { onMounted, ref } from 'vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { actualizarAhora, getEstadoFrescura } from '@/dashboards/services/dashboardsApi'

const estado = ref({ cargando: true, disponible: false, masReciente: null })
const actualizando = ref(false)

function _masReciente(dominios) {
  let top = null
  for (const d of dominios || []) {
    if (d.ultima_carga_ts && (!top || d.ultima_carga_ts > top)) top = d.ultima_carga_ts
  }
  return top
}

async function cargar() {
  estado.value.cargando = true
  try {
    const r = await getEstadoFrescura()
    estado.value = { cargando: false, disponible: r.disponible, masReciente: _masReciente(r.dominios) }
  } catch {
    estado.value = { cargando: false, disponible: false, masReciente: null }
  }
}

async function disparar() {
  actualizando.value = true
  try {
    await actualizarAhora()
    toast.success('Corrida disparada — los datos se actualizarán en unos minutos')
    setTimeout(cargar, 4000)
  } catch (e) {
    toast.error(e.status === 409 ? 'Ya hay una corrida en curso' : e.status === 503 ? 'El orquestador no está disponible' : e.message)
  } finally {
    actualizando.value = false
  }
}

function horaTexto(iso) {
  if (!iso) return null
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

onMounted(cargar)
</script>

<template>
  <div class="flex items-center gap-2 text-xs text-ink-3">
    <template v-if="estado.cargando">
      <span class="h-3 w-24 animate-pulse rounded bg-surface-sunk"></span>
    </template>
    <template v-else-if="estado.disponible && estado.masReciente">
      <CrIcon name="clock" :size="13" />
      <span>Actualizado a las {{ horaTexto(estado.masReciente) }}</span>
    </template>
    <template v-else>
      <CrIcon name="alert-circle" :size="13" class="text-warn" />
      <span>Datos analíticos no disponibles</span>
    </template>
    <button type="button" class="cr-btn cr-btn-ghost !py-1 !px-2 text-xs" :disabled="actualizando" @click="disparar">
      <CrIcon name="refresh-cw" :size="12" :class="{ 'animate-spin': actualizando }" /> Actualizar ahora
    </button>
  </div>
</template>
