<template>
  <div>
    <PageHeader
      title="评价复核"
      subtitle="查看授权班级的真实 AI 评价与诊断结果；正式修改需通过学生申诉复核形成可追溯记录。"
    >
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadEvaluations"
        >
          刷新
        </el-button>
      </template>
    </PageHeader>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="复核入口说明"
      description="本页展示 AI 原始评价。需要修改分数、反馈文字或新增教师反馈时，请进入“申诉管理”处理对应申诉，系统会保留原始记录。"
      class="notice"
    />
    <section class="wm-card list-card">
      <el-table
        v-loading="loading"
        :data="evaluations"
        empty-text="暂无可见评价"
      >
        <el-table-column
          prop="id"
          label="评价"
          width="85"
        >
          <template #default="{ row }">
            #{{ row.id }}
          </template>
        </el-table-column>
        <el-table-column
          label="作文"
          width="110"
        >
          <template #default="{ row }">
            作文 #{{ row.essay_id }}<div class="muted">
              v{{ row.essay_version }}
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="110"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.status === 'completed' ? 'success' : 'info'"
            >
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="AI 诊断维度"
          min-width="240"
        >
          <template #default="{ row }">
            <span
              v-for="item in row.dimension_scores"
              :key="item.dimension"
              class="dimension-chip"
            >
              {{ dimensionLabel(item.dimension) }} {{ item.original_score ?? '—' }}/{{ item.max_score }}
              <small v-if="item.final_score !== null">→ 教师 {{ item.final_score }}</small>
            </span>
          </template>
        </el-table-column>
        <el-table-column
          prop="rubric_version_id"
          label="量规"
          width="90"
        >
          <template #default="{ row }">
            #{{ row.rubric_version_id ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column
          label="完成时间"
          width="170"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.report?.completed_at || row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="175"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              size="small"
              @click="openDetail(row.id)"
            >
              查看评价
            </el-button>
            <el-button
              text
              type="primary"
              size="small"
              @click="router.push('/teacher/appeals')"
            >
              申诉复核
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-drawer
      v-model="drawerVisible"
      size="680px"
      title="AI 原始评价详情"
    >
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-descriptions
            :column="2"
            border
          >
            <el-descriptions-item label="评价编号">
              #{{ detail.id }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              {{ detail.status }}
            </el-descriptions-item>
            <el-descriptions-item label="执行模式">
              {{ detail.report?.execution_mode || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="质量审核">
              {{ detail.report?.quality_status || '—' }}
            </el-descriptions-item>
          </el-descriptions>
          <div class="detail-dimensions">
            <div
              v-for="item in detail.dimension_scores"
              :key="item.dimension"
            >
              <span>{{ dimensionLabel(item.dimension) }}</span>
              <strong>{{ item.original_score ?? '—' }}/{{ item.max_score }}</strong>
              <small>教师最终值 {{ item.final_score ?? '未复核' }}</small>
            </div>
          </div>
          <el-alert
            v-if="detail.report?.overall_summary"
            type="info"
            :closable="false"
            title="AI 综合反馈"
            :description="detail.report.overall_summary"
            class="summary-alert"
          />
          <article
            v-for="item in detail.feedback_items"
            :key="item.id"
            class="feedback-row"
          >
            <el-tag
              size="small"
              effect="plain"
            >
              {{ dimensionLabel(item.dimension) }}
            </el-tag>
            <span>{{ item.content }}</span>
            <blockquote
              v-for="(evidence, index) in item.evidence"
              :key="index"
            >
              “{{ evidence.quote }}”
            </blockquote>
          </article>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import PageHeader from '@/components/PageHeader.vue'
import { fetchEvaluation, fetchEvaluations } from '@/api/evaluation'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const evaluations = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

function dimensionLabel(value) { return { content: '内容', organization: '结构', language: '语言' }[value] || value }

async function loadEvaluations() {
  loading.value = true
  try {
    const response = await fetchEvaluations({ page: 1, page_size: 50 })
    evaluations.value = response.data.items
  } finally {
    loading.value = false
  }
}

async function openDetail(evaluationId) {
  drawerVisible.value = true
  detailLoading.value = true
  try {
    const response = await fetchEvaluation(evaluationId)
    detail.value = response.data
  } finally {
    detailLoading.value = false
  }
}

onMounted(loadEvaluations)
</script>

<style scoped>
.notice { margin-bottom: 18px; }
.list-card { padding: 20px; }
.muted { color: var(--wm-text-secondary); font-size: 11px; }
.dimension-chip { display: inline-block; margin: 2px 6px 2px 0; padding: 3px 8px; border-radius: 999px; background: var(--wm-bg-soft); font-size: 11px; }
.dimension-chip small { color: var(--wm-primary); margin-left: 4px; }
.detail-dimensions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 16px 0; }
.detail-dimensions div { padding: 12px; border-radius: 9px; background: var(--wm-bg-soft); }
.detail-dimensions span, .detail-dimensions small { display: block; color: var(--wm-text-secondary); font-size: 11px; }
.detail-dimensions strong { color: var(--wm-primary); font-size: 22px; }
.summary-alert { margin-bottom: 14px; }
.feedback-row { padding: 12px; margin-bottom: 9px; border: 1px solid var(--wm-border); border-radius: 9px; font-size: 13px; line-height: 1.8; }
.feedback-row > span { margin-left: 8px; }
.feedback-row blockquote { margin: 7px 0 0; padding-left: 10px; border-left: 3px solid var(--wm-primary-soft); color: var(--wm-text-secondary); font-size: 12px; }
</style>