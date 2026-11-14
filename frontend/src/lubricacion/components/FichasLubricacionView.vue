<script setup>
import { onMounted, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import Pill from '@/shared/ui/Pill.vue'
import { listarCalibres } from '@/inventario'
import { getFichaLubricacion } from '@/lubricacion/services/lubricacionApi'
import FichaLubricacionModal from './FichaLubricacionModal.vue'

const calibres = ref([])
const fichas = ref({}) // calibre_id -> ficha | null
const loading = ref(true)
const q = ref('')
const modal = ref({ abierto: false, calibre: null, ficha: null })

async function cargar() {
  loading.value = true
  const res = await listarCalibres(q.value || undefined).catch(() => [])
  calibres.value = Array.isArray(res) ? res : res.items || []
  await Promise.all(
    calibres.value.map(async (c) => {
      fichas.value[c.id] = await getFichaLubricacion(c.id).catch(() => null)
    }),
  )
  loading.value = false
}
onMounted(cargar)

function editar(c) {
  modal.value = { abierto: true, calibre: c, ficha: fichas.value[c.id] }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Taller · Lubricación"
      titulo="Fichas de lubricación por calibre"
      sub="Cada calibre tiene su ficha: puntos de lubricación con el producto Moebius recomendado y notas técnicas. Se ofrece al abrir una OT de ese calibre."
    >
      <template #acciones>
        <RouterLink :to="{ name: 'moebius' }" class="cr-btn cr-btn-ghost">Catálogo Moebius</RouterLink>
        <RouterLink :to="{ name: 'desviacion-lubricacion' }" class="cr-btn cr-btn-ghost">Desviaciones</RouterLink>
      </template>
    </PageHeader>

    <input v-model="q" class="cr-input mb-4 max-w-sm" placeholder="Buscar calibre…" @input="cargar" />

    <p v-if="loading" class="text-sm text-ink-3">Cargando…</p>
    <p v-else-if="!calibres.length" class="cr-card p-8 text-center text-ink-3">No hay calibres. Créalos en Inventario → Calibres.</p>

    <div v-else class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <button
        v-for="c in calibres"
        :key="c.id"
        class="cr-card p-4 text-left transition hover:border-gold"
        @click="editar(c)"
      >
        <div class="flex items-center justify-between">
          <span class="serif text-base text-ink">{{ c.codigo }}</span>
          <Pill :tone="fichas[c.id] ? 'good' : 'neutral'" :label="fichas[c.id] ? `${fichas[c.id].puntos.length} puntos` : 'sin ficha'" />
        </div>
        <p v-if="c.marca" class="mt-1 text-xs text-ink-3">{{ c.marca }}</p>
        <p class="mt-2 flex items-center gap-1 text-xs text-gold-strong"><CrIcon name="edit" :size="12" /> Editar ficha</p>
      </button>
    </div>

    <FichaLubricacionModal
      v-if="modal.calibre"
      v-model="modal.abierto"
      :calibre="modal.calibre"
      :ficha="modal.ficha"
      @guardado="cargar"
    />
  </div>
</template>
