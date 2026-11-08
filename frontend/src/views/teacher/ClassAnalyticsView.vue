<template>
  <div>
    <PageHeader
      title="班级学情分析"
      subtitle="基于授权班级真实作文评价、教师复核、确认争议与训练数据汇总。"
    >
      <template #actions>
        <el-select
          v-model="selectedClassId"
          placeholder="选择班级"
          style="width: 210px"
          :loading="classesLoading"
          @change="loadAnalytics"
        >
          <el-option
            v-for="item in classes"
            :key="item.id"
            :value="item.id"
            :label="item.name"
          />
        </el-select>
        <el-button
          :loading="loading"
          @click="loadAnalytics"
        >
          刷新
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="analytics?.insufficient_data"
      type="warning"
      :closable="false"
      show-icon
      title="数据积累中"
      :description="analytics.notice"
      class="notice"
    />
    <el-alert
      v-else-if="analytics"
      type="info"
      :closable="false"
      show-icon
      title="统计口径"
      :description="analytics.notice"
      class="notice"
    />

    <el-empty
      v-if="!loading && !analytics"
      description="暂无可分析班级"
    />
    <div
      v-else
      v-loading="loading"
    >
      <section
        v-if="analytics"
        class="stats-grid"
      >
        <div class="wm-card stat-card">
          <span>班级学生</span><strong>{{ analytics.student_count }}</strong><small>{{ analytics.class_name }}</small>
        </div>
        <div class="wm-card stat-card">
          <span>有效作文</span><strong>{{ analytics.essay_count }}</strong><small>篇</small>
        </div>
        <div class="wm-card stat-card">
          <span>有效评价</span><strong>{{ analytics.evaluation_count }}</strong><small>条</small>
        </div>
        <div class="wm-card stat-card">
          <span>教师已复核</span><strong>{{ analytics.reviewed_evaluation_count }}</strong><small>优先统计口径</small>
        </div>
      </section>

      <div
        v-if="analytics"
        class="analysis-grid"
      >
        <section class="wm-card panel">
          <div class="section-head">
            <h2>维度能力分布</h2><span>诊断值 1–5 · 薄弱为低于 3.5</span>
          </div>
          <div
            v-for="dimension in dimensions"
            :key="dimension.key"
            class="dimension-row"
          >
            <div class="dimension-row__head">
              <span>{{ dimension.label }}</span>
              <strong>{{ analytics.dimension_averages[dimension.key] ?? '—' }}<small>/5</small></strong>
            </div>
            <div class="dimension-row__meta">
              <span>薄弱比例 <strong>{{ analytics.dimension_weak_ratios[dimension.key] ?? 0 }}%</strong></span>
              <span>样本 {{ analytics.dimension_distribution[dimension.key]?.total ?? 0 }}</span>
            </div>
            <div class="distribution-bar">
              <span
                class="is-low"
                :style="{ width: distributionWidth(dimension.key, 'low') }"
              />
              <span
                class="is-basic"
                :style="{ width: distributionWidth(dimension.key, 'basic') }"
              />
              <span
                class="is-good"
                :style="{ width: distributionWidth(dimension.key, 'good') }"
              />
            </div>
            <div class="distribution-legend">
              <span>待提升 {{ analytics.dimension_distribution[dimension.key]?.low ?? 0 }}</span>
              <span>基本达成 {{ analytics.dimension_distribution[dimension.key]?.basic ?? 0 }}</span>
              <span>良好 {{ analytics.dimension_distribution[dimension.key]?.good ?? 0 }}</span>
            </div>
          </div>
        </section>

        <section class="wm-card panel">
          <div class="section-head">
            <h2>班级高频问题与争议</h2><span>教师确认标签优先</span>
          </div>
          <el-empty
            v-if="!analytics.top_confirmed_issues.length && !Object.keys(analytics.feedback_problem_counts).length"
            description="暂无已确认问题或反馈问题"
            :image-size="65"
          />
          <div
            v-for="item in analytics.top_confirmed_issues"
            :key="item.tag_code"
            class="issue-row"
          >
            <span>{{ item.label }}</span><strong>{{ item.count }}</strong>
          </div>
          <div
            v-if="Object.keys(analytics.feedback_problem_counts).length"
            class="problem-counts"
          >
            <h3>AI 反馈问题条目分布（参考）</h3>
            <div
              v-for="(count, dimension) in analytics.feedback_problem_counts"
              :key="dimension"
            >
              <span>{{ dimensionLabel(dimension) }}</span><strong>{{ count }}</strong>
            </div>
          </div>
          <div class="appeal-status">
            <span
              v-for="(count, status) in analytics.appeal_status_counts"
              :key="status"
            >{{ statusLabel(status) }}：{{ count }}</span>
          </div>
          <p class="panel-note">
            确认争议数来自教师复核记录，不能直接解释为模型错误率。
          </p>
        </section>

        <section
          v-if="analytics"
          class="wm-card panel students-panel"
        >
          <div class="section-head">
            <h2>学生个体成长</h2><span>点击查看单人成长详情</span>
          </div>
          <el-table
            :data="analytics.students"
            size="small"
            empty-text="班级暂无学生"
          >
            <el-table-column
              prop="student_name"
              label="学生"
              min-width="120"
            />
            <el-table-column
              label="有效评价"
              width="90"
            >
              <template #default="{ row }">
                {{ row.sample_count }}<span
                  v-if="row.needs_data"
                  class="muted"
                > · 积累中</span>
              </template>
            </el-table-column>
            <el-table-column
              label="已复核"
              width="80"
            >
              <template #default="{ row }">
                {{ row.reviewed_count }}
              </template>
            </el-table-column>
            <el-table-column
              label="内容"
              width="65"
            >
              <template #default="{ row }">
                {{ row.averages.content ?? '—' }}
              </template>
            </el-table-column>
            <el-table-column
              label="结构"
              width="65"
            >
              <template #default="{ row }">
                {{ row.averages.organization ?? '—' }}
              </template>
            </el-table-column>
            <el-table-column
              label="语言"
              width="65"
            >
              <template #default="{ row }">
                {{ row.averages.language ?? '—' }}
              </template>
            </el-table-column>
            <el-table-column
              label="主要弱项"
              width="110"
            >
              <template #default="{ row }">
                {{ row.weakest_dimension ? dimensionLabel(row.weakest_dimension) : '数据不足' }}
              </template>
            </el-table-column>
            <el-table-column
              label="操作"
              width="120"
              fixed="right"
            >
              <template #default="{ row }">
                <el-button
                  text
                  type="primary"
                  size="small"
                  @click="openStudent(row.student_id)"
                >
                  查看成长
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section
          v-if="analytics"
          class="wm-card panel"
        >
          <div class="section-head">
            <h2>个性化教学建议</h2><span>规则生成 · 非 AI 结论</span>
          </div>
          <el-empty
            v-if="!analytics.teaching_suggestions.length"
            description="样本积累中，暂无教学建议"
            :image-size="65"
          />
          <article
            v-for="(item, index) in analytics.teaching_suggestions"
            :key="index"
            class="suggestion-card"
          >
            <strong>{{ item.title }}</strong>
            <p>{{ item.description }}</p>
            <small>{{ item.basis }}</small>
          </article>
          <p class="panel-note">
            量规版本：{{ analytics.rubric_versions.join('、') || '暂无' }}；跨版本差异可能影响趋势解释。
          </p>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import PageHeader from '@/components/PageHeader.vue'
