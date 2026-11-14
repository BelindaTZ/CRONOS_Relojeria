<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import { listarCalibres } from '@/inventario'
import {
  getPieza,
  inactivarPieza,
  listarLotesPieza,
  listarMovimientos,
} from '@/piezas/services/piezasApi'
import PiezaFormModal from './PiezaFormModal.vue'
import MovimientoModal from './MovimientoModal.vue'

const route = useRoute()
const id = Number(route.params.id)

const p = ref(null)
const lotes = ref([])
const movs = ref([])
const movTotal = ref(0)
const movPage = ref(1)
const sucursales = ref([])
const calibres = ref([])

const LOTE_TONO = { vigente: 'good', proximo_vencer: 'warn', vencido: 'bad' }
const MOV_TONO = {
  ingreso: 'good', transferencia_entrada: 'good',
  consumo_ot: 'warn', venta_suelta: 'warn', transferencia_salida: 'warn',
  merma: 'bad', ajuste: 'neutral',
}

const modalForm = ref(false)
const modalMov = ref(false)

const sucursalNombre = (idx) => sucursales.value.find((s) => s.id === idx)?.nombre ?? `#${idx}`
const calibreCodigo = (idx) => calibres.value.find((c) => c.id === idx)?.codigo ?? `#${idx}`

async function cargarMovs() {
  const r = await listarMovimientos(id, { page: movPage.value, size: 10 })
  movs.value = r.items
  movTotal.value = r.total
}
async function cargar() {
  p.value = await getPieza(id)
  if (p.value.perecedera) lotes.value = await listarLotesPieza(id).catch(() => [])
  await cargarMovs()
}
onMounted(async () => {
  sucursales.value = (await listarSucursales().catch(() => ({ items: [] }))).items
  calibres.value = await listarCalibres().catch(() => [])
  cargar()
})

async function inactivar() {
  const ok = await confirm({
    title: `Inactivar «${p.value.codigo}»`,
    message: 'La pieza no se elimina; queda inactiva. Su stock, lotes y movimientos se conservan.',
    confirmLabel: 'Inactivar',
    tone: 'danger',
  })
  if (!ok) return
  await inactivarPieza(id)
  toast.success('Pieza inactivada')
  cargar()
}

const fmt = (v) => (v == null ? '—' : `$ ${Number(v).toLocaleString()}`)
</script>

