<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { listarSucursales } from '@/sucursales'
import { getTecnico, setEstadoTecnico } from '@/tecnicos/services/tecnicosApi'
import TecnicoFormModal from './TecnicoFormModal.vue'
import EsquemaCostoModal from './EsquemaCostoModal.vue'

const route = useRoute()
const id = Number(route.params.id)

const t = ref(null)
const sucursales = ref([])
const modalForm = ref(false)
const modalCosto = ref(false)

const sucursalNombre = (sid) => sucursales.value.find((s) => s.id === sid)?.nombre ?? `#${sid}`

async function cargar() {
  t.value = await getTecnico(id)
}
onMounted(async () => {
  sucursales.value = (await listarSucursales().catch(() => ({ items: [] }))).items
  cargar()
})

async function cambiarEstado() {
  const inactivar = t.value.estado === 'activo'
  if (inactivar && !(await confirm({
    title: `Inactivar a ${t.value.nombre}`,
    message: 'El técnico queda inactivo y sale de la asignación de órdenes de trabajo. Su historial y bonos se conservan.',
    confirmLabel: 'Inactivar', tone: 'danger',
  }))) return
  try {
    await setEstadoTecnico(id, inactivar ? 'inactivo' : 'activo')
    toast.success(inactivar ? 'Técnico inactivado' : 'Técnico reactivado')
    cargar()
  } catch (e) {
    toast.error(e.status === 403 ? 'Requiere Técnico Jefe o Gerencia General.' : e.message)
  }
}

const fmt = (v) => (v == null ? '—' : `$ ${Number(v).toLocaleString()}`)
</script>

<template>
  <div v-if="t">
    <PageHeader eyebrow="Técnicos · Ficha" :titulo="t.nombre" :sub="t.usuario_id ? 'Con acceso al sistema' : 'Sin acceso al sistema'">
      <template #acciones>
        <RouterLink :to="{ name: 'tecnicos' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Técnicos</RouterLink>
        <button class="cr-btn cr-btn-ghost" @click="modalForm = true">Editar</button>
        <button class="cr-btn cr-btn-primary" @click="modalCosto = true">Fijar costo interno</button>
        <button v-if="t.estado === 'activo'" class="cr-btn cr-btn-danger" @click="cambiarEstado">Inactivar</button>
        <button v-else class="cr-btn cr-btn-ghost" @click="cambiarEstado">Reactivar</button>
      </template>
    </PageHeader>

    <div class="mb-6 flex flex-wrap items-center gap-3">
      <Pill :tone="t.estado === 'activo' ? 'good' : 'neutral'" :label="t.estado" />
      <span v-for="e in t.especialidades" :key="e" class="rounded-full bg-surface-sunk px-2.5 py-0.5 text-xs text-ink-2">{{ e }}</span>
    </div>

    <div class="grid gap-5 lg:grid-cols-2">
      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Datos</h2>
        <dl class="mt-4 space-y-2.5 text-sm">
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Especialidades</dt><dd class="text-right">{{ t.especialidades.join(', ') || '—' }}</dd></div>
          <div class="flex justify-between gap-4">
            <dt class="text-ink-3">Sucursales</dt>
            <dd class="text-right">{{ t.sucursal_ids.map(sucursalNombre).join(', ') || '—' }}</dd>
          </div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Usuario vinculado</dt><dd>{{ t.usuario_id ? `#${t.usuario_id}` : '—' }}</dd></div>
        </dl>
        <div v-if="t.certificaciones" class="mt-4 border-t border-hairline-soft pt-3">
          <p class="cr-label mb-1">Certificaciones y formación</p>
          <p class="whitespace-pre-line text-sm text-ink-2">{{ t.certificaciones }}</p>
        </div>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Costo interno de mano de obra</h2>
        <template v-if="t.costos_visibles">
          <template v-if="t.costo_vigente">
            <p class="mt-4 serif text-3xl text-gold-strong tabular-nums">
              $ {{ Number(t.costo_vigente.tarifa_hora).toLocaleString() }}
              <span class="text-base font-normal text-ink-2">/ hora</span>
            </p>
            <dl class="mt-3 space-y-2 text-sm">
              <div class="flex justify-between gap-4"><dt class="text-ink-3">Sueldo mensual</dt><dd class="tabular-nums">{{ fmt(t.costo_vigente.sueldo_mensual) }}</dd></div>
              <div class="flex justify-between gap-4"><dt class="text-ink-3">Horas estándar / mes</dt><dd class="tabular-nums">{{ Number(t.costo_vigente.horas_estandar_mes) }}</dd></div>
              <div class="flex justify-between gap-4"><dt class="text-ink-3">Vigente desde</dt><dd class="tabular-nums">{{ t.costo_vigente.vigente_desde }}</dd></div>
            </dl>
            <p class="mt-3 text-xs text-ink-3">
              El costo de mano de obra de una orden de trabajo = tarifa × horas registradas (o × tiempo estimado del tipo de reparación). Nunca se muestra al cliente.
            </p>
          </template>
          <div v-else class="mt-4 rounded-xl border border-dashed border-hairline p-4 text-sm text-ink-2">
            Este técnico aún no tiene un esquema de costo. Fíjalo para poder costear sus órdenes de trabajo.
            <button class="mt-2 block cr-btn cr-btn-ghost" @click="modalCosto = true">Fijar costo interno</button>
          </div>
        </template>
        <p v-else class="mt-4 flex items-center gap-2 text-sm text-ink-3">
          <CrIcon name="lock" :size="14" /> Restringido a roles administrativos.
        </p>
      </section>

      <section class="cr-card p-6 lg:col-span-2">
        <h2 class="serif text-lg text-ink">Productividad y bonos</h2>
        <p class="mt-2 text-sm text-ink-3">
          Las órdenes de trabajo completadas, el margen generado y el bono alcanzado se ven en
          <RouterLink :to="{ name: 'productividad' }" class="text-gold-strong underline">Productividad</RouterLink> y
          <RouterLink :to="{ name: 'bonos-periodo' }" class="text-gold-strong underline">Bonos por periodo</RouterLink>.
          La acumulación se activa cuando el taller registra órdenes de trabajo (feature 008).
        </p>
      </section>
    </div>

    <TecnicoFormModal v-model="modalForm" :tecnico="t" @guardado="cargar" />
    <EsquemaCostoModal v-model="modalCosto" :tecnico="t" @guardado="cargar" />
  </div>
</template>
