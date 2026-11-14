<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import WorkPanel from '@/shared/ui/WorkPanel.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import {
  crearCategoriaGasto,
  crearColor,
  crearCondicionPago,
  crearMarcaReloj,
  crearMaterial,
  crearMedioPago,
  listarCanalesCita,
  listarCategoriasGasto,
  listarColores,
  listarCondicionesPago,
  listarMarcasReloj,
  listarMateriales,
  listarMediosPago,
  setActivoColor,
  setActivoCondicionPago,
  setActivoMarcaReloj,
  setActivoMaterial,
  setActivoMedioPago,
} from '@/configuracion/services/configuracionApi'

const CATALOGOS = {
  medio_pago: {
    titulo: 'Medios de pago',
    sub: 'Se pueden agregar e inactivar (nunca borrar los que estén en uso). Sin pasarela de pago en línea.',
    editable: true,
    puedeInactivar: true,
    cols: [{ key: 'nombre', label: 'Nombre' }, { key: 'estado', label: 'Estado' }],
    listar: listarMediosPago,
    crear: (f) => crearMedioPago(f.nombre),
    activar: setActivoMedioPago,
    campos: [{ key: 'nombre', label: 'Nombre', tipo: 'text', required: true }],
  },
  condicion_pago: {
    titulo: 'Condiciones de pago',
    sub: 'Catálogo maestro. Se usa en la ficha de proveedor y en las órdenes de compra.',
    editable: true,
    puedeInactivar: true,
    cols: [{ key: 'nombre', label: 'Nombre' }, { key: 'dias_credito', label: 'Días de crédito', align: 'right' }, { key: 'estado', label: 'Estado' }],
    listar: () => listarCondicionesPago(false),
    crear: (f) => crearCondicionPago({ nombre: f.nombre, dias_credito: Number(f.dias_credito || 0) }),
    activar: setActivoCondicionPago,
    campos: [
      { key: 'nombre', label: 'Nombre', tipo: 'text', required: true },
      { key: 'dias_credito', label: 'Días de crédito', tipo: 'number' },
    ],
  },
  categoria_gasto: {
    titulo: 'Categorías de gasto',
    sub: 'Para el registro contable de gastos (feature 010).',
    editable: true,
    puedeInactivar: false,
    cols: [{ key: 'nombre', label: 'Nombre' }, { key: 'tipo', label: 'Tipo' }],
    listar: listarCategoriasGasto,
    crear: (f) => crearCategoriaGasto({ nombre: f.nombre, tipo: f.tipo }),
    campos: [
      { key: 'nombre', label: 'Nombre', tipo: 'text', required: true },
      { key: 'tipo', label: 'Tipo', tipo: 'select', opciones: ['local_operativos', 'personal', 'otros', 'mermas_perdidas'], required: true },
    ],
  },
  marca_reloj: {
    titulo: 'Marcas de reloj',
    sub: 'Catálogo de la ficha de reloj. País, sitio web y nota son opcionales.',
    editable: true,
    puedeInactivar: true,
    cols: [{ key: 'nombre', label: 'Marca' }, { key: 'pais', label: 'País' }, { key: 'estado', label: 'Estado' }],
    listar: () => listarMarcasReloj(false),
    crear: (f) => crearMarcaReloj({ nombre: f.nombre, pais: f.pais || null, sitio_web: f.sitio_web || null, nota: f.nota || null }),
    activar: setActivoMarcaReloj,
    campos: [
      { key: 'nombre', label: 'Nombre', tipo: 'text', required: true },
      { key: 'pais', label: 'País', tipo: 'text' },
      { key: 'sitio_web', label: 'Sitio web', tipo: 'text' },
      { key: 'nota', label: 'Nota', tipo: 'text' },
    ],
  },
  material: {
    titulo: 'Materiales',
    sub: 'Compartido para la caja y el brazalete de la ficha de reloj.',
    editable: true,
    puedeInactivar: true,
    cols: [{ key: 'nombre', label: 'Material' }, { key: 'estado', label: 'Estado' }],
    listar: () => listarMateriales(false),
    crear: (f) => crearMaterial(f.nombre),
    activar: setActivoMaterial,
    campos: [{ key: 'nombre', label: 'Nombre', tipo: 'text', required: true }],
  },
  color: {
    titulo: 'Colores de esfera',
    sub: 'Nombre + hex opcional para la muestra de color.',
    editable: true,
    puedeInactivar: true,
    cols: [{ key: 'nombre', label: 'Color' }, { key: 'hex', label: 'Hex' }, { key: 'estado', label: 'Estado' }],
    listar: () => listarColores(false),
    crear: (f) => crearColor({ nombre: f.nombre, hex: f.hex || null }),
    activar: setActivoColor,
    campos: [
      { key: 'nombre', label: 'Nombre', tipo: 'text', required: true },
      { key: 'hex', label: 'Hex (ej. #1A1A1A)', tipo: 'text' },
    ],
  },
  canal_cita: {
    titulo: 'Canales de solicitud de citas',
    sub: 'Cómo llega una solicitud de cita (correo, presencial…). Se administra desde la feature de Citas.',
    editable: false,
    puedeInactivar: false,
    cols: [{ key: 'nombre', label: 'Nombre' }, { key: 'estado', label: 'Estado' }],
    listar: listarCanalesCita,
    campos: [],
  },
}

