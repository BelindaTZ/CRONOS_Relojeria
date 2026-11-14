<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthShell from './AuthShell.vue'
import { useSessionStore } from '@/shared/stores/session'

const session = useSessionStore()
const router = useRouter()
const route = useRoute()

const identificacion = ref('')
const password = ref('')
const error = ref('')
const cargando = ref(false)

async function enviar() {
  error.value = ''
  cargando.value = true
  try {
    const r = await session.login(identificacion.value.trim(), password.value)
    if (r.must_change_password) router.push({ name: 'cambiar-contrasena' })
    else router.push(route.query.next || { name: 'inicio' })
  } catch (e) {
    error.value = e.status === 429 ? 'Demasiados intentos. Espera unos minutos.' : 'Identificación o contraseña incorrectas.'
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <AuthShell titulo="Iniciar sesión" subtitulo="Acceso al sistema de gestión">
    <form class="space-y-4" @submit.prevent="enviar">
      <label class="block space-y-1">
        <span class="cr-label">Identificación</span>
        <input v-model="identificacion" class="cr-input" autocomplete="username" required />
      </label>
      <label class="block space-y-1">
        <span class="cr-label">Contraseña</span>
        <input v-model="password" type="password" class="cr-input" autocomplete="current-password" required />
      </label>
      <p v-if="error" class="text-sm text-bad">{{ error }}</p>
      <button class="cr-btn cr-btn-primary w-full" :disabled="cargando" type="submit">
        {{ cargando ? 'Entrando…' : 'Entrar' }}
      </button>
    </form>
    <div class="text-center">
      <RouterLink :to="{ name: 'olvide-contrasena' }" class="text-sm text-gold-strong hover:underline">
        Olvidé mi contraseña
      </RouterLink>
    </div>
  </AuthShell>
</template>
