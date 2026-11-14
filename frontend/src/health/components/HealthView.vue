<script setup>
/**
 * Vista de inicio de la feature 000: confirma visualmente que la plataforma
 * está en pie. Módulo PLANTILLA — demuestra components + composable + service.
 */
import { useHealth } from '@/health/composables/useHealth'

const { health, loading, error, refresh } = useHealth()

const filas = [
  { clave: 'db', etiqueta: 'PostgreSQL' },
  { clave: 'storage', etiqueta: 'MinIO (almacenamiento de objetos)' },
]
</script>

<template>
  <section class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold text-primary-900">Estado de la plataforma</h1>
      <button
        type="button"
        class="rounded-md bg-primary-900 px-3 py-2 text-sm font-semibold text-white hover:bg-primary-800"
        @click="refresh"
      >
        Actualizar
      </button>
    </div>

    <p v-if="loading" class="text-sm text-neutral-500">Comprobando…</p>
    <p v-else-if="error" class="text-sm text-danger-700">
      No se pudo contactar al backend ({{ error.message }}).
    </p>

    <table v-else-if="health" class="w-full overflow-hidden rounded-lg text-sm ring-1 ring-neutral-200">
      <thead class="bg-primary-900 text-primary-50">
        <tr>
          <th class="px-4 py-2 text-left font-semibold">Dependencia</th>
          <th class="px-4 py-2 text-left font-semibold">Estado</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-neutral-200 bg-white">
        <tr v-for="f in filas" :key="f.clave">
          <td class="px-4 py-2 text-neutral-700">{{ f.etiqueta }}</td>
          <td class="px-4 py-2">
            <span
              class="rounded-full px-2 py-0.5 text-xs font-semibold"
              :class="health[f.clave] === 'up' ? 'bg-tertiary-100 text-tertiary-800' : 'bg-danger-100 text-danger-800'"
            >
              {{ health[f.clave] === 'up' ? 'Operativo' : 'Caído' }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>

    <p v-if="health?.version" class="text-xs text-neutral-400">Versión del backend: {{ health.version }}</p>
  </section>
</template>
