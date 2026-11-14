<script setup>
import { ref } from 'vue'
import AuthShell from './AuthShell.vue'
import { apiClient } from '@/shared/api/client'

const identificacion = ref('')
const enviado = ref(false)
const cargando = ref(false)

async function enviar() {
  cargando.value = true
  try {
    await apiClient.post('/auth/olvide-contrasena', { identificacion: identificacion.value.trim() })
  } catch {
    /* la respuesta es siempre neutra */
  } finally {
    cargando.value = false
    enviado.value = true
  }
}
</script>

<template>
  <AuthShell titulo="Restablecer contraseña" subtitulo="Te enviaremos una contraseña temporal al correo registrado">
    <template v-if="!enviado">
      <form class="space-y-4" @submit.prevent="enviar">
        <label class="block space-y-1">
          <span class="cr-label">Identificación</span>
          <input v-model="identificacion" class="cr-input" required />
        </label>
        <button class="cr-btn cr-btn-primary w-full" :disabled="cargando" type="submit">
          {{ cargando ? 'Enviando…' : 'Enviar' }}
        </button>
      </form>
    </template>
    <p v-else class="text-sm text-ink-2">
      Si la identificación corresponde a un usuario activo, se ha enviado una contraseña temporal a su
      correo. Es de un solo uso y caduca en 24 horas.
    </p>
    <div class="text-center">
      <RouterLink :to="{ name: 'login' }" class="text-sm text-gold-strong hover:underline">
        Volver a iniciar sesión
      </RouterLink>
    </div>
  </AuthShell>
</template>
