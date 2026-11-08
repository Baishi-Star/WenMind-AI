<template>
  <div class="trend-chart">
    <div
      ref="chartContainer"
      class="trend-chart__canvas"
    />
    <el-empty
      v-if="!points.length"
      description="暂无有效评价数据，无法绘制趋势"
      :image-size="80"
    />
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  points: { type: Array, default: () => [] },
})

const chartContainer = ref(null)
let chart = null

const dimensionNames = {
  content: '内容能力',
  organization: '结构能力',
  language: '语言能力',
}
const dimensionColors = {
  content: '#6366f1',
  organization: '#0d9488',
  language: '#a855f7',
}

function buildOption() {
  return {
    animationDuration: 500,
    grid: { left: 38, right: 22, top: 54, bottom: 38 },
    tooltip: {
      trigger: 'axis',
      renderMode: 'richText',
      backgroundColor: 'rgba(17, 24, 39, 0.92)',
      borderWidth: 0,
      textStyle: { color: '#e5e7eb', fontSize: 11 },
      formatter: (params) => {
        const index = params[0]?.dataIndex ?? 0
        const point = props.points[index]
        if (!point) return ''
        const lines = [`作文 #${point.essay_id} · ${point.essay_title}`]
        params.forEach((item) => {
          if (item.value !== null && item.value !== undefined) lines.push(`${item.seriesName}：${item.value}/5`)
        })
        lines.push(`评价来源：${point.review_status === 'teacher_confirmed' ? '教师复核确认' : 'AI 原始诊断（未复核）'}`)
        if (point.rubric_version_id) lines.push(`量规版本：#${point.rubric_version_id}`)
        return lines.join('\n')
      },
    },
    legend: {
      top: 8,
      right: 10,
      itemWidth: 12,
      itemHeight: 7,
      textStyle: { color: '#6b7280', fontSize: 11 },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.points.map((point) => `#${point.essay_id}`),
      axisLine: { lineStyle: { color: '#e4e8f3' } },
      axisTick: { show: false },
      axisLabel: { color: '#7b8499', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      min: 1,
      max: 5,
      interval: 1,
      axisLabel: { color: '#7b8499', fontSize: 11, formatter: '{value}' },
      splitLine: { lineStyle: { color: '#eef1f7', type: 'dashed' } },
    },
    series: [
      ...Object.entries(dimensionNames).map(([key, name]) => ({
        name,
        type: 'line',
        smooth: 0.28,
        symbol: 'circle',
        symbolSize: 7,
        connectNulls: true,
        data: props.points.map((point) => point.scores[key] ?? null),
        lineStyle: { width: 2, color: dimensionColors[key] },
        itemStyle: { color: dimensionColors[key] },
      })),
      {
        name: '三维展示均值',
        type: 'line',
        smooth: 0.28,
        symbol: 'emptyCircle',
        symbolSize: 5,
        data: props.points.map((point) => point.unweighted_average),
        lineStyle: { width: 1.5, type: 'dashed', color: '#9ca3af' },
        itemStyle: { color: '#9ca3af' },
        markLine: {
          silent: true,
          symbol: 'none',
          label: { formatter: '弱项参考线 3.5', color: '#9ca3af', fontSize: 10 },
          lineStyle: { color: '#d1d5db', type: 'dashed' },
          data: [{ yAxis: 3.5 }],
        },
      },
    ],
  }
}

function renderChart() {
  if (!chartContainer.value) return
  if (!chart) chart = echarts.init(chartContainer.value)
  chart.setOption(buildOption(), true)
  chart.resize()
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', handleResize)
})

watch(() => props.points, () => nextTick(renderChart), { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.trend-chart { position: relative; width: 100%; }
.trend-chart__canvas { width: 100%; height: 340px; }
.trend-chart :deep(.el-empty) { position: absolute; inset: 0; background: rgba(255, 255, 255, 0.88); }
</style>