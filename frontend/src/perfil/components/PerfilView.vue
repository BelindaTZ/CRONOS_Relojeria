<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { useSessionStore } from '@/shared/stores/session'
import { actualizarPerfil, cambiarContrasena, getPerfil } from '@/perfil/services/perfilApi'

const session = useSessionStore()
const router = useRouter()

const perfil = ref(null)
const iniciales = computed(() =>
  (perfil.value?.nombre ?? '?').split(' ').slice(0, 2).map((p) => p[0]).join('').toUpperCase(),
)

async function cargar() {
  perfil.value = await getPerfil()
}
onMounted(cargar)

// --- editar email + foto ---
const edit = reactive({ abierto: false, guardando: false, error: '', email: '', foto: null, fotoPreview: '' })
function abrirEdicion() {
  Object.assign(edit, { abierto: true, guardando: false, error: '', email: perfil.value.email, foto: null, fotoPreview: '' })
}
function onFoto(ev) {
  const f = ev.target.files[0]
  edit.foto = f || null
  edit.fotoPreview = f ? URL.createObjectURL(f) : ''
}
async function guardarEdicion() {
  edit.error = ''
  if (edit.email && !/^\S+@\S+\.\S+$/.test(edit.email)) return (edit.error = 'Correo electrónico inválido.')
  edit.guardando = true
  try {
    perfil.value = await actualizarPerfil({
      email: edit.email !== perfil.value.email ? edit.email : null,
      foto: edit.foto,
    })
    await session.cargarPerfil() // refresca el avatar del navbar
    toast.success('Datos actualizados')
    edit.abierto = false
  } catch (e) {
    edit.error = e.status === 409 ? 'Ese correo ya está en uso por otra cuenta.' : e.message
  } finally {
    edit.guardando = false
  }
}

// --- cambiar contraseña ---
const pass = reactive({ abierto: false, guardando: false, error: '', actual: '', nueva: '', repetir: '' })
function abrirPass() {
  Object.assign(pass, { abierto: true, guardando: false, error: '', actual: '', nueva: '', repetir: '' })
}
async function guardarPass() {
  pass.error = ''
  if (!pass.actual) return (pass.error = 'Ingresa tu contraseña actual.')
  if (pass.nueva.length < 8) return (pass.error = 'La nueva contraseña debe tener al menos 8 caracteres.')
  if (pass.nueva !== pass.repetir) return (pass.error = 'La nueva contraseña y su repetición no coinciden.')
  pass.guardando = true
  try {
    await cambiarContrasena(pass.actual, pass.nueva)
    toast.success('Contraseña cambiada. Vuelve a iniciar sesión.')
    pass.abierto = false
    await session.logout()
    router.push({ name: 'login' })
  } catch (e) {
    pass.error = e.status === 401 || e.status === 422 ? 'La contraseña actual no es correcta.' : e.message
  } finally {
    pass.guardando = false
  }
}
</script>

<template>
  <div v-if="perfil">
    <PageHeader eyebrow="Autoservicio" titulo="Mis datos">
      <template #acciones>
        <button class="cr-btn cr-btn-ghost" @click="abrirPass">Cambiar contraseña</button>
        <button class="cr-btn cr-btn-primary" @click="abrirEdicion">Editar</button>
      </template>
    </PageHeader>

    <div class="grid gap-5 md:grid-cols-3">
      <section class="cr-card flex flex-col items-center p-6 text-center">
        <img
          v-if="perfil.foto_perfil_url"
          :src="perfil.foto_perfil_url"
          alt="Foto de perfil"
          class="h-28 w-28 rounded-full border border-hairline object-cover"
        />
        <span
          v-else
          class="serif grid h-28 w-28 place-items-center rounded-full border border-hairline bg-surface-sunk text-2xl text-ink-3"
        >
          {{ iniciales }}
        </span>
        <p class="serif mt-4 text-lg text-ink">{{ perfil.nombre }}</p>
        <p class="text-sm text-ink-3">{{ perfil.roles.join(', ') || 'Sin rol' }}</p>
      </section>

      <section class="cr-card p-6 md:col-span-2">
        <h2 class="serif text-lg text-ink">Datos de la cuenta</h2>
        <dl class="mt-4 space-y-2.5 text-sm">
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Identificación</dt><dd>{{ perfil.identificacion }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Nombre</dt><dd>{{ perfil.nombre }}</dd></div>
          <div class="flex justify-between gap-4">
            <dt class="text-ink-3">Correo electrónico</dt>
            <dd class="text-ink">{{ perfil.email || '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Rol(es)</dt><dd>{{ perfil.roles.join(', ') || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Sucursal(es)</dt><dd>{{ perfil.sucursales.join(', ') || '—' }}</dd></div>
        </dl>
        <p class="mt-4 flex items-center gap-1.5 border-t border-hairline-soft pt-3 text-xs text-ink-3">
          <CrIcon name="lock" :size="12" />
          Solo puedes cambiar tu correo, tu foto y tu contraseña. Identificación, nombre, rol y sucursales los gestiona Gerencia General.
        </p>
      </section>
    </div>

    <FormModal
      v-model="edit.abierto"
      titulo="Editar mis datos"
      :guardando="edit.guardando"
      ancho="max-w-lg"
      @guardar="guardarEdicion"
    >
      <FormField label="Correo electrónico" wide>
        <input v-model="edit.email" type="email" class="cr-input" autocomplete="email" />
      </FormField>
      <FormField label="Foto de perfil" wide helper="JPG o PNG. Se muestra en tu círculo de perfil y en esta pantalla.">
        <div class="flex items-center gap-3">
          <label class="cr-btn cr-btn-ghost cursor-pointer text-xs">
            <CrIcon name="camera" :size="14" /> Elegir imagen
            <input type="file" accept="image/*" class="hidden" @change="onFoto" />
          </label>
          <img v-if="edit.fotoPreview" :src="edit.fotoPreview" alt="Vista previa" class="h-14 w-14 rounded-full border border-hairline object-cover" />
          <img v-else-if="perfil.foto_perfil_url" :src="perfil.foto_perfil_url" alt="Foto actual" class="h-14 w-14 rounded-full border border-hairline object-cover opacity-60" />
        </div>
      </FormField>
      <p v-if="edit.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ edit.error }}</p>
    </FormModal>

    <FormModal
      v-model="pass.abierto"
      titulo="Cambiar contraseña"
      subtitulo="Se cerrará tu sesión tras el cambio."
      :guardando="pass.guardando"
      guardar-label="Cambiar contraseña"
      ancho="max-w-lg"
      @guardar="guardarPass"
    >
      <FormField label="Contraseña actual" required wide>
        <input v-model="pass.actual" type="password" class="cr-input" autocomplete="current-password" required />
      </FormField>
      <FormField label="Nueva contraseña (mín. 8)" required>
        <input v-model="pass.nueva" type="password" class="cr-input" autocomplete="new-password" minlength="8" required />
      </FormField>
      <FormField label="Repetir nueva contraseña" required>
        <input v-model="pass.repetir" type="password" class="cr-input" autocomplete="new-password" required />
      </FormField>
      <p v-if="pass.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ pass.error }}</p>
    </FormModal>
  </div>
</template>
