<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/shared/ui/PageHeader.vue'
import Pill from '@/shared/ui/Pill.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'
import { toast } from '@/shared/ui/toast'
import { getCliente, setEstadoCliente } from '@/clientes/services/clientesApi'
import ClienteFormModal from './ClienteFormModal.vue'

const route = useRoute()
const id = Number(route.params.id)
const c = ref(null)
const modalForm = ref(false)

async function cargar() {
  c.value = await getCliente(id)
}
onMounted(cargar)

async function cambiarEstado() {
  const inactivar = c.value.estado === 'activo'
  if (inactivar && !(await confirm({
    title: `Inactivar a ${c.value.nombre}`,
    message: 'El cliente queda inactivo y sale de los selectores. Su historial se conserva.',
    confirmLabel: 'Inactivar', tone: 'danger',
  }))) return
  try {
    await setEstadoCliente(id, inactivar ? 'inactivo' : 'activo')
    toast.success(inactivar ? 'Cliente inactivado' : 'Cliente reactivado')
    cargar()
  } catch (e) {
    toast.error(e.message)
  }
}

const beneficios = (b) => Object.entries(b || {})
</script>

<template>
  <div v-if="c">
    <PageHeader eyebrow="Clientes · Ficha" :titulo="c.nombre" :sub="`${c.tipo === 'juridica' ? 'Persona jurídica' : 'Persona natural'} · ${c.identificacion} · ${c.numero_afiliado}`">
      <template #acciones>
        <RouterLink :to="{ name: 'clientes' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Clientes</RouterLink>
        <RouterLink :to="{ name: 'cliente-historial', params: { id } }" class="cr-btn cr-btn-ghost">Historial</RouterLink>
        <button class="cr-btn cr-btn-primary" @click="modalForm = true">Editar</button>
        <button v-if="c.estado === 'activo'" class="cr-btn cr-btn-danger" @click="cambiarEstado">Inactivar</button>
        <button v-else class="cr-btn cr-btn-ghost" @click="cambiarEstado">Reactivar</button>
      </template>
    </PageHeader>

    <div class="mb-6 flex flex-wrap items-center gap-3">
      <Pill :tone="c.estado === 'activo' ? 'good' : 'neutral'" :label="c.estado" />
      <span
        v-if="c.nivel_nombre"
        class="inline-flex items-center rounded-full border border-gold/50 bg-gold-pale px-3 py-0.5 text-xs font-medium text-gold-strong"
      >Fidelización: {{ c.nivel_nombre }}</span>
    </div>

    <div class="grid gap-5 lg:grid-cols-2">
      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Datos</h2>
        <dl class="mt-4 space-y-2.5 text-sm">
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Teléfono</dt><dd>{{ c.telefono || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Email</dt><dd>{{ c.email || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Dirección</dt><dd class="text-right">{{ c.direccion || '—' }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-ink-3">Fecha de nacimiento</dt><dd class="tabular-nums">{{ c.fecha_nacimiento || '—' }}</dd></div>
        </dl>
        <div v-if="c.preferencias?.marcas?.length" class="mt-4 border-t border-hairline-soft pt-3">
          <p class="cr-label mb-1">Marcas de interés</p>
          <span v-for="m in c.preferencias.marcas" :key="m" class="mr-1 inline-block rounded-full bg-surface-sunk px-2 py-0.5 text-xs text-ink-2">{{ m }}</span>
        </div>
        <div v-if="c.notas" class="mt-4 border-t border-hairline-soft pt-3">
          <p class="cr-label mb-1">Notas del vendedor</p>
          <p class="whitespace-pre-line text-sm text-ink-2">{{ c.notas }}</p>
        </div>
      </section>

      <section class="cr-card p-6">
        <h2 class="serif text-lg text-ink">Fidelización y beneficios</h2>
        <p class="mt-3 text-sm">
          Nivel actual:
          <span class="font-medium text-gold-strong">{{ c.nivel_nombre || 'Sin nivel' }}</span>
        </p>
        <ul v-if="beneficios(c.beneficios_nivel).length" class="mt-2 space-y-1 text-sm text-ink-2">
          <li v-for="[k, v] in beneficios(c.beneficios_nivel)" :key="k" class="flex justify-between gap-4">
            <span>{{ k.replace(/_/g, ' ') }}</span>
            <span class="tabular-nums">{{ typeof v === 'number' && v < 1 ? `${(v * 100).toFixed(0)} %` : v }}</span>
          </li>
        </ul>
        <p v-else class="mt-2 text-sm text-ink-3">El nivel base no tiene beneficios asociados.</p>

        <div class="mt-4 border-t border-hairline-soft pt-3">
          <p class="cr-label mb-1.5">Cupones activos</p>
          <div v-if="c.cupones_activos.length" class="flex flex-wrap gap-1.5">
            <span
              v-for="cu in c.cupones_activos"
              :key="cu.id"
              class="inline-flex items-center gap-1 rounded-full border border-gold/40 bg-gold-pale px-2.5 py-0.5 text-xs text-gold-strong"
              :title="cu.vigencia_fin ? `Vence ${cu.vigencia_fin}` : ''"
            >
              <CrIcon name="tag" :size="12" /> {{ cu.codigo }}
              · {{ cu.tipo === 'porcentaje' ? `${(cu.valor * 100).toFixed(0)} %` : `$ ${Number(cu.valor).toLocaleString()}` }}
            </span>
          </div>
          <p v-else class="text-sm text-ink-3">Sin cupones activos.</p>
        </div>

        <p class="mt-4 flex items-center gap-1.5 border-t border-hairline-soft pt-3 text-xs text-ink-3">
          <CrIcon name="circle-check" :size="12" class="text-good" />
          Consentimiento de datos {{ c.consentimiento_vigente?.aceptado ? `aceptado (v${c.consentimiento_vigente.version_texto})` : 'no registrado' }}.
        </p>
      </section>
    </div>

    <ClienteFormModal v-model="modalForm" :cliente="c" @guardado="cargar" />
  </div>
</template>