<template>
  <div v-if="p">
    <PageHeader eyebrow="Inventario · Pieza" :titulo="p.codigo" :sub="p.descripcion">
      <template #acciones>
        <RouterLink :to="{ name: 'piezas' }" class="cr-btn cr-btn-ghost">
          <CrIcon name="arrow-left" :size="15" /> Piezas
        </RouterLink>
        <button class="cr-btn cr-btn-ghost" @click="modalForm = true">Editar</button>
        <button class="cr-btn cr-btn-primary" @click="modalMov = true">Registrar movimiento</button>
        <button v-if="p.activo" class="cr-btn cr-btn-danger" @click="inactivar">Inactivar</button>
      </template>
    </PageHeader>

    <div class="mb-6 flex flex-wrap items-center gap-3">
      <Pill :tone="p.tipo === 'original' ? 'info' : 'neutral'" :label="p.tipo === 'original' ? 'original' : 'no original'" />
      <Pill v-if="p.perecedera" tone="warn" label="perecedera" />
      <Pill v-if="!p.activo" tone="bad" label="inactiva" />
    </div>

    <div class="grid gap-5 lg:grid-cols-2">
      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Datos</h2>
        <dl class="mt-4 space-y-2.5 text-sm">
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Unidad de medida</dt><dd>{{ p.unidad_medida || 'unidad' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Marca(s) compatible(s)</dt><dd>{{ p.marca_compatible || 'universal' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Proveedor</dt><dd>{{ p.proveedor_id ? `#${p.proveedor_id}` : '—' }}</dd></div>
          <div class="flex justify-between gap-4">
            <dt class="text-ink-3">Costo de adquisición</dt>
            <dd v-if="p.costos_visibles" class="tabular-nums">{{ fmt(p.costo_adquisicion) }}</dd>
            <dd v-else class="flex items-center gap-1 text-ink-3"><CrIcon name="lock" :size="12" /> restringido</dd>
          </div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Precio venta suelta</dt><dd class="tabular-nums">{{ fmt(p.precio_venta_suelta) }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Stock mínimo</dt><dd class="tabular-nums">{{ p.stock_minimo }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Stock total</dt><dd class="serif text-lg text-ink tabular-nums" :class="{ 'text-bad': p.bajo_minimo }">{{ p.stock_total }}</dd></div>
        </dl>
        <p v-if="p.calibres_compatibles.length" class="mt-4 flex flex-wrap gap-1.5 border-t border-hairline-soft pt-3">
          <span v-for="c in p.calibres_compatibles" :key="c" class="rounded-full bg-surface-sunk px-2 py-0.5 text-xs text-ink-2">{{ calibreCodigo(c) }}</span>
        </p>
      </section>

      <section class="cr-card overflow-hidden p-0">
        <header class="p-6 pb-3"><h2 class="serif text-lg text-ink">Stock por sucursal</h2></header>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Sucursal</th>
              <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Stock</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Estado</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-hairline-soft">
            <tr v-for="s in p.stock_por_sucursal" :key="s.sucursal_id">
              <td class="px-6 py-2.5">{{ sucursalNombre(s.sucursal_id) }}</td>
              <td class="px-6 py-2.5 text-right tabular-nums">{{ s.stock_actual }}</td>
              <td class="px-6 py-2.5"><Pill :tone="s.bajo_minimo ? 'warn' : 'good'" :label="s.bajo_minimo ? 'bajo mínimo' : 'ok'" /></td>
            </tr>
            <tr v-if="!p.stock_por_sucursal.length"><td colspan="3" class="px-6 py-6 text-center text-ink-3">Sin stock en ninguna sucursal.</td></tr>
          </tbody>
        </table>
      </section>

      <section v-if="p.perecedera" class="cr-card overflow-hidden p-0 lg:col-span-2">
        <header class="flex items-center justify-between p-6 pb-3">
          <h2 class="serif text-lg text-ink">Lotes y caducidad</h2>
          <span class="text-xs text-ink-3">Consumo FEFO — primero el que vence antes</span>
        </header>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Lote</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Sucursal</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Caducidad</th>
              <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Días</th>
              <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Cantidad</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Estado</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-hairline-soft">
            <tr v-for="l in lotes" :key="l.id">
              <td class="px-6 py-2.5 font-medium">{{ l.numero_lote }}</td>
              <td class="px-6 py-2.5">{{ sucursalNombre(l.sucursal_id) }}</td>
              <td class="px-6 py-2.5 tabular-nums">{{ l.fecha_caducidad }}</td>
              <td class="px-6 py-2.5 text-right tabular-nums" :class="{ 'text-bad': l.dias_restantes < 0 }">{{ l.dias_restantes }}</td>
              <td class="px-6 py-2.5 text-right tabular-nums">{{ l.cantidad }}</td>
              <td class="px-6 py-2.5"><Pill :tone="LOTE_TONO[l.estado] || 'neutral'" :label="l.estado.replace(/_/g, ' ')" /></td>
            </tr>
            <tr v-if="!lotes.length"><td colspan="6" class="px-6 py-6 text-center text-ink-3">Sin lotes registrados.</td></tr>
          </tbody>
        </table>
      </section>

      <section class="cr-card overflow-hidden p-0 lg:col-span-2">
        <header class="p-6 pb-3"><h2 class="serif text-lg text-ink">Movimientos</h2><p class="mt-1 text-xs text-ink-3">Libro append-only.</p></header>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Fecha</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Tipo</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Sucursal</th>
              <th class="px-6 py-2.5 text-right text-[0.7rem] font-semibold uppercase text-ink-2">Cantidad</th>
              <th class="px-6 py-2.5 text-[0.7rem] font-semibold uppercase text-ink-2">Documento</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-hairline-soft">
            <tr v-for="m in movs" :key="m.id">
              <td class="px-6 py-2.5 tabular-nums text-ink-2">{{ new Date(m.creado_en).toLocaleString() }}</td>
              <td class="px-6 py-2.5"><Pill :tone="MOV_TONO[m.tipo] || 'neutral'" :label="m.tipo.replace(/_/g, ' ')" /></td>
              <td class="px-6 py-2.5">{{ sucursalNombre(m.sucursal_id) }}</td>
              <td class="px-6 py-2.5 text-right font-semibold tabular-nums" :class="m.cantidad < 0 ? 'text-bad' : 'text-good'">
                {{ m.cantidad > 0 ? '+' : '' }}{{ m.cantidad }}
              </td>
              <td class="px-6 py-2.5 text-ink-3">{{ m.documento_tipo ? `${m.documento_tipo.replace(/_/g, ' ')} ${m.documento_id ? '#' + m.documento_id : ''}` : (m.nota || '—') }}</td>
            </tr>
            <tr v-if="!movs.length"><td colspan="5" class="px-6 py-6 text-center text-ink-3">Sin movimientos aún.</td></tr>
          </tbody>
        </table>
        <div v-if="movTotal > 10" class="flex items-center justify-end gap-3 border-t border-hairline px-6 py-3 text-sm text-ink-2">
          <button class="cr-btn cr-btn-ghost px-3 py-1.5" :disabled="movPage <= 1" @click="((movPage -= 1), cargarMovs())"><CrIcon name="chevron-left" :size="15" /></button>
          <span class="tabular-nums">{{ movPage }} / {{ Math.ceil(movTotal / 10) }}</span>
          <button class="cr-btn cr-btn-ghost px-3 py-1.5" :disabled="movPage >= Math.ceil(movTotal / 10)" @click="((movPage += 1), cargarMovs())"><CrIcon name="chevron-right" :size="15" /></button>
        </div>
      </section>

      <section class="cr-card p-6 lg:col-span-2">
        <h2 class="serif text-lg text-ink">Uso en órdenes de trabajo</h2>
        <p class="mt-2 text-sm text-ink-3">Se registrará automáticamente cuando la pieza se consuma en una orden de trabajo (feature 008).</p>
      </section>
    </div>

    <PiezaFormModal v-model="modalForm" :pieza="p" @guardada="cargar" />
    <MovimientoModal v-model="modalMov" :pieza="p" @registrado="cargar" />
  </div>
</template>