import { fetchTeacherClasses } from '@/api/teacher'
import { fetchClassAnalytics } from '@/api/growth'

const router = useRouter()
const classes = ref([])
const selectedClassId = ref(null)
const analytics = ref(null)
const loading = ref(false)
const classesLoading = ref(false)

const dimensions = [
  { key: 'content', label: '内容能力' },
  { key: 'organization', label: '结构能力' },
  { key: 'language', label: '语言能力' },
]

function dimensionLabel(value) { return { content: '内容', organization: '结构', language: '语言', overall: '整体', topic: '审题' }[value] || value }
function statusLabel(status) { return { pending: '待复核', reviewing: '复核中', accepted: '已接受', rejected: '已驳回', resolved: '已处理' }[status] || status }
function distributionWidth(dimension, bucket) {
  const distribution = analytics.value?.dimension_distribution?.[dimension]
  if (!distribution?.total) return '0%'
  return `${((distribution[bucket] || 0) / distribution.total) * 100}%`
}

async function loadClasses() {
  classesLoading.value = true
  try {
    const response = await fetchTeacherClasses()
    classes.value = response.data
    if (!selectedClassId.value && classes.value.length) selectedClassId.value = classes.value[0].id
  } finally {
    classesLoading.value = false
  }
}

async function loadAnalytics() {
  if (!selectedClassId.value) return
  loading.value = true
  try {
    const response = await fetchClassAnalytics(selectedClassId.value)
    analytics.value = response.data
  } finally {
    loading.value = false
  }
}

