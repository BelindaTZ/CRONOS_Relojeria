<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import { listarCategoriasGasto } from '@/configuracion'
import { crearBeneficiario, listarBeneficiarios, registrarGasto } from '@/contabilidad/services/contabilidadApi'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'guardado'])

function vacio() {
  return {
    sucursal_id: null, categoria_gasto_id: null, monto: null, fecha: new Date().toISOString().slice(0, 10),
    descripcion: '', estado_pago: 'pagado', medio_pago: 'efectivo', beneficiario_id: null,
  }
}
const f = reactive(vacio())
const archivo = ref(null)
const sucursales = ref([])
const categorias = ref([])
const beneficiarios = ref([])
const guardando = ref(false)
const error = ref('')

onMounted(async () => {
  ;[sucursales.value, categorias.value, beneficiarios.value] = await Promise.all([
    listarSucursales().then((r) => r.items).catch(() => []),
    listarCategoriasGasto().catch(() => []),
    listarBeneficiarios().catch(() => []),
  ])
})
watch(() => props.modelValue, (v) => { if (v) { Object.assign(f, vacio()); archivo.value = null; error.value = '' } })

async function nuevoBeneficiario(nombre) {
  try {
    const b = await crearBeneficiario({ nombre, identificacion: null, tipo_servicio: null })
    beneficiarios.value.push(b)
    return b
  } catch (e) {
    toast.error(e.message)
    return null
  }
}

function onArchivo(e) { archivo.value = e.target.files?.[0] || null }

async function guardar() {
  error.value = ''
  if (!f.sucursal_id) return (error.value = 'Selecciona la sucursal.')
  if (!f.categoria_gasto_id) return (error.value = 'Selecciona la categoría.')
  if (!f.monto || Number(f.monto) <= 0) return (error.value = 'Indica el monto.')
  if (f.estado_pago === 'pagado' && !f.medio_pago) return (error.value = 'Indica el medio de pago.')
  if (f.estado_pago === 'por_pagar' && !f.beneficiario_id) return (error.value = 'Elige el beneficiario o proveedor.')
  guardando.value = true
  try {
    await registrarGasto({
      sucursal_id: f.sucursal_id, categoria_gasto_id: f.categoria_gasto_id, monto: Number(f.monto),
      fecha: f.fecha, descripcion: f.descripcion.trim() || null, estado_pago: f.estado_pago,
      medio_pago: f.estado_pago === 'pagado' ? f.medio_pago : null,
      beneficiario_id: f.estado_pago === 'por_pagar' ? f.beneficiario_id : null,
    }, archivo.value)
    toast.success('Gasto registrado')
    emit('update:modelValue', false)
    emit('guardado')
  } catch (e) {
    error.value = e.status === 403 ? 'El registro de gastos requiere Gerencia General o Contador.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    titulo="Registrar gasto"
    subtitulo="Atribuido a una sucursal y una categoría. Pagado ahora genera un movimiento de caja; por pagar genera una cuenta por pagar."
    :guardando="guardando"
    ancho="max-w-2xl"
    :sucio="!!f.monto"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Sucursal" required>
      <select v-model="f.sucursal_id" class="cr-input">
        <option :value="null">Elige…</option>
        <option v-for="s in sucursales" :key="s.id" :value="s.id">{{ s.nombre }}</option>
      </select>
    </FormField>
    <FormField label="Categoría" required>
      <select v-model="f.categoria_gasto_id" class="cr-input">
        <option :value="null">Elige…</option>
        <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
      </select>
    </FormField>
    <FormField label="Monto" required>
      <input v-model="f.monto" type="number" step="0.01" min="0.01" class="cr-input tabular-nums" />
    </FormField>
    <FormField label="Fecha" required>
      <input v-model="f.fecha" type="date" class="cr-input" />
    </FormField>
    <FormField label="Descripción" wide>
      <input v-model="f.descripcion" class="cr-input" placeholder="Ej. Arriendo de septiembre" />
    </FormField>

    <FormField label="¿Cómo se paga?" wide>
      <div class="flex gap-4 text-sm">
        <label class="flex items-center gap-1"><input v-model="f.estado_pago" type="radio" value="pagado" /> Pagado ahora</label>
        <label class="flex items-center gap-1"><input v-model="f.estado_pago" type="radio" value="por_pagar" /> Por pagar</label>
      </div>
    </FormField>
    <FormField v-if="f.estado_pago === 'pagado'" label="Medio de pago" required>
      <select v-model="f.medio_pago" class="cr-input">
        <option value="efectivo">Efectivo</option>
        <option value="transferencia">Transferencia</option>
        <option value="cheque">Cheque</option>
        <option value="tarjeta">Tarjeta</option>
      </select>
    </FormField>
    <FormField v-else label="Beneficiario / proveedor" required helper="Acreedor del servicio (EMAPA, CNT…) o un proveedor registrado.">
      <ComboBox
        v-model="f.beneficiario_id" :opciones="beneficiarios" opcion-label="nombre" opcion-value="id"
        placeholder="Buscar o crear…" :crear="nuevoBeneficiario" crear-label="Crear beneficiario"
      />
    </FormField>

    <FormField label="Documento de soporte" wide helper="Factura, recibo o comprobante (opcional).">
      <input type="file" class="cr-input" @change="onArchivo" />
    </FormField>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
