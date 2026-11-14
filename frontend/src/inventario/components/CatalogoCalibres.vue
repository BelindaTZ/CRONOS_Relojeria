<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import { toast } from '@/shared/ui/toast'
import { crearCalibre, listarCalibres } from '@/inventario/services/inventarioApi'

const columns = [
  { key: 'codigo', label: 'Código' },
  { key: 'marca', label: 'Marca' },
  { key: 'descripcion', label: 'Descripción' },
  { key: 'relojes', label: 'Relojes', align: 'right' },
]

const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')

const modal = reactive({ abierto: false, guardando: false, error: '', codigo: '', marca: '', descripcion: '' })

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await listarCalibres(q.value || undefined)
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
let t
watch(q, () => {
  clearTimeout(t)
  t = setTimeout(cargar, 250)
})

function abrir() {
  Object.assign(modal, { abierto: true, guardando: false, error: '', codigo: '', marca: '', descripcion: '' })
}
async function guardar() {
  modal.error = ''
  if (!modal.codigo.trim()) return (modal.error = 'El código es obligatorio.')
  modal.guardando = true
  try {
    await crearCalibre({ codigo: modal.codigo.trim(), marca: modal.marca.trim() || null, descripcion: modal.descripcion.trim() || null })
    toast.success(`Calibre ${modal.codigo} creado`)
    modal.abierto = false
    cargar()
  } catch (e) {
    modal.error = e.status === 409 ? 'Ya existe un calibre con ese código.' : e.message
  } finally {
    modal.guardando = false
  }
}
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Inventario"
      titulo="Calibres"
      sub="Identificador del movimiento. La ficha de lubricación por calibre (puntos y productos Moebius) se añade en Servicio Técnico."
      :columns="columns"
      :rows="rows"
      :total="rows.length"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      :page-size="rows.length || 1"
      search-placeholder="Código o marca…"
      empty-title="Sin calibres registrados"
      empty-hint="Registra los calibres para poder asociarlos a cada reloj y a las piezas compatibles."
      empty-icon="layers"
      @retry="cargar"
    >
      <template #actions>
        <RouterLink :to="{ name: 'inventario' }" class="cr-btn cr-btn-ghost">Relojes</RouterLink>
        <button class="cr-btn cr-btn-primary" @click="abrir">Agregar calibre</button>
      </template>
      <template #cell-marca="{ row }">{{ row.marca || '—' }}</template>
      <template #cell-descripcion="{ row }">{{ row.descripcion || '—' }}</template>
    </WorkPanel>

    <FormModal v-model="modal.abierto" titulo="Nuevo calibre" :guardando="modal.guardando" ancho="max-w-md" @guardar="guardar">
      <FormField label="Código" required wide><input v-model="modal.codigo" class="cr-input" required /></FormField>
      <FormField label="Marca" wide><input v-model="modal.marca" class="cr-input" /></FormField>
      <FormField label="Descripción" wide><input v-model="modal.descripcion" class="cr-input" /></FormField>
      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
