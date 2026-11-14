<script setup>
/** Campos del formulario de proveedor (dentro de un <FormModal>). v-model = objeto form. */
import { onMounted, ref } from 'vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CheckList from '@/shared/ui/CheckList.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { crearMarcaReloj, listarCondicionesPago, listarMarcasReloj } from '@/configuracion'

const TIPOS = ['relojes', 'piezas_originales', 'piezas_no_originales', 'lubricantes', 'herramientas']
const props = defineProps({
  modelValue: { type: Object, required: true },
  edicion: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const f = props.modelValue
const condiciones = ref([])
const marcas = ref([])

onMounted(async () => {
  ;[condiciones.value, marcas.value] = await Promise.all([
    listarCondicionesPago(true).catch(() => []),
    listarMarcasReloj(true).catch(() => []),
  ])
})
async function nuevaMarca(t) {
  try {
    const m = await crearMarcaReloj({ nombre: t })
    marcas.value.push(m)
    return m
  } catch {
    return null
  }
}
function toggleTipo(tp) {
  const i = f.tipos.indexOf(tp)
  if (i === -1) f.tipos.push(tp)
  else f.tipos.splice(i, 1)
}
</script>

<template>
  <FormField label="Razón social" required wide>
    <input v-model="f.razon_social" class="cr-input" minlength="2" required />
  </FormField>
  <FormField label="Nombre comercial"><input v-model="f.nombre_comercial" class="cr-input" /></FormField>
  <FormField label="RUC / NIT" :helper="edicion ? 'Cambio restringido a rol elevado' : ''">
    <input v-model="f.ruc_nit" class="cr-input" />
  </FormField>
  <FormField label="Contacto"><input v-model="f.contacto_nombre" class="cr-input" /></FormField>
  <FormField label="Teléfono"><input v-model="f.telefono" type="tel" class="cr-input" /></FormField>
  <FormField label="Email" wide><input v-model="f.email" type="email" class="cr-input" /></FormField>

  <FormField
    label="Condición de pago acordada"
    wide
    helper="Plazo de crédito negociado con este proveedor (Contado, 30 días, 50% anticipo…). El medio de pago concreto se elige al registrar cada pago."
  >
    <ComboBox v-model="f.condicion_pago_id" :opciones="condiciones" opcion-label="nombre" opcion-value="id" placeholder="Elegir…" />
  </FormField>

  <FormField label="Tipos que provee" wide>
    <div class="flex flex-wrap gap-1.5">
      <button
        v-for="tp in TIPOS"
        :key="tp"
        type="button"
        class="rounded-full border px-3 py-1 text-xs font-medium capitalize"
        :class="f.tipos.includes(tp) ? 'border-gold bg-gold-pale text-gold-strong' : 'border-hairline text-ink-2 hover:border-gold'"
        @click="toggleTipo(tp)"
      >
        {{ tp.replace(/_/g, ' ') }}
      </button>
    </div>
  </FormField>

  <div class="sm:col-span-2">
    <label class="flex items-center gap-2 text-sm text-ink-2">
      <input v-model="f.certificacion_autorizada" type="checkbox" /> Es distribuidor autorizado de marca
    </label>
    <div v-if="f.certificacion_autorizada" class="mt-2 space-y-2">
      <p class="cr-label">Marcas para las que está autorizado</p>
      <CheckList v-model="f.marcas_autorizadas" :opciones="marcas" opcion-label="nombre" opcion-value="id" />
      <div class="flex items-center gap-2">
        <ComboBox
          :model-value="null" :opciones="marcas" opcion-label="nombre" opcion-value="id"
          placeholder="Buscar o crear marca…" :crear="nuevaMarca" crear-label="Crear marca"
          @update:model-value="(id) => { if (id && !f.marcas_autorizadas.includes(id)) f.marcas_autorizadas.push(id) }"
        />
      </div>
      <p class="flex items-start gap-1.5 rounded-lg bg-warn-bg px-3 py-2 text-xs text-warn">
        <CrIcon name="alert-triangle" :size="13" class="mt-px shrink-0" />
        Adjunta el certificado de distribución autorizada en la pestaña <strong>Documentos</strong> de la ficha del proveedor.
      </p>
    </div>
  </div>

  <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
</template>
