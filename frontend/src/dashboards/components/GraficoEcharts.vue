<script setup>
/**
 * Wrapper único de `vue-echarts` (Principio XI: sin otra librería de gráficos).
 * Dibuja barras / pastel(dona) / líneas según `tipo`, con el tratamiento visual
 * del Principio XI: marcas finas, relleno tenue, grilla mínima, remate en oro.
 */
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent])

const props = defineProps({
  tipo: { type: String, required: true }, // barras | pastel | lineas
  categorias: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] }, // [{ nombre, datos }]
  altura: { type: String, default: '320px' },
})

// Paleta categórica fija (Principio XI: primary + oro reservado + verde + neutral).
const PALETA = ['#2E3D5F', '#8A6D2B', '#047857', '#94A3B8', '#6B7C99', '#D8B876']
const INK_3 = '#8B909A'
const HAIRLINE = '#E5E0D3'

const ejeTexto = { color: INK_3, fontFamily: "'Hanken Grotesk', sans-serif", fontSize: 11 }

const opciones = computed(() => {
  if (props.tipo === 'pastel') {
    const datos = (props.series[0]?.datos || []).map((v, i) => ({ name: props.categorias[i], value: v }))
    return {
      color: PALETA,
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, textStyle: ejeTexto, itemWidth: 10, itemHeight: 10 },
      series: [{
        type: 'pie',
        radius: ['45%', '72%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { color: INK_3, fontFamily: ejeTexto.fontFamily, fontSize: 11 },
        data: datos,
      }],
    }
  }

  const esLineas = props.tipo === 'lineas'
  return {
    color: PALETA,
    tooltip: { trigger: 'axis' },
    legend: props.series.length > 1 ? { top: 0, textStyle: ejeTexto, itemWidth: 10, itemHeight: 10 } : undefined,
    grid: { left: 8, right: 12, top: props.series.length > 1 ? 32 : 12, bottom: 28, containLabel: true },
    xAxis: {
      type: 'category',
      data: props.categorias,
      axisLine: { lineStyle: { color: HAIRLINE } },
      axisTick: { show: false },
      axisLabel: { ...ejeTexto, hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: HAIRLINE, type: 'dashed' } },
      axisLabel: ejeTexto,
    },
    series: props.series.map((s, i) => esLineas ? ({
      name: s.nombre,
      type: 'line',
      data: s.datos,
      smooth: false,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2, color: i === 0 ? '#8A6D2B' : PALETA[i] },
      itemStyle: { color: i === 0 ? '#8A6D2B' : PALETA[i] },
      areaStyle: { color: i === 0 ? '#8A6D2B' : PALETA[i], opacity: 0.06 },
    }) : ({
      name: s.nombre,
      type: 'bar',
      data: s.datos,
      barMaxWidth: 28,
      itemStyle: { color: PALETA[i], borderRadius: [3, 3, 0, 0] },
    })),
  }
})
</script>

<template>
  <p v-if="!categorias.length" class="flex items-center justify-center rounded-lg bg-surface-sunk text-xs text-ink-3" :style="{ height: altura }">
    Sin datos para los filtros elegidos
  </p>
  <VChart v-else :option="opciones" autoresize :style="{ height: altura }" />
</template>
