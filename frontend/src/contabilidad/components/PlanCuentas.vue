<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { getPlanCuentas } from '@/contabilidad/services/contabilidadApi'

const cuentas = ref([])
const loading = ref(true)
const q = ref('')

onMounted(async () => {
  cuentas.value = await getPlanCuentas().catch(() => [])
  loading.value = false
})

const TIPO_LABEL = { activo: 'Activo', pasivo: 'Pasivo', patrimonio: 'Patrimonio', ingreso: 'Ingreso', gasto: 'Gasto/Costo' }
const filtradas = computed(() => {
  const s = q.value.trim().toLowerCase()
  if (!s) return cuentas.value
  return cuentas.value.filter((c) => `${c.codigo} ${c.nombre}`.toLowerCase().includes(s))
})
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Contabilidad"
      titulo="Plan de cuentas"
      sub="Estructura NIIF para PYMES simplificada. Solo las cuentas imputables reciben movimientos del libro diario."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'libro-diario' }" class="cr-btn cr-btn-ghost"><CrIcon name="arrow-left" :size="15" /> Libro diario</RouterLink>
      </template>
    </PageHeader>

    <input v-model="q" class="cr-input mb-4 max-w-sm" placeholder="Buscar código o nombre…" />

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <div v-else class="cr-card overflow-hidden p-0">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-table-head-border bg-surface-head text-left">
            <th class="px-4 py-2 font-medium">Código</th>
            <th class="px-4 py-2 font-medium">Nombre</th>
            <th class="px-4 py-2 font-medium">Tipo</th>
            <th class="px-4 py-2 font-medium">Imputable</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in filtradas" :key="c.id" class="border-b border-hairline-soft">
            <td class="px-4 py-2 tabular-nums" :class="c.imputable ? 'pl-8 text-ink-2' : 'font-medium text-ink'">{{ c.codigo }}</td>
            <td class="px-4 py-2" :class="c.imputable ? 'text-ink-2' : 'font-medium text-ink'">{{ c.nombre }}</td>
            <td class="px-4 py-2 text-ink-3">{{ TIPO_LABEL[c.tipo] }}</td>
            <td class="px-4 py-2"><CrIcon v-if="c.imputable" name="check" :size="14" class="text-good" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
