<script setup>
import { computed, onMounted, ref } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import Pill from '@/shared/ui/Pill.vue'
import { listarProductosMoebius } from '@/lubricacion/services/lubricacionApi'
import ProductoMoebiusModal from './ProductoMoebiusModal.vue'

const columns = [
  { key: 'codigo', label: 'Código' },
  { key: 'uso_recomendado', label: 'Uso recomendado' },
  { key: 'pieza_id', label: 'Insumo en stock', align: 'right' },
  { key: 'activo', label: 'Estado' },
]
const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const modal = ref(false)

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await listarProductosMoebius()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)

const filtradas = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return rows.value
  return rows.value.filter((p) => `${p.codigo} ${p.uso_recomendado}`.toLowerCase().includes(s))
})
const kpis = computed(() => [
  { label: 'Productos Moebius', value: String(rows.value.length) },
  { label: 'Vinculados a stock', value: String(rows.value.filter((p) => p.pieza_id).length), gold: true },
])
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Taller · Lubricación"
      titulo="Catálogo Moebius"
      sub="Aceites y grasas de referencia (9010, 9104/HP-1300, 9415, 9501/9504, 8200/8217, 8513/8516…). Cada producto puede vincularse a la pieza-insumo perecedera en stock para calcular su consumo."
      :columns="columns"
      :rows="filtradas"
      :total="filtradas.length"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      :page-size="50"
      search-placeholder="Código o uso…"
      :kpis="kpis"
      empty-title="Catálogo vacío"
      empty-hint="El catálogo base se siembra con la instalación; aquí puedes ampliarlo."
      empty-icon="layers"
      @retry="cargar"
    >
      <template #actions>
        <button class="cr-btn cr-btn-primary" @click="modal = true">Añadir producto</button>
      </template>
      <template #cell-codigo="{ row }"><span class="serif text-ink">{{ row.codigo }}</span></template>
      <template #cell-pieza_id="{ row }">
        <span v-if="row.pieza_id" class="tabular-nums text-ink-2">#{{ row.pieza_id }}</span>
        <span v-else class="text-ink-3">sin vincular</span>
      </template>
      <template #cell-activo="{ row }">
        <Pill :tone="row.activo ? 'good' : 'neutral'" :label="row.activo ? 'activo' : 'inactivo'" />
      </template>
    </WorkPanel>

    <ProductoMoebiusModal v-model="modal" @guardado="cargar" />
  </div>
</template>
