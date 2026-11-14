<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthShell from './AuthShell.vue'
import { useSessionStore } from '@/shared/stores/session'

const session = useSessionStore()
const router = useRouter()

const actual = ref('')
const nueva = ref('')
const repetir = ref('')
const error = ref('')
const cargando = ref(false)

async function enviar() {
  error.value = ''
  if (nueva.value.length < 8) return (error.value = 'La nueva contraseña debe tener al menos 8 caracteres.')
  if (nueva.value !== repetir.value) return (error.value = 'Las contraseñas no coinciden.')
  cargando.value = true
  try {
    await session.cambiarContrasena(actual.value, nueva.value)
    router.push({ name: 'login' })
  } catch (e) {
    error.value = e.message || 'No se pudo cambiar la contraseña.'
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <AuthShell
    titulo="Fija una contraseña nueva"
    subtitulo="Tu acceso actual es temporal. Debes cambiarlo antes de continuar."
  >
    <form class="space-y-4" @submit.prevent="enviar">
      <label class="block space-y-1">
        <span class="cr-label">Contraseña actual (la temporal)</span>
        <input v-model="actual" type="password" class="cr-input" autocomplete="current-password" required />
      </label>
      <label class="block space-y-1">
        <span class="cr-label">Nueva contraseña</span>
        <input v-model="nueva" type="password" class="cr-input" autocomplete="new-password" required />
      </label>
      <label class="block space-y-1">
        <span class="cr-label">Repetir nueva contraseña</span>
        <input v-model="repetir" type="password" class="cr-input" autocomplete="new-password" required />
      </label>
      <p v-if="error" class="text-sm text-bad">{{ error }}</p>
      <button class="cr-btn cr-btn-primary w-full" :disabled="cargando" type="submit">
        {{ cargando ? 'Guardando…' : 'Guardar y continuar' }}
      </button>
    </form>
  </AuthShell>
</template>
