<script setup>
import { onMounted, reactive, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { listarMarcasReloj } from '@/configuracion'
import { getMargenMinimo, setMargenMinimo } from '@/clientes/services/clientesApi'

const global = ref(null)
const overrides = ref([]) // { ambito, ref, out }
const loading = ref(true)
const marcas = ref([])

const modal = reactive({ abierto: false, guardando: false, error: '' })
const f = reactive({ ambito: 'global', ref: '', tipo: 'porcentaje_costo', valor: null, politica: 'autorizar' })

async function cargar() {
  loading.value = true
  global.value = await getMargenMinimo({ ambito: 'global' }).catch(() => null)
  // overrides por marca (consulta best-effort; el backend cae a global si no hay)
  overrides.value = []
  for (const m of marcas.value) {
    const r = await getMargenMinimo({ ambito: 'marca', ref: m.nombre }).catch(() => null)
    if (r && r.ambito === 'marca') overrides.value.push(r)
  }
  loading.value = false
}
onMounted(async () => {
  marcas.value = await listarMarcasReloj(true).catch(() => [])
  cargar()
})

function abrir(pre = null) {
  Object.assign(f, {
    ambito: pre?.ambito ?? 'global',
    ref: pre?.ref ?? '',
    tipo: pre?.tipo ?? global.value?.tipo ?? 'porcentaje_costo',
    valor: pre?.valor ?? null,
    politica: global.value?.politica ?? 'autorizar',
  })
  modal.error = ''
  modal.abierto = true
}

async function guardar() {
  modal.error = ''
  if (f.valor === null || Number(f.valor) < 0) return (modal.error = 'Indica el valor del margen mínimo.')
  if (f.tipo === 'porcentaje_costo' && Number(f.valor) > 1) return (modal.error = 'El porcentaje va como fracción (0,15 = 15 %).')
  if (f.ambito !== 'global' && !f.ref.trim()) return (modal.error = 'Indica la marca o el producto del ámbito.')
  modal.guardando = true
  try {
    await setMargenMinimo({
      tipo: f.tipo, valor: Number(f.valor), ambito: f.ambito,
      ref: f.ambito === 'global' ? null : f.ref.trim(),
      politica: f.ambito === 'global' ? f.politica : null,
    })
    toast.success('Margen mínimo actualizado — se recalculan las operaciones abiertas')
    modal.abierto = false
    cargar()
  } catch (e) {
    modal.error = e.message
  } finally {
    modal.guardando = false
  }
}

const fmt = (mm) => (mm.tipo === 'porcentaje_costo' ? `${(mm.valor * 100).toFixed(1)} % sobre el costo` : `$ ${Number(mm.valor).toLocaleString()} mínimo`)
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Clientes · Protección financiera"
      titulo="Margen mínimo protegido"
      sub="Ningún descuento ni cupón puede dejar el margen de una venta u orden de trabajo por debajo de este mínimo. El cálculo es siempre del backend."
    >
      <template #acciones>
        <button class="cr-btn cr-btn-primary" @click="abrir()">Configurar</button>
      </template>
    </PageHeader>

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>

    <template v-else>
      <section class="cr-card mb-5 border-gold/40 p-6">
        <p class="cr-label">Margen mínimo global</p>
        <p class="serif mt-1 text-3xl text-gold-strong tabular-nums">{{ global ? fmt(global) : '—' }}</p>
        <p class="mt-2 flex items-center gap-2 text-sm text-ink-2">
          Política cuando un descuento cae por debajo:
          <Pill :tone="global?.politica === 'bloquear' ? 'bad' : 'warn'" :label="global?.politica === 'bloquear' ? 'bloquear la operación' : 'exigir autorización de Gerencia'" />
        </p>
        <p class="mt-3 text-xs text-ink-3">
          <CrIcon name="lock" :size="12" class="mr-1 inline" />
          La autorización expresa la registra solo Gerencia General y queda auditada (quién, cuándo, sobre qué operación).
        </p>
      </section>

      <section class="cr-card overflow-hidden p-0">
        <header class="flex items-center justify-between p-6 pb-3">
          <h2 class="serif text-lg text-ink">Excepciones por marca / producto</h2>
          <span class="text-xs text-ink-3">Tienen prioridad sobre el mínimo global</span>
        </header>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Ámbito</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Referencia</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Mínimo</th>
              <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-hairline-soft">
            <tr v-for="o in overrides" :key="`${o.ambito}-${o.ref}`">
              <td class="px-6 py-2.5">{{ o.ambito }}</td>
              <td class="px-6 py-2.5">{{ o.ref }}</td>
              <td class="px-6 py-2.5 tabular-nums">{{ fmt(o) }}</td>
              <td class="px-6 py-2.5 text-right"><button class="text-xs text-gold-strong hover:underline" @click="abrir(o)">Editar</button></td>
            </tr>
            <tr v-if="!overrides.length"><td colspan="4" class="px-6 py-6 text-center text-ink-3">Sin excepciones — todo usa el mínimo global.</td></tr>
          </tbody>
        </table>
      </section>
    </template>

    <FormModal v-model="modal.abierto" titulo="Configurar margen mínimo" :guardando="modal.guardando" @guardar="guardar">
      <FormField label="Ámbito" required>
        <select v-model="f.ambito" class="cr-input">
          <option value="global">Global</option><option value="marca">Marca</option><option value="producto">Producto</option>
        </select>
      </FormField>
      <FormField v-if="f.ambito === 'marca'" label="Marca">
        <select v-model="f.ref" class="cr-input"><option value="">—</option><option v-for="m in marcas" :key="m.id" :value="m.nombre">{{ m.nombre }}</option></select>
      </FormField>
      <FormField v-else-if="f.ambito === 'producto'" label="Referencia del producto"><input v-model="f.ref" class="cr-input" /></FormField>

      <FormField label="Tipo" required>
        <select v-model="f.tipo" class="cr-input"><option value="porcentaje_costo">% sobre el costo</option><option value="monto">Monto mínimo ($)</option></select>
      </FormField>
      <FormField :label="f.tipo === 'porcentaje_costo' ? 'Valor (fracción: 0,15 = 15 %)' : 'Monto mínimo ($)'" required>
        <input v-model="f.valor" type="number" min="0" step="0.01" class="cr-input" required />
      </FormField>

      <FormField v-if="f.ambito === 'global'" label="Política al caer bajo el mínimo" wide>
        <select v-model="f.politica" class="cr-input">
          <option value="autorizar">Exigir autorización expresa de Gerencia General</option>
          <option value="bloquear">Bloquear la operación (sin excepción)</option>
        </select>
      </FormField>

      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
