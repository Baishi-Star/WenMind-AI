<template>
  <div class="growth-overview">
    <el-alert
      :type="profile.insufficient_data ? 'warning' : 'info'"
      :closable="false"
      show-icon
      :title="trendTitle"
      :description="profile.notice"
      class="growth-notice"
    />

    <section class="stats-grid">
      <div class="wm-card stat-card">
        <span>有效评价</span><strong>{{ profile.sample_count }}</strong><small>篇作文</small>
      </div>
      <div class="wm-card stat-card">
        <span>教师已复核</span><strong>{{ profile.reviewed_count }}</strong><small>优先作为成长口径</small>
      </div>
      <div class="wm-card stat-card">
        <span>AI 未复核</span><strong>{{ profile.unreviewed_count }}</strong><small>已标记来源</small>
      </div>
      <div class="wm-card stat-card">
        <span>已完成训练</span><strong>{{ profile.training_completed }}</strong><small>待完成 {{ profile.training_pending }}</small>
      </div>
    </section>

    <section class="wm-card capability-section">
      <div class="section-head">
        <h2>能力概览</h2><span>诊断值范围 1–5，不是正式考试分</span>
      </div>
      <div class="capability-grid">
        <article
          v-for="item in profile.capabilities"
          :key="item.key"
          class="capability-card"
          :class="{ 'is-unavailable': !item.available }"
        >
          <div class="capability-card__head">
            <span>{{ item.label }}</span><el-tag
              v-if="!item.available"
              size="small"
              type="info"
              effect="plain"
            >
              待量规支持
            </el-tag>
          </div>
          <strong v-if="item.available">{{ item.score }}<small>/5</small></strong>
          <strong
            v-else
            class="is-empty"
          >未独立计分</strong>
          <div
            v-if="item.available"
            class="capability-bar"
          >
            <span :style="{ width: `${((item.score || 0) / 5) * 100}%` }" />
          </div>
          <p>{{ item.note }}</p>
          <small v-if="item.available">来源：{{ item.source }} · 样本 {{ item.sample_count }}</small>
        </article>
      </div>
      <div class="strength-row">
        <div>
          <span>相对优势</span><el-tag
            v-for="item in profile.strengths"
            :key="item"
            type="success"
            effect="plain"
          >
            {{ item }}
          </el-tag><small v-if="!profile.strengths.length">暂未形成稳定优势</small>
        </div>
        <div>
          <span>重点关注</span><el-tag
            v-for="item in profile.weaknesses"
            :key="item"
            type="warning"
            effect="plain"
          >
            {{ item }}
          </el-tag><small v-if="!profile.weaknesses.length">暂无低于阈值的计分维度</small>
        </div>
      </div>
    </section>

    <section class="wm-card trend-section">
      <div class="section-head">
        <h2>成长趋势</h2>
        <span>{{ profile.insufficient_data ? '数据积累中，趋势参考有限' : '来自真实评价记录' }}</span>
      </div>
      <GrowthTrendChart :points="points" />
      <div class="source-note">
        <span>趋势点 {{ points.length }} 个</span>
        <span v-if="profile.version_mixed">样本跨量规版本 {{ profile.rubric_versions.join('、') }}，变化可能包含规则差异</span>
        <span v-else-if="profile.rubric_versions.length">量规版本 {{ profile.rubric_versions.join('、') }}</span>
      </div>
    </section>

    <section
      v-if="points.length"
      class="wm-card records-section"
    >
      <div class="section-head">
        <h2>评价记录口径</h2><span>教师复核优先，未复核明确标记</span>
      </div>
      <el-table
        :data="points"
        size="small"
      >
        <el-table-column
          label="作文"
          width="85"
        >
          <template #default="{ row }">
            #{{ row.essay_id }}
          </template>
        </el-table-column>
        <el-table-column
          prop="essay_title"
          label="题目"
          min-width="190"
          show-overflow-tooltip
        />
        <el-table-column
          label="内容"
          width="70"
        >
          <template #default="{ row }">
            {{ row.scores.content ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column
          label="结构"
          width="70"
        >
          <template #default="{ row }">
            {{ row.scores.organization ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column
          label="语言"
          width="70"
        >
          <template #default="{ row }">
            {{ row.scores.language ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column
          label="展示均值"
          width="90"
        >
          <template #default="{ row }">
            {{ row.unweighted_average ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column
          label="口径"
          width="135"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.review_status === 'teacher_confirmed' ? 'success' : 'warning'"
            >
              {{ row.review_status === 'teacher_confirmed' ? '教师复核确认' : 'AI 未复核' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="量规"
          width="80"
        >
          <template #default="{ row }">
            #{{ row.rubric_version_id ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column
          label="评价时间"
          width="165"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import GrowthTrendChart from '@/components/GrowthTrendChart.vue'
import { formatDateTime } from '@/utils/format'

const props = defineProps({
  profile: { type: Object, required: true },
  points: { type: Array, default: () => [] },
})

const trendTitle = computed(() => {
  if (props.profile.trend_status === 'no_data') return '数据积累中：暂无成长趋势'
  if (props.profile.insufficient_data) return '数据积累中：样本不足以判断长期趋势'
  return '成长趋势基于真实评价记录'
})
</script>

<style scoped>
.growth-overview { display: grid; gap: 18px; }
.growth-notice { margin-bottom: 0; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.stat-card { padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.stat-card span, .stat-card small { color: var(--wm-text-secondary); font-size: 11px; }
.stat-card strong { font-size: 25px; }
.capability-section, .trend-section, .records-section { padding: 20px; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.section-head h2 { margin: 0; font-size: 17px; }
.section-head span { color: var(--wm-text-secondary); font-size: 11px; }
.capability-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.capability-card { padding: 14px; border: 1px solid var(--wm-border); border-radius: 12px; background: #fff; }
.capability-card.is-unavailable { background: var(--wm-bg-soft); }
.capability-card__head { display: flex; justify-content: space-between; align-items: center; gap: 6px; min-height: 28px; }
.capability-card__head > span { font-size: 12px; font-weight: 600; }
.capability-card strong { display: block; margin: 10px 0 8px; font-size: 24px; color: var(--wm-primary); }
.capability-card strong small { color: var(--wm-text-secondary); font-size: 11px; }
.capability-card strong.is-empty { font-size: 14px; color: var(--wm-text-secondary); }
.capability-bar { height: 6px; border-radius: 99px; background: var(--wm-bg-soft); overflow: hidden; }
.capability-bar span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #6366f1, #99f6e4); }
.capability-card p { margin: 10px 0 6px; color: var(--wm-text-secondary); font-size: 10px; line-height: 1.7; }
.capability-card > small { color: var(--wm-text-secondary); font-size: 9px; }
.strength-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--wm-border); }
.strength-row > div { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.strength-row > div > span { color: var(--wm-text-secondary); font-size: 11px; margin-right: 3px; }
.strength-row small { color: var(--wm-text-secondary); font-size: 10px; }
.source-note { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 10px; color: var(--wm-text-secondary); font-size: 10px; }

@media (max-width: 1250px) {
  .capability-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .stats-grid { grid-template-columns: 1fr 1fr; }
  .capability-grid { grid-template-columns: 1fr 1fr; }
  .strength-row { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .capability-grid, .stats-grid { grid-template-columns: 1fr; }
}
</style>