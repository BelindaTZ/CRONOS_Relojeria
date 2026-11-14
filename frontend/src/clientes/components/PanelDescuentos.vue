<script setup>
import { onMounted, reactive, ref } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import { toast } from '@/shared/ui/toast'
import { listarMarcasReloj } from '@/configuracion'
import { actualizarDescuento, crearDescuento, listarDescuentos, listarNiveles } from '@/clientes/services/clientesApi'

const columns = [
  { key: 'nombre', label: 'Descuento' },
  { key: 'valor', label: 'Valor', align: 'right' },
  { key: 'alcance', label: 'Alcance' },
  { key: 'segmento', label: 'Segmento' },
  { key: 'vigencia', label: 'Vigencia' },
  { key: 'estado', label: 'Estado' },
]
const TONO = { activo: 'good', inactivo: 'neutral', vencido: 'bad' }

const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')
const niveles = ref([])
const marcas = ref([])

const modal = reactive({ abierto: false, guardando: false, error: '' })
const f = reactive({
  nombre: '', tipo: 'porcentaje', valor: null, alcance: 'tienda', alcance_ref: '',
  segmento: 'todos', segmento_ref: '', vigencia_inicio: '', vigencia_fin: '', evento: '',
  limite_uso: 'global', max_usos: null,
})

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await listarDescuentos()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  ;[niveles.value, marcas.value] = await Promise.all([
    listarNiveles().catch(() => []),
    listarMarcasReloj(true).catch(() => []),
  ])
  cargar()
})

const visibles = () => {
  const s = q.value.trim().toLowerCase()
  return s ? rows.value.filter((r) => r.nombre.toLowerCase().includes(s)) : rows.value
}

function abrir() {
  Object.assign(f, {
    nombre: '', tipo: 'porcentaje', valor: null, alcance: 'tienda', alcance_ref: '',
    segmento: 'todos', segmento_ref: '', vigencia_inicio: '', vigencia_fin: '', evento: '',
    limite_uso: 'global', max_usos: null,
  })
  modal.error = ''
  modal.abierto = true
}

async function guardar() {
  modal.error = ''
  if (f.nombre.trim().length < 2) return (modal.error = 'Ponle un nombre al descuento.')
  if (!f.valor || Number(f.valor) <= 0) return (modal.error = 'Indica el valor del descuento.')
  if (f.tipo === 'porcentaje' && Number(f.valor) > 1) return (modal.error = 'El porcentaje va como fracción (0,10 = 10 %).')
  modal.guardando = true
  try {
    await crearDescuento({
      nombre: f.nombre.trim(), tipo: f.tipo, valor: Number(f.valor),
      alcance: f.alcance, alcance_ref: f.alcance === 'tienda' ? null : (f.alcance_ref || null),
      segmento: f.segmento, segmento_ref: f.segmento === 'todos' ? null : (f.segmento_ref || null),
      vigencia_inicio: f.vigencia_inicio || null, vigencia_fin: f.vigencia_fin || null,
      evento: f.evento || null, limite_uso: f.limite_uso,
      max_usos: f.limite_uso === 'una_vez' ? null : (f.max_usos ? Number(f.max_usos) : null),
    })
    toast.success('Descuento general creado')
    modal.abierto = false
    cargar()
  } catch (e) {
    modal.error = e.message
  } finally {
    modal.guardando = false
  }
}