function openStudent(studentId) {
  router.push(`/teacher/students/${studentId}/growth`)
}

onMounted(async () => {
  await loadClasses()
  await loadAnalytics()
})
</script>

<style scoped>
.notice { margin-bottom: 16px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.stat-card { padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.stat-card span, .stat-card small { color: var(--wm-text-secondary); font-size: 11px; }
.stat-card strong { font-size: 26px; }
.analysis-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.panel { padding: 20px; }
.students-panel { grid-column: 1 / -1; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 16px; }
.section-head h2 { margin: 0; font-size: 16px; }
.section-head span { color: var(--wm-text-secondary); font-size: 11px; }
.dimension-row { margin-bottom: 18px; }
.dimension-row__head { display: flex; justify-content: space-between; align-items: baseline; font-size: 13px; font-weight: 600; }
.dimension-row__head strong { color: var(--wm-primary); font-size: 20px; }
.dimension-row__head small { color: var(--wm-text-secondary); font-size: 10px; }
.dimension-row__meta { display: flex; gap: 16px; margin: 4px 0 7px; color: var(--wm-text-secondary); font-size: 10px; }
.distribution-bar { display: flex; height: 10px; border-radius: 999px; overflow: hidden; background: var(--wm-bg-soft); }
.distribution-bar .is-low { background: #fca5a5; }
.distribution-bar .is-basic { background: #fcd34d; }
.distribution-bar .is-good { background: #5eead4; }
.distribution-legend { display: flex; gap: 12px; margin-top: 5px; color: var(--wm-text-secondary); font-size: 9px; }
.issue-row { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid var(--wm-border); font-size: 12px; }
.problem-counts { margin-top: 14px; }
.problem-counts h3 { margin: 0 0 8px; font-size: 13px; }
.problem-counts div { display: flex; justify-content: space-between; padding: 4px 0; color: var(--wm-text-secondary); font-size: 11px; }
.appeal-status { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.appeal-status span { padding: 3px 8px; border-radius: 999px; background: var(--wm-bg-soft); color: var(--wm-text-secondary); font-size: 10px; }
.panel-note { margin: 12px 0 0; color: var(--wm-text-secondary); font-size: 10px; line-height: 1.7; }
.suggestion-card { padding: 12px; margin-bottom: 10px; border: 1px solid var(--wm-border); border-radius: 9px; }
.suggestion-card strong { font-size: 13px; }
.suggestion-card p { margin: 6px 0; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.7; }
.suggestion-card small { color: var(--wm-text-secondary); font-size: 10px; }
.muted { color: var(--wm-text-secondary); font-size: 10px; }

@media (max-width: 1100px) {
  .stats-grid, .analysis-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 720px) {
  .stats-grid, .analysis-grid { grid-template-columns: 1fr; }
  .students-panel { grid-column: auto; }
}
</style>