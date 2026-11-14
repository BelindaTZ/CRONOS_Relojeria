<script setup>
import { onMounted, reactive, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import {
  getEmisorFacturacion,
  listarPuntosEmision,
  setEmisorFacturacion,
  setPuntoEmision,
} from '@/ventas/services/ventasApi'

const f = reactive({
  razon_social: '', nombre_comercial: '', ruc: '', direccion_matriz: '',
  obligado_contabilidad: true, contribuyente_especial: '', regimen: '', leyenda_pie: '',
})
const puntos = ref([])
const guardando = ref(false)
const guardandoPunto = ref(null)
const error = ref('')

async function cargar() {
  const [emisor, pes] = await Promise.all([getEmisorFacturacion(), listarPuntosEmision()])
  Object.assign(f, {
    razon_social: emisor.razon_social, nombre_comercial: emisor.nombre_comercial || '',
    ruc: emisor.ruc, direccion_matriz: emisor.direccion_matriz || '',
    obligado_contabilidad: emisor.obligado_contabilidad,
    contribuyente_especial: emisor.contribuyente_especial || '', regimen: emisor.regimen || '',
    leyenda_pie: emisor.leyenda_pie || '',
  })
  puntos.value = pes.map((p) => ({ ...p }))
}
onMounted(cargar)

async function guardarEmisor() {
  error.value = ''
  if (f.razon_social.trim().length < 2) return (error.value = 'La razón social es obligatoria.')
  if (f.ruc.trim().length < 10) return (error.value = 'El RUC no es válido.')
  guardando.value = true
  try {
    await setEmisorFacturacion({
      razon_social: f.razon_social.trim(), nombre_comercial: f.nombre_comercial.trim() || null,
      ruc: f.ruc.trim(), direccion_matriz: f.direccion_matriz.trim() || null,
      obligado_contabilidad: f.obligado_contabilidad,
      contribuyente_especial: f.contribuyente_especial.trim() || null,
      regimen: f.regimen.trim() || null, leyenda_pie: f.leyenda_pie.trim() || null,
    })
    toast.success('Datos del emisor actualizados')
  } catch (e) {
    error.value = e.message
  } finally {
    guardando.value = false
  }
}

async function guardarPunto(p) {
  guardandoPunto.value = p.sucursal_id
  try {
    const r = await setPuntoEmision(p.sucursal_id, {
      establecimiento_codigo: p.establecimiento_codigo, punto_emision_codigo: p.punto_emision_codigo,
      direccion_establecimiento: p.direccion_establecimiento || null,
    })
    Object.assign(p, r)
    toast.success(`Punto de emisión de ${p.sucursal_nombre} guardado`)
  } catch (e) {
    toast.error(e.message)
  } finally {
    guardandoPunto.value = null
  }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Sistema"
      titulo="Facturación"
      sub="Datos del emisor y numeración de la factura (formato tipo SRI: establecimiento-punto de emisión-secuencial). Sin autorización real del SRI en esta fase."
    >
      <template #acciones>
        <button class="cr-btn cr-btn-primary" :disabled="guardando" @click="guardarEmisor">
          {{ guardando ? 'Guardando…' : 'Guardar datos del emisor' }}
        </button>
      </template>
    </PageHeader>

    <section class="cr-card p-6">
      <h2 class="serif text-lg text-ink">Datos del emisor</h2>
      <div class="mt-4 grid gap-4 sm:grid-cols-2">
        <FormField label="Razón social" required>
          <input v-model="f.razon_social" class="cr-input" />
        </FormField>
        <FormField label="Nombre comercial">
          <input v-model="f.nombre_comercial" class="cr-input" />
        </FormField>
        <FormField label="RUC" required>
          <input v-model="f.ruc" class="cr-input tabular-nums" maxlength="13" />
        </FormField>
        <FormField label="Régimen" helper="Ej. RIMPE, General…">
          <input v-model="f.regimen" class="cr-input" />
        </FormField>
        <FormField label="Dirección matriz" wide>
          <input v-model="f.direccion_matriz" class="cr-input" />
        </FormField>
        <FormField label="Obligado a llevar contabilidad">
          <select v-model="f.obligado_contabilidad" class="cr-input">
            <option :value="true">Sí</option>
            <option :value="false">No</option>
          </select>
        </FormField>
        <FormField label="Contribuyente especial" helper="N.º de resolución, o vacío si no aplica.">
          <input v-model="f.contribuyente_especial" class="cr-input" />
        </FormField>
        <FormField label="Leyenda al pie" wide helper="Texto legal adicional en la factura.">
          <input v-model="f.leyenda_pie" class="cr-input" />
        </FormField>
      </div>
      <p v-if="error" class="mt-3 text-sm text-bad" role="alert">{{ error }}</p>
    </section>

    <section class="cr-card mt-5 p-6">
      <h2 class="serif text-lg text-ink">Puntos de emisión por sucursal</h2>
      <p class="mt-1 text-sm text-ink-3">Cada sucursal factura con su propio establecimiento/punto y secuencial. El secuencial avanza solo (no editable).</p>
      <div class="mt-4 overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-table-head-border bg-surface-head text-left">
              <th class="px-3 py-2 font-medium">Sucursal</th>
              <th class="px-3 py-2 font-medium">Establecimiento</th>
              <th class="px-3 py-2 font-medium">Punto de emisión</th>
              <th class="px-3 py-2 font-medium">Dirección del establecimiento</th>
              <th class="px-3 py-2 text-right font-medium">Secuencial actual</th>
              <th class="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in puntos" :key="p.sucursal_id" class="border-b border-hairline-soft">
              <td class="px-3 py-2 font-medium text-ink">{{ p.sucursal_nombre }}</td>
              <td class="px-3 py-2"><input v-model="p.establecimiento_codigo" class="cr-input w-20 tabular-nums" maxlength="3" /></td>
              <td class="px-3 py-2"><input v-model="p.punto_emision_codigo" class="cr-input w-20 tabular-nums" maxlength="3" /></td>
              <td class="px-3 py-2"><input v-model="p.direccion_establecimiento" class="cr-input" /></td>
              <td class="px-3 py-2 text-right tabular-nums text-ink-3">{{ p.secuencial_actual }}</td>
              <td class="px-3 py-2">
                <button class="cr-btn cr-btn-ghost text-xs" :disabled="guardandoPunto === p.sucursal_id" @click="guardarPunto(p)">
                  <CrIcon name="check" :size="13" /> Guardar
                </button>
              </td>
            </tr>
            <tr v-if="!puntos.length"><td colspan="6" class="px-3 py-6 text-center text-ink-3">Sin sucursales configuradas.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
