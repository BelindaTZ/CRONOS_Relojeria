import PanelEnvios from '@/notificaciones/components/PanelEnvios.vue'
import EditorPlantilla from '@/notificaciones/components/EditorPlantilla.vue'
import PreferenciasCliente from '@/notificaciones/components/PreferenciasCliente.vue'

export const routes = [
  { path: '/notificaciones/envios', name: 'notificaciones-envios', component: PanelEnvios, meta: { modulo: 'notificaciones', operacion: 'consultar' } },
  { path: '/notificaciones/plantillas', name: 'notificaciones-plantillas', component: EditorPlantilla, meta: { soloGerencia: true } },
  { path: '/notificaciones/preferencias', name: 'notificaciones-preferencias', component: PreferenciasCliente, meta: { modulo: 'notificaciones', operacion: 'consultar' } },
]

export default routes
