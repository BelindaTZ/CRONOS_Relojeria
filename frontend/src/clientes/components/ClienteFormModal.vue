<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { listarMarcasReloj } from '@/configuracion'
import {
  actualizarCliente,
  crearCliente,
  getTextoConsentimiento,
} from '@/clientes/services/clientesApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  cliente: { type: Object, default: null }, // si viene, es edición
})
const emit = defineEmits(['update:modelValue', 'guardado'])

function vacio() {
  return {
    tipo: 'natural', identificacion: '', nombre: '', telefono: '', email: '', direccion: '',
    fecha_nacimiento: '', notas: '', marcas: [], consentimiento_aceptado: false,
  }
}
const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')
const marcas = ref([])
const consentimiento = ref({ version: 1, texto: '' })

onMounted(async () => {
  ;[marcas.value, consentimiento.value] = await Promise.all([
    listarMarcasReloj(true).catch(() => []),
    getTextoConsentimiento().catch(() => ({ version: 1, texto: '' })),
  ])
})

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    error.value = ''
    if (props.cliente) {
      Object.assign(f, {
        tipo: props.cliente.tipo,
        identificacion: props.cliente.identificacion,
        nombre: props.cliente.nombre,
        telefono: props.cliente.telefono ?? '',
        email: props.cliente.email ?? '',
        direccion: props.cliente.direccion ?? '',
        fecha_nacimiento: props.cliente.fecha_nacimiento ?? '',
        notas: props.cliente.notas ?? '',
        marcas: [...(props.cliente.preferencias?.marcas || [])],
        consentimiento_aceptado: true,
      })
    } else {
      Object.assign(f, vacio())
    }
  },
)

function toggleMarca(nombre) {
  const s = new Set(f.marcas)
  s.has(nombre) ? s.delete(nombre) : s.add(nombre)
  f.marcas = [...s]
}

async function guardar() {
  error.value = ''
  if (!f.nombre.trim()) return (error.value = 'El nombre / razón social es obligatorio.')
  if (!f.identificacion.trim()) return (error.value = 'La cédula / RUC es obligatoria.')
  if (!props.cliente && !f.consentimiento_aceptado) {
    return (error.value = 'Debes registrar la aceptación del consentimiento de tratamiento de datos.')
  }
  guardando.value = true
  try {
    const payload = {
      tipo: f.tipo,
      identificacion: f.identificacion.trim(),
      nombre: f.nombre.trim(),
      telefono: f.telefono.trim() || null,
      email: f.email.trim() || null,
      direccion: f.direccion.trim() || null,
      fecha_nacimiento: f.fecha_nacimiento || null,
      notas: f.notas.trim() || null,
      preferencias: f.marcas.length ? { marcas: f.marcas } : null,
    }
    let resultado
    if (props.cliente) {
      resultado = await actualizarCliente(props.cliente.id, payload)
      toast.success('Ficha del cliente actualizada')
    } else {
      resultado = await crearCliente({
        ...payload,
        consentimiento: { aceptado: true, version_texto: consentimiento.value.version },
      })
      toast.success(`${f.nombre.trim()} registrado`)
    }
    emit('update:modelValue', false)
    emit('guardado', resultado)
  } catch (e) {
    error.value = e.status === 403 ? 'Corregir la cédula/RUC de un cliente requiere rol elevado.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="cliente ? 'Editar cliente' : 'Nuevo cliente'"
    :guardando="guardando"
    ancho="max-w-2xl"
    :sucio="!!f.nombre"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Tipo">
      <select v-model="f.tipo" class="cr-input">
        <option value="natural">Persona natural</option>
        <option value="juridica">Persona jurídica</option>
      </select>
    </FormField>
    <FormField label="Cédula / RUC" required :helper="cliente ? 'Solo un rol elevado puede corregirla.' : ''">
      <input v-model="f.identificacion" class="cr-input" required />
    </FormField>

    <FormField :label="f.tipo === 'juridica' ? 'Razón social' : 'Nombre completo'" required wide>
      <input v-model="f.nombre" class="cr-input" required />
    </FormField>

    <FormField label="Teléfono"><input v-model="f.telefono" type="tel" class="cr-input" /></FormField>
    <FormField label="Email"><input v-model="f.email" type="email" class="cr-input" /></FormField>
    <FormField label="Dirección" wide helper="Opcional."><input v-model="f.direccion" class="cr-input" /></FormField>
    <FormField label="Fecha de nacimiento" helper="Opcional; habilita el cupón de cumpleaños.">
      <input v-model="f.fecha_nacimiento" type="date" class="cr-input" />
    </FormField>

    <FormField label="Marcas de interés" wide helper="Se usan para segmentar campañas y recomendaciones.">
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="m in marcas"
          :key="m.id"
          type="button"
          class="rounded-full border px-2.5 py-1 text-xs transition"
          :class="f.marcas.includes(m.nombre) ? 'border-gold bg-gold-pale text-gold-strong' : 'border-hairline text-ink-2 hover:border-ink-3'"
          @click="toggleMarca(m.nombre)"
        >{{ m.nombre }}</button>
        <span v-if="!marcas.length" class="text-xs text-ink-3">Registra marcas en Configuración.</span>
      </div>
    </FormField>

    <FormField label="Notas del vendedor" wide>
      <textarea v-model="f.notas" rows="2" class="cr-input"></textarea>
    </FormField>

    <div v-if="!cliente" class="sm:col-span-2 rounded-xl border border-hairline bg-surface-sunk/40 p-3">
      <label class="flex items-start gap-2 text-sm">
        <input v-model="f.consentimiento_aceptado" type="checkbox" class="mt-0.5" required />
        <span>
          <span class="font-medium text-ink">Consentimiento de tratamiento de datos (LOPDP) — versión {{ consentimiento.version }}</span>
          <span class="mt-1 block max-h-28 overflow-y-auto text-xs leading-relaxed text-ink-2">{{ consentimiento.texto }}</span>
        </span>
      </label>
    </div>
    <p v-else class="sm:col-span-2 text-xs text-ink-3">
      <CrIcon name="circle-check" :size="12" class="mr-1 inline text-good" />
      Consentimiento aceptado al alta. La reafirmación se gestiona aparte.
    </p>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
