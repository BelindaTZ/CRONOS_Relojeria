<script setup>
import { onMounted, reactive, ref } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import Pill from '@/shared/ui/Pill.vue'
import { toast } from '@/shared/ui/toast'
import { listarMarcasReloj } from '@/configuracion'
import { crearCupon, listarClientes, listarCupones } from '@/clientes/services/clientesApi'

const columns = [
  { key: 'codigo', label: 'Código' },
  { key: 'cliente', label: 'Cliente' },
  { key: 'valor', label: 'Valor', align: 'right' },
  { key: 'vigencia', label: 'Vigencia' },
  { key: 'limite_uso', label: 'Límite' },
  { key: 'estado', label: 'Estado' },
]
const TONO = { activo: 'good', usado: 'neutral', vencido: 'bad' }

const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')
const fEstado = ref('')
const clientes = ref([])
const marcas = ref([])

const modal = reactive({ abierto: false, guardando: false, error: '' })
const f = reactive({
  codigo: '', cliente_id: null, tipo: 'porcentaje', valor: null, alcance: 'tienda', alcance_ref: '',
  vigencia_inicio: '', vigencia_fin: '', evento: '', limite_uso: 'una_vez', max_usos: null,
})

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await listarCupones({ estado: fEstado.value || undefined })
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  const [cl, mk] = await Promise.all([
    listarClientes({ page: 1, size: 100 }).catch(() => ({ items: [] })),
    listarMarcasReloj(true).catch(() => []),
  ])
  clientes.value = cl.items.map((x) => ({ ...x, _label: `${x.nombre} · ${x.numero_afiliado}` }))
  marcas.value = mk
  cargar()
})

function abrir() {
  Object.assign(f, {
    codigo: '', cliente_id: null, tipo: 'porcentaje', valor: null, alcance: 'tienda', alcance_ref: '',
    vigencia_inicio: '', vigencia_fin: '', evento: '', limite_uso: 'una_vez', max_usos: null,
  })
  modal.error = ''
  modal.abierto = true
}

async function guardar() {
  modal.error = ''
  if (f.codigo.trim().length < 3) return (modal.error = 'El código debe tener al menos 3 caracteres.')
  if (!f.cliente_id) return (modal.error = 'Elige el cliente al que se asigna el cupón.')
  if (!f.valor || Number(f.valor) <= 0) return (modal.error = 'Indica el valor del cupón.')
  if (f.tipo === 'porcentaje' && Number(f.valor) > 1) return (modal.error = 'El porcentaje va como fracción (0,10 = 10 %).')
  modal.guardando = true
  try {
    await crearCupon({
      codigo: f.codigo.trim().toUpperCase(), cliente_id: f.cliente_id, tipo: f.tipo, valor: Number(f.valor),
      alcance: f.alcance, alcance_ref: f.alcance === 'tienda' ? null : (f.alcance_ref || null),
      vigencia_inicio: f.vigencia_inicio || null, vigencia_fin: f.vigencia_fin || null,
      evento: f.evento || null, limite_uso: f.limite_uso,
      max_usos: f.limite_uso === 'una_vez' ? null : (f.max_usos ? Number(f.max_usos) : null),
    })
    toast.success(`Cupón ${f.codigo.trim().toUpperCase()} emitido`)
    modal.abierto = false
    cargar()
  } catch (e) {
    modal.error = e.message
  } finally {
    modal.guardando = false
  }
}

const fmtValor = (c) => (c.tipo === 'porcentaje' ? `${(c.valor * 100).toFixed(0)} %` : `$ ${Number(c.valor).toLocaleString()}`)
const EVENTO = { cumpleanos: 'cumpleaños del cliente', aniversario_tienda: 'aniversario de la tienda' }
const fmtEvento = (e) => EVENTO[e] || e
</script>