const activo = ref('medio_pago')
const rows = ref([])
const loading = ref(true)
const errorMsg = ref('')
const q = ref('')

const cfg = computed(() => CATALOGOS[activo.value])

async function cargar() {
  loading.value = true
  errorMsg.value = ''
  try {
    rows.value = await cfg.value.listar()
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(cargar)
watch(activo, () => {
  q.value = ''
  cargar()
})

const visibles = computed(() => {
  const s = q.value.trim().toLowerCase()
  return s ? rows.value.filter((r) => r.nombre.toLowerCase().includes(s)) : rows.value
})

// --- alta ---
const modal = reactive({ abierto: false, guardando: false, error: '', form: {} })
function abrirAlta() {
  modal.form = {}
  modal.error = ''
  modal.abierto = true
}
async function crear() {
  modal.error = ''
  modal.guardando = true
  try {
    await cfg.value.crear(modal.form)
    toast.success('Agregado al catálogo')
    modal.abierto = false
    cargar()
  } catch (e) {
    modal.error = e.status === 409 ? 'Ya existe un registro equivalente.' : e.message
  } finally {
    modal.guardando = false
  }
}

async function alternar(row) {
  const nuevo = !row.activo
  if (!nuevo && !(await confirm({
    title: `Inactivar «${row.nombre}»`,
    message: 'No se elimina; deja de ofrecerse en los selectores. Se puede reactivar.',
    tone: 'danger',
    confirmLabel: 'Inactivar',
  }))) return
  try {
    await cfg.value.activar(row.id, nuevo)
    toast.success(nuevo ? 'Reactivado' : 'Inactivado')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const acciones = (row) => (cfg.value.puedeInactivar
  ? [{ label: row.activo ? 'Inactivar' : 'Reactivar', icon: row.activo ? 'ban' : 'check', danger: row.activo, onClick: () => alternar(row) }]
  : [])
</script>

<template>
  <div>
    <div class="mb-5 flex flex-wrap gap-1 border-b border-hairline">
      <button
        v-for="(c, k) in CATALOGOS"
        :key="k"
        class="border-b-2 px-3 py-2 text-sm font-medium"
        :class="activo === k ? 'border-gold text-ink' : 'border-transparent text-ink-3 hover:text-ink-2'"
        @click="activo = k"
      >
        {{ c.titulo }}
      </button>
    </div>

    <WorkPanel
      eyebrow="Sistema · Configuración"
      :titulo="cfg.titulo"
      :sub="cfg.sub"
      :columns="cfg.cols"
      :rows="visibles"
      :total="visibles.length"
      :loading="loading"
      :error="errorMsg"
      v-model:search="q"
      :page-size="visibles.length || 1"
      search-placeholder="Filtrar…"
      :row-actions="cfg.puedeInactivar ? acciones : null"
      empty-title="Catálogo vacío"
      @retry="cargar"
    >
      <template v-if="cfg.editable" #actions>
        <button class="cr-btn cr-btn-primary" @click="abrirAlta">Agregar</button>
      </template>
      <template #cell-estado="{ row }">
        <Pill :tone="row.activo === false ? 'bad' : 'good'" :label="row.activo === false ? 'inactivo' : 'activo'" />
      </template>
      <template #cell-tipo="{ row }"><span class="text-ink-2">{{ (row.tipo || '').replace(/_/g, ' ') }}</span></template>
      <template #cell-dias_credito="{ row }">{{ row.dias_credito ?? 0 }}</template>
      <template #cell-pais="{ row }">{{ row.pais || '—' }}</template>
      <template #cell-hex="{ row }">
        <span v-if="row.hex" class="inline-flex items-center gap-1.5">
          <span class="h-3 w-3 rounded-full border border-hairline" :style="{ background: row.hex }"></span>
          <span class="tabular-nums text-ink-2">{{ row.hex }}</span>
        </span>
        <span v-else class="text-ink-3">—</span>
      </template>
    </WorkPanel>

    <FormModal v-model="modal.abierto" :titulo="`Agregar a ${cfg.titulo.toLowerCase()}`" :guardando="modal.guardando" ancho="max-w-md" @guardar="crear">
      <FormField v-for="campo in cfg.campos" :key="campo.key" :label="campo.label" :required="campo.required" wide>
        <select v-if="campo.tipo === 'select'" v-model="modal.form[campo.key]" class="cr-input" :required="campo.required">
          <option value="" disabled>Elegir…</option>
          <option v-for="o in campo.opciones" :key="o" :value="o">{{ o.replace(/_/g, ' ') }}</option>
        </select>
        <input v-else v-model="modal.form[campo.key]" :type="campo.tipo" class="cr-input" :required="campo.required" :min="campo.tipo === 'number' ? 0 : undefined" />
      </FormField>
      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
