import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { conectarSesionAlCliente } from '@/shared/stores/session'
import './shared/styles/main.css'

const pinia = createPinia()
conectarSesionAlCliente(pinia)

createApp(App).use(pinia).use(router).mount('#app')
