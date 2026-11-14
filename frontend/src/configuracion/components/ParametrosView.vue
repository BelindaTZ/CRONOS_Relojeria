<script setup>
import { ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { getParametro, setParametro } from '@/configuracion/services/configuracionApi'

// parámetros conocidos hasta ahora (cada feature dueña añade los suyos)
const CONOCIDOS = [
  { clave: 'proveedores_n_recepciones_indicador', label: 'Recepciones para el indicador de plazos', tipo: 'numero' },
  { clave: 'oc_horas_min_cancelacion', label: 'Horas mínimas para cancelar una orden', tipo: 'numero' },
  { clave: 'stock_maximo_modelo', label: 'Stock máximo recomendado por modelo', tipo: 'numero' },
  { clave: 'umbral_reposicion_relojes', label: 'Umbral de alerta de reposición de relojes', tipo: 'numero' },
  { clave: 'umbral_reposicion_piezas', label: 'Margen extra sobre el mínimo para alertar piezas', tipo: 'numero' },
  { clave: 'umbral_caducidad_dias', label: 'Días para alertar caducidad próxima de un lote', tipo: 'numero' },
  { clave: 'horas_productivas_estandar_mes', label: 'Horas productivas estándar al mes (tarifa horaria del técnico)', tipo: 'numero' },
  { clave: 'tiempo_estimado_horas_default', label: 'Horas estimadas por defecto de una reparación', tipo: 'numero' },
  { clave: 'margen_minimo', label: 'Margen mínimo protegido (mejor edítalo en Clientes · Margen mínimo)', tipo: 'json' },
  { clave: 'margen_minimo_politica', label: 'Política del margen mínimo (bloquear | autorizar)', tipo: 'texto' },
  { clave: 'monto_max_consumidor_final', label: 'Monto máximo de venta a «consumidor final» (sin ficha)', tipo: 'monto' },
  { clave: 'fidelizacion_ventana_meses', label: 'Ventana por defecto (meses) para el nivel de fidelización', tipo: 'numero' },
  { clave: 'churn_piso_dias', label: 'Riesgo de abandono — piso mínimo de días de silencio', tipo: 'numero' },
  { clave: 'churn_factor_cadencia', label: 'Riesgo de abandono — factor sobre la cadencia propia del cliente', tipo: 'numero' },
  { clave: 'churn_min_transacciones', label: 'Riesgo de abandono — mínimo de transacciones para tener patrón', tipo: 'numero' },
  { clave: 'churn_ventana_analisis_meses', label: 'Riesgo de abandono — ventana de análisis (meses)', tipo: 'numero' },
  { clave: 'citas_ventana_solape_min', label: 'Citas — minutos de tolerancia para la advertencia de solape', tipo: 'numero' },
  { clave: 'margen_objetivo_servicio', label: 'Servicio técnico — margen objetivo (fracción; 0.5 = 50 %). Ámbito global, por tipo de servicio o sucursal', tipo: 'porcentaje' },
  { clave: 'garantia_tienda_dias_default', label: 'Servicio técnico / venta — garantía de tienda por defecto (días)', tipo: 'numero' },
  { clave: 'garantia_fabrica_dias_default', label: 'Venta — garantía de fábrica por defecto (días; se puede fijar por marca)', tipo: 'numero' },
  { clave: 'umbral_merma_autorizacion', label: 'Mermas — monto a partir del cual la baja definitiva exige autorización de Gerencia General', tipo: 'monto' },
  { clave: 'costo_traslado_venta', label: 'Traslados — cargo al cliente cuando pide expresamente traer un reloj de otra sucursal', tipo: 'monto' },
]

const clave = ref(CONOCIDOS[0].clave)
const param = ref(null)
const errorMsg = ref('')

const modal = ref({ abierto: false, guardando: false, valor: '', error: '' })

async function ver() {
  errorMsg.value = ''
  param.value = null
  try {
    param.value = await getParametro(clave.value.trim())
  } catch (e) {
    errorMsg.value = e.message
  }
}

function abrirEdicion() {
  modal.value = { abierto: true, guardando: false, valor: param.value?.valor_vigente ?? '', error: '' }
}
async function guardar() {
  modal.value.error = ''
  modal.value.guardando = true
  try {
    const r = await setParametro(clave.value.trim(), {
      valor: Number(modal.value.valor),
      tipo: 'numero',
      ambito_tipo: 'global',
    })
    toast.success(
      `Guardado. Recálculo: ${r.recalculo.entidades_abiertas_afectadas} entidades abiertas · ${r.recalculo.consumidores.length} consumidores.`,
    )
    modal.value.abierto = false
    ver()
  } catch (e) {
    modal.value.error = e.status === 403 ? 'Solo Gerencia General o un delegado.' : e.message
  } finally {
    modal.value.guardando = false
  }
}
</script>

<template>
  <div>
    <PageHeader eyebrow="Sistema · Configuración" titulo="Parámetros" sub="Valores de negocio con vigencia. Cambiarlos recalcula en cascada lo abierto; lo emitido y los periodos cerrados se conservan.">
      <template #acciones>
        <RouterLink :to="{ name: 'configuracion' }" class="cr-btn cr-btn-ghost">Catálogos</RouterLink>
        <RouterLink :to="{ name: 'auditoria' }" class="cr-btn cr-btn-ghost">Auditoría</RouterLink>
      </template>
    </PageHeader>

    <div class="cr-card max-w-2xl p-6">
      <label class="block space-y-1">
        <span class="cr-label">Parámetro</span>
        <div class="flex gap-2">
          <select v-model="clave" class="cr-input">
            <option v-for="p in CONOCIDOS" :key="p.clave" :value="p.clave">{{ p.label }}</option>
          </select>
          <button class="cr-btn cr-btn-ghost" @click="ver">Ver</button>
        </div>
      </label>

      <p v-if="errorMsg" class="mt-3 text-sm text-bad">{{ errorMsg }}</p>

      <div v-if="param" class="mt-5 space-y-4">
        <div class="flex items-baseline justify-between rounded-xl border border-hairline bg-surface-sunk/50 px-4 py-3">
          <span class="text-sm text-ink-3">Valor vigente</span>
          <span class="serif text-2xl text-gold-strong tabular-nums">{{ param.valor_vigente ?? '—' }}</span>
        </div>
        <button class="cr-btn cr-btn-primary" @click="abrirEdicion">Fijar valor nuevo</button>

        <div v-if="param.historial.length">
          <p class="cr-label mb-2">Historial</p>
          <ul class="space-y-1.5 text-sm text-ink-2">
            <li v-for="(h, i) in param.historial" :key="i" class="flex items-center gap-2">
              <CrIcon name="clock" :size="13" class="text-ink-3" />
              <span class="tabular-nums">{{ h.valor }}</span>
              <span class="text-ink-3">— desde {{ new Date(h.vigente_desde).toLocaleString() }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <FormModal v-model="modal.abierto" titulo="Fijar valor nuevo" subtitulo="Dispara el recálculo de los consumidores registrados." :guardando="modal.guardando" ancho="max-w-md" @guardar="guardar">
      <FormField label="Nuevo valor" required wide><input v-model="modal.valor" type="number" class="cr-input" required /></FormField>
      <p v-if="modal.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ modal.error }}</p>
    </FormModal>
  </div>
</template>
