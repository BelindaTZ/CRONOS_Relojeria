<script setup>
/** Raíz. Monta <DialogHost> y <ToastHost> una sola vez (Principio XI). Las
 * pantallas de acceso (`meta.sinShell`) se pintan sin la barra de navegación. */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from '@/shared/ui/AppShell.vue'
import DialogHost from '@/shared/ui/DialogHost.vue'
import ToastHost from '@/shared/ui/ToastHost.vue'

const route = useRoute()
const conShell = computed(() => !route.meta.sinShell)
</script>

<template>
  <AppShell v-if="conShell">
    <RouterView />
  </AppShell>
  <RouterView v-else />
  <DialogHost />
  <ToastHost />
</template>
