<script setup>
/** Marco centrado para las pantallas de acceso (sin la barra de navegación). */
defineProps({ titulo: { type: String, required: true }, subtitulo: { type: String, default: '' } })
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
    <div class="w-full max-w-sm">
      <div class="mb-6 text-center">
        <p class="serif text-2xl tracking-[0.14em] text-primary-900">CRONOS</p>
        <div class="mx-auto mt-2 h-0.5 w-7 bg-gold"></div>
      </div>
      <div class="cr-card p-6">
        <h1 class="serif text-xl text-ink">{{ titulo }}</h1>
        <p v-if="subtitulo" class="mt-1 text-sm text-ink-2">{{ subtitulo }}</p>
        <div class="mt-5 space-y-4">
          <slot />
        </div>
      </div>
      <slot name="pie" />
    </div>
  </div>
</template>