<template>
  <div>
    <WorkPanel
      eyebrow="Clientes"
      titulo="Cupones"
      sub="Beneficio puntual asignado a un cliente, con código, vigencia y límite de uso propios. Un cupón de uso único no puede consumirse dos veces."
      :columns="columns"
      :rows="rows"
      :total="rows.length"
      :loading="loading"
      :error="errorMsg"
      :page-size="rows.length || 1"
      :row-actions="null"
      empty-title="Sin cupones emitidos"
      empty-hint="Emite un cupón de cumpleaños, de reactivación o de beneficio puntual para un cliente."
      empty-icon="tag"
      @retry="cargar"
    >
      <template #actions>
        <RouterLink :to="{ name: 'descuentos' }" class="cr-btn cr-btn-ghost">Descuentos</RouterLink>
        <button class="cr-btn cr-btn-primary" @click="abrir">Emitir cupón</button>
      </template>
      <template #toolbar>
        <select v-model="fEstado" class="cr-input max-w-[11rem]" @change="cargar">
          <option value="">Todos los estados</option><option value="activo">Activo</option><option value="usado">Usado</option><option value="vencido">Vencido</option>
        </select>
      </template>
      <template #cell-codigo="{ row }"><span class="font-medium tabular-nums text-ink">{{ row.codigo }}</span></template>
      <template #cell-cliente="{ row }">{{ row.cliente_nombre || `#${row.cliente_id}` }}</template>
      <template #cell-valor="{ row }"><span class="tabular-nums text-gold-strong">{{ fmtValor(row) }}</span></template>
      <template #cell-vigencia="{ row }">
        <span v-if="row.evento" class="text-ink-2">{{ fmtEvento(row.evento) }}</span>
        <span v-else class="tabular-nums text-ink-2">{{ row.vigencia_inicio || '…' }} → {{ row.vigencia_fin || '…' }}</span>
      </template>
      <template #cell-limite_uso="{ row }">{{ row.limite_uso.replace(/_/g, ' ') }} · {{ row.usos }}{{ row.max_usos ? `/${row.max_usos}` : '' }}</template>
      <template #cell-estado="{ row }"><Pill :tone="TONO[row.estado] || 'neutral'" :label="row.estado" /></template>
    </WorkPanel>

    <FormModal v-model="modal.abierto" titulo="Emitir cupón" :guardando="modal.guardando" ancho="max-w-2xl" @guardar="guardar">
      <FormField label="Código" required><input v-model="f.codigo" class="cr-input uppercase" required placeholder="CUMPLE-001" /></FormField>
      <FormField label="Cliente" required>
        <ComboBox v-model="f.cliente_id" :opciones="clientes" opcion-label="_label" opcion-value="id" placeholder="Buscar cliente…" />
      </FormField>

      <FormField label="Tipo" required>
        <select v-model="f.tipo" class="cr-input"><option value="porcentaje">Porcentaje</option><option value="monto">Monto fijo</option></select>
      </FormField>
      <FormField :label="f.tipo === 'porcentaje' ? 'Valor (fracción: 0,10 = 10 %)' : 'Monto ($)'" required>
        <input v-model="f.valor" type="number" min="0" step="0.01" class="cr-input" required />
      </FormField>

      <FormField label="Alcance" required>
        <select v-model="f.alcance" class="cr-input"><option value="tienda">Toda la tienda</option><option value="marca">Marca</option><option value="producto">Producto</option></select>
      </FormField>
      <FormField v-if="f.alcance === 'marca'" label="Marca">
        <select v-model="f.alcance_ref" class="cr-input"><option value="">—</option><option v-for="m in marcas" :key="m.id" :value="m.nombre">{{ m.nombre }}</option></select>
      </FormField>
      <FormField v-else-if="f.alcance === 'producto'" label="Referencia del producto"><input v-model="f.alcance_ref" class="cr-input" /></FormField>

      <FormField label="Vigencia — inicio"><input v-model="f.vigencia_inicio" type="date" class="cr-input" /></FormField>
      <FormField label="Vigencia — fin"><input v-model="f.vigencia_fin" type="date" class="cr-input" /></FormField>
      <FormField label="Evento asociado">
        <select v-model="f.evento" class="cr-input"><option value="">—</option><option value="cumpleanos">Cumpleaños del cliente</option><option value="aniversario_tienda">Aniversario de la tienda</option></select>
      </FormField>

      <FormField label="Límite de uso">
        <select v-model="f.limite_uso" class="cr-input">
          <option value="una_vez">Una vez</option><option value="n_veces">N veces</option><option value="por_cliente">Por cliente</option><option value="global">Global</option>
        </select>
      </FormField>
      <FormField v-if="f.limite_uso !== 'una_vez'" label="Máx. usos"><input v-model="f.max_usos" type="number" min="1" class="cr-input" /></FormField>

      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