async function alternarEstado(d) {
  try {
    await actualizarDescuento(d.id, { estado: d.estado === 'activo' ? 'inactivo' : 'activo' })
    toast.success(d.estado === 'activo' ? 'Descuento desactivado' : 'Descuento activado')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const acciones = (d) => [
  { label: d.estado === 'activo' ? 'Desactivar' : 'Activar', icon: d.estado === 'activo' ? 'ban' : 'circle-check', onClick: () => alternarEstado(d) },
]
const fmtValor = (d) => (d.tipo === 'porcentaje' ? `${(d.valor * 100).toFixed(0)} %` : `$ ${Number(d.valor).toLocaleString()}`)
const EVENTO = { cumpleanos: 'cumpleaños del cliente', aniversario_tienda: 'aniversario de la tienda' }
const fmtEvento = (e) => EVENTO[e] || e
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Clientes"
      titulo="Descuentos generales"
      sub="Se aplican automáticamente a un segmento (nivel, cliente) o a toda la tienda durante una vigencia. Un descuento general y un cupón nunca se combinan en la misma operación."
      :columns="columns"
      :rows="visibles()"
      :total="visibles().length"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      :page-size="visibles().length || 1"
      search-placeholder="Filtrar por nombre…"
      :row-actions="acciones"
      empty-title="Sin descuentos generales"
      empty-hint="Crea un descuento por nivel de fidelización, por cliente o para toda la tienda."
      empty-icon="tag"
      @retry="cargar"
    >
      <template #actions>
        <RouterLink :to="{ name: 'cupones' }" class="cr-btn cr-btn-ghost">Cupones</RouterLink>
        <button class="cr-btn cr-btn-primary" @click="abrir">Nuevo descuento</button>
      </template>
      <template #cell-nombre="{ row }"><span class="font-medium text-ink">{{ row.nombre }}</span></template>
      <template #cell-valor="{ row }"><span class="tabular-nums text-gold-strong">{{ fmtValor(row) }}</span></template>
      <template #cell-alcance="{ row }">{{ row.alcance }}<span v-if="row.alcance_ref" class="text-ink-3"> · {{ row.alcance_ref }}</span></template>
      <template #cell-segmento="{ row }">{{ row.segmento }}<span v-if="row.segmento_ref" class="text-ink-3"> · #{{ row.segmento_ref }}</span></template>
      <template #cell-vigencia="{ row }">
        <span v-if="row.evento" class="text-ink-2">{{ fmtEvento(row.evento) }}</span>
        <span v-else-if="row.vigencia_inicio || row.vigencia_fin" class="tabular-nums text-ink-2">{{ row.vigencia_inicio || '…' }} → {{ row.vigencia_fin || '…' }}</span>
        <span v-else class="text-ink-3">permanente</span>
      </template>
      <template #cell-estado="{ row }"><Pill :tone="TONO[row.estado] || 'neutral'" :label="row.estado" /></template>
    </WorkPanel>

    <FormModal v-model="modal.abierto" titulo="Nuevo descuento general" :guardando="modal.guardando" ancho="max-w-2xl" @guardar="guardar">
      <FormField label="Nombre" required wide><input v-model="f.nombre" class="cr-input" required placeholder="10 % en mantenimiento — aniversario" /></FormField>

      <FormField label="Tipo" required>
        <select v-model="f.tipo" class="cr-input"><option value="porcentaje">Porcentaje</option><option value="monto">Monto fijo</option></select>
      </FormField>
      <FormField :label="f.tipo === 'porcentaje' ? 'Valor (fracción: 0,10 = 10 %)' : 'Monto ($)'" required>
        <input v-model="f.valor" type="number" min="0" step="0.01" class="cr-input" required />
      </FormField>

      <FormField label="Alcance" required>
        <select v-model="f.alcance" class="cr-input">
          <option value="tienda">Toda la tienda</option><option value="marca">Marca</option><option value="producto">Producto</option>
        </select>
      </FormField>
      <FormField v-if="f.alcance === 'marca'" label="Marca">
        <select v-model="f.alcance_ref" class="cr-input"><option value="">—</option><option v-for="m in marcas" :key="m.id" :value="m.nombre">{{ m.nombre }}</option></select>
      </FormField>
      <FormField v-else-if="f.alcance === 'producto'" label="Referencia del producto"><input v-model="f.alcance_ref" class="cr-input" /></FormField>

      <FormField label="Segmento" required>
        <select v-model="f.segmento" class="cr-input">
          <option value="todos">Todos los clientes</option><option value="nivel">Nivel de fidelización</option><option value="cliente">Cliente puntual</option>
        </select>
      </FormField>
      <FormField v-if="f.segmento === 'nivel'" label="Nivel">
        <select v-model="f.segmento_ref" class="cr-input"><option value="">—</option><option v-for="n in niveles" :key="n.id" :value="String(n.id)">{{ n.nombre }}</option></select>
      </FormField>
      <FormField v-else-if="f.segmento === 'cliente'" label="ID del cliente"><input v-model="f.segmento_ref" type="number" class="cr-input" /></FormField>

      <FormField label="Vigencia — inicio"><input v-model="f.vigencia_inicio" type="date" class="cr-input" /></FormField>
      <FormField label="Vigencia — fin"><input v-model="f.vigencia_fin" type="date" class="cr-input" /></FormField>
      <FormField label="Evento asociado" helper="En vez de fechas fijas.">
        <select v-model="f.evento" class="cr-input"><option value="">—</option><option value="cumpleanos">Cumpleaños del cliente</option><option value="aniversario_tienda">Aniversario de la tienda</option></select>
      </FormField>

      <FormField label="Límite de uso">
        <select v-model="f.limite_uso" class="cr-input">
          <option value="global">Global</option><option value="por_cliente">Por cliente</option><option value="n_veces">N veces</option><option value="una_vez">Una vez</option>
        </select>
      </FormField>
      <FormField v-if="['n_veces', 'global', 'por_cliente'].includes(f.limite_uso)" label="Máx. usos"><input v-model="f.max_usos" type="number" min="1" class="cr-input" /></FormField>

      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
