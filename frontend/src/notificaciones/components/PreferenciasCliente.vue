<script setup>
/**
 * Opt-out por tipo de comunicación (feature 014, US5). Los tipos operativos
 * críticos (ej. contraseña temporal) no se ofrecen — el backend los rechaza
 * igual, pero no tiene sentido mostrarlos aquí.
 */
import { onMounted, reactive, ref, watch } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { toast } from '@/shared/ui/toast'
import { listarClientes } from '@/clientes'
import { getPreferencias, setPreferencia } from '@/notificaciones/services/notificacionesApi'

const TIPOS = [
  { clave: 'cupon', etiqueta: 'Cupones de descuento' },
  { clave: 'nivel', etiqueta: 'Ascensos de nivel de fidelización' },
  { clave: 'recordatorio_cita', etiqueta: 'Recordatorios de cita' },
  { clave: 'ot_entregado', etiqueta: 'Confirmación de entrega de servicio' },
  { clave: 'diagnostico_cliente', etiqueta: 'Diagnóstico de reparación' },
  { clave: 'servicio_listo_retiro', etiqueta: 'Aviso de servicio listo' },
]

const clientes = ref([])
const clienteId = ref(null)
const prefs = reactive({})
const cargando = ref(false)

onMounted(async () => {
  clientes.value = await listarClientes({ page: 1, size: 100 })
    .then((r) => r.items.map((c) => ({ ...c, _label: `${c.nombre} · ${c.numero_afiliado}` })))
    .catch(() => [])
})

watch(clienteId, async (id) => {
  if (!id) return
  cargando.value = true
  try {
    const lista = await getPreferencias(id)
    const mapa = Object.fromEntries(lista.map((p) => [p.tipo_comunicacion, p.opt_in]))
    TIPOS.forEach((t) => { prefs[t.clave] = mapa[t.clave] ?? true })
  } finally {
    cargando.value = false
  }
})

async function actualizar(tipo, optIn) {
  try {
    await setPreferencia(clienteId.value, { tipo_comunicacion: tipo, opt_in: optIn })
    prefs[tipo] = optIn
    toast.success(optIn ? 'Comunicación reactivada' : 'Cliente excluido de este tipo de correo')
  } catch (e) {
    toast.error(e.message)
  }
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Notificaciones" titulo="Preferencias de comunicación" sub="Opt-out por cliente y tipo de correo — el hecho que dispara el correo (cupón, cita…) se sigue registrando igual." />

    <FormField label="Cliente" wide class="mb-5 max-w-md">
      <ComboBox v-model="clienteId" :opciones="clientes" opcion-label="_label" opcion-value="id" placeholder="Buscar cliente…" />
    </FormField>

    <p v-if="!clienteId" class="rounded-lg bg-surface-sunk px-4 py-6 text-sm text-ink-3">Elige un cliente para ver y editar sus preferencias.</p>
    <p v-else-if="cargando" class="text-sm text-ink-3">Cargando…</p>
    <div v-else class="cr-card divide-y divide-hairline-soft p-0">
      <label v-for="t in TIPOS" :key="t.clave" class="flex items-center justify-between gap-4 px-5 py-3">
        <span class="text-sm text-ink">{{ t.etiqueta }}</span>
        <input type="checkbox" :checked="prefs[t.clave]" @change="actualizar(t.clave, $event.target.checked)" />
      </label>
    </div>
  </div>
</template>
