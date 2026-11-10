<template>
  <div>
    <PageHeader
      title="学生工作台"
      subtitle="提交作文、查看真实 AI 评价与原文证据、跟踪申诉和个性化训练进度。"
    >
      <template #tag>
        <DemoSessionTag />
      </template>
    </PageHeader>

    <section class="welcome-card wm-card">
      <div>
        <p class="welcome-card__eyebrow">
          WenMind AI · Student Workspace
        </p>
        <h2>{{ greeting }}，{{ authStore.displayName }}</h2>
        <p>在这里完成作文提交，查看多 Agent 评价与原文证据，发起申诉，并依据近期真实评价安排个性化训练。</p>
      </div>
      <div class="welcome-card__meta">
        <span>最近一次评价</span>
        <strong>{{ latestEvalLabel }}</strong>
        <small>{{ trainingLabel }}</small>
      </div>
    </section>

    <div class="workspace-grid">
      <div class="workspace-main">
        <section class="stats-grid">
          <article class="wm-card stat-card">
            <span>待评价作文</span>
            <small
              v-if="essaysState.status === 'loading'"
              class="muted"
            >加载中…</small>
            <small
              v-else-if="essaysState.status === 'error'"
              class="muted"
            >数据暂不可用</small>
            <template v-else>
              <strong v-if="pendingEssayCount > 0">{{ pendingEssayCount }}<small>篇</small></strong>
              <em v-else>暂无待评价作文</em>
            </template>
          </article>

          <article class="wm-card stat-card">
            <span>最近一次诊断</span>
            <small
              v-if="evalsState.status === 'loading'"
              class="muted"
            >加载中…</small>
            <small
              v-else-if="evalsState.status === 'error'"
              class="muted"
            >数据暂不可用</small>
            <template v-else-if="latestDimensions.length">
              <div class="dimension-chips">
                <span
                  v-for="item in latestDimensions"
                  :key="item.dimension"
                  class="dim-chip"
                >
                  <strong>{{ dimensionLabel(item.dimension) }}</strong>
                  {{ item.original_score ?? '—' }}/{{ item.max_score }}
                  <em>{{ gradeLabel(item.original_score) }}</em>
                </span>
              </div>
              <small
                class="review-tag"
                :class="latestReviewed ? 'is-reviewed' : 'is-pending'"
              >{{ latestReviewed ? '已复核' : '待教师复核' }}</small>
            </template>
            <em v-else>暂无已完成评价</em>
          </article>

          <article class="wm-card stat-card">
            <span>待处理申诉</span>
            <small
              v-if="appealsState.status === 'loading'"
              class="muted"
            >加载中…</small>
            <small
              v-else-if="appealsState.status === 'error'"
              class="muted"
            >数据暂不可用</small>
            <template v-else>
              <strong v-if="pendingAppealCount > 0">{{ pendingAppealCount }}<small>条</small></strong>
              <em v-else>暂无待处理申诉</em>
            </template>
          </article>

          <article class="wm-card stat-card">
            <span>训练进度</span>
            <small
              v-if="trainingState.status === 'loading'"
              class="muted"
            >加载中…</small>
            <small
              v-else-if="trainingState.status === 'error'"
              class="muted"
            >数据暂不可用</small>
            <template v-else>
              <strong v-if="trainingTotal > 0">{{ trainingCompleted }}<small>/{{ trainingTotal }}</small></strong>
              <em v-else>暂无训练任务</em>
              <div
                v-if="trainingTotal > 0"
                class="progress-bar"
              >
                <span :style="{ width: `${trainingPercent}%` }" />
              </div>
            </template>
          </article>
        </section>

        <section class="wm-card workspace-section">
          <div class="workspace-section__head">
            <h2>现在该做什么</h2>
          </div>
          <div class="action-row">
            <el-button
              type="primary"
              size="large"
              @click="goSubmit"
            >
              提交新作文
            </el-button>
            <el-button
              size="large"
              :disabled="!latestEvaluationId"
              @click="goLatestEvaluation"
            >
              查看最近评价
            </el-button>
            <span
              v-if="!latestEvaluationId"
              class="muted"
            >暂无已完成评价，提交作文后可查看</span>
          </div>
        </section>

        <section class="wm-card workspace-section">
          <div class="workspace-section__head">
            <h2>最近作文</h2>
            <span>最多展示最近 3 篇</span>
          </div>
          <div
            v-if="essaysState.status === 'loading'"
            class="muted"
          >
            加载中…
          </div>
          <div
            v-else-if="essaysState.status === 'error'"
            class="muted"
          >
            数据暂不可用
          </div>
          <el-empty
            v-else-if="recentEssays.length === 0"
            description="还没有提交过作文"
            :image-size="70"
          />
          <ul
            v-else
            class="recent-list"
          >
            <li
              v-for="item in recentEssays"
              :key="item.id"
              @click="goEssay(item)"
            >
              <div>
                <strong>{{ item.prompt_title || '自由作文' }}</strong>
                <small>{{ formatDateTime(item.created_at) }}</small>
              </div>
              <el-tag
                size="small"
                :type="essayStatusType(item.status)"
              >
                {{ essayStatusLabel(item.status) }}
              </el-tag>
              <span class="recent-grade">{{ essayGrade(item) }}</span>
              <el-icon>
                <ArrowRight />
              </el-icon>
            </li>
          </ul>
        </section>

        <section class="wm-card workspace-section">
          <div class="workspace-section__head">
            <h2>核心业务闭环</h2>
            <span>评价不是终点，复核与改进同样重要</span>
          </div>
          <el-steps
            :active="-1"
            align-center
            class="workflow-steps"
          >
            <el-step
              v-for="step in workflow"
              :key="step"
              :title="step"
              status="wait"
            />
          </el-steps>
        </section>
      </div>

      <aside class="workspace-aside">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="评价定位说明"
          description="AI 评价为教学诊断参考，按全国卷 60 分制量规生成原始分，最终结果以教师复核为准。"
        />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

import DemoSessionTag from '@/components/DemoSessionTag.vue'
import PageHeader from '@/components/PageHeader.vue'
import { fetchAppeals } from '@/api/appeal'
import { fetchEssays } from '@/api/essay'
import { fetchEvaluations } from '@/api/evaluation'
import { fetchTrainingTasks } from '@/api/growth'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const authStore = useAuthStore()

const essaysState = reactive({ status: 'loading', items: [] })
const evalsState = reactive({ status: 'loading', items: [] })
const appealsState = reactive({ status: 'loading', items: [] })
const trainingState = reactive({ status: 'loading', completed: 0, pending: 0 })

const workflow = ['提交作文', '多 Agent 评价', '证据追溯', '申诉复核', '成长训练']

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const completedEvaluations = computed(() =>
  evalsState.items.filter((item) => item.status === 'completed'),
)

const latestEvaluation = computed(() => {
  const list = [...completedEvaluations.value]
  list.sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at))
  return list[0] || null
})

const latestEvaluationId = computed(() => latestEvaluation.value?.id ?? null)

const dimensionOrder = ['content', 'expression', 'development', 'organization', 'language']

const latestDimensions = computed(() => {
  const scores = latestEvaluation.value?.dimension_scores || []
  return [...scores].sort((a, b) => dimensionOrder.indexOf(a.dimension) - dimensionOrder.indexOf(b.dimension))
})

const latestReviewed = computed(() =>
  latestDimensions.value.some((item) => item.final_score !== null && item.final_score !== undefined),
)

const latestEvalLabel = computed(() => {
  if (evalsState.status === 'loading') return '加载中…'
  if (evalsState.status === 'error') return '数据暂不可用'
  return latestEvaluation.value ? formatDateTime(latestEvaluation.value.updated_at || latestEvaluation.value.created_at) : '暂无'
})

const pendingEssayCount = computed(() =>
  essaysState.items.filter((item) => ['submitted', 'evaluating'].includes(item.status)).length,
)

const pendingAppealCount = computed(() =>
  appealsState.items.filter((item) => ['pending', 'reviewing'].includes(item.status)).length,
)

const trainingCompleted = computed(() => trainingState.completed)
const trainingTotal = computed(() => trainingState.completed + trainingState.pending)
const trainingPercent = computed(() =>
  trainingTotal.value > 0 ? Math.round((trainingCompleted.value / trainingTotal.value) * 100) : 0,
)
const trainingLabel = computed(() => {
  if (trainingState.status === 'loading') return '训练进度加载中…'
  if (trainingState.status === 'error') return '训练进度暂不可用'
  return trainingTotal.value > 0 ? `训练进度 ${trainingCompleted.value}/${trainingTotal.value}` : '暂无训练任务'
})

const recentEssays = computed(() => {
  const list = [...essaysState.items]
  list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  return list.slice(0, 3)
})

function dimensionLabel(dimension) {
  return {
    content: '内容',
    expression: '表达',
    development: '发展',
    organization: '组织（旧）',
    language: '语言（旧）',
  }[dimension] || dimension
}

function gradeLabel(score) {
  if (score === null || score === undefined) return '—'
  if (score >= 17) return '一等'
  if (score >= 12) return '二等'
  if (score >= 7) return '三等'
  return '四等'
}

function essayStatusLabel(status) {
  return {
    draft: '草稿',
    submitted: '已提交',
    evaluating: '评价中',
    completed: '已完成',
    failed: '评价失败',
  }[status] || status
}

function essayStatusType(status) {
  return {
    draft: 'info',
    submitted: 'info',
    evaluating: 'warning',
    completed: 'success',
    failed: 'danger',
  }[status] || 'info'
}

function evaluationForEssay(essayId) {
  const list = completedEvaluations.value.filter((item) => item.essay_id === essayId)
  list.sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at))
  return list[0] || null
}

function essayGrade(item) {
  const evaluation = evaluationForEssay(item.id)
  if (!evaluation) {
    if (item.status === 'evaluating') return '评价中'
    if (item.status === 'submitted') return '待评价'
    if (item.status === 'failed') return '评价失败'
    return '暂无诊断'
  }
  const scores = [...(evaluation.dimension_scores || [])].sort(
    (a, b) => dimensionOrder.indexOf(a.dimension) - dimensionOrder.indexOf(b.dimension),
  )
  if (!scores.length) return '暂无诊断'
  return scores.map((score) => `${dimensionLabel(score.dimension)}${gradeLabel(score.original_score)}`).join(' · ')
}

function hasEvaluation(essayId) {
  return completedEvaluations.value.some((item) => item.essay_id === essayId)
}

function goSubmit() {
  router.push('/student/essays/new')
}

function goLatestEvaluation() {
  if (latestEvaluationId.value) {
    router.push('/student/evaluations')
  }
}

function goEssay(item) {
  router.push(hasEvaluation(item.id) ? '/student/evaluations' : '/student/essays')
}

async function loadDashboard() {
  const [essays, evaluations, appeals, training] = await Promise.allSettled([
    fetchEssays({ page: 1, page_size: 50 }),
    fetchEvaluations({ page: 1, page_size: 50 }),
    fetchAppeals(),
    fetchTrainingTasks(),
  ])

  if (essays.status === 'fulfilled') {
    essaysState.items = essays.value?.data?.items || []
    essaysState.status = 'success'
  } else {
    essaysState.status = 'error'
  }

  if (evaluations.status === 'fulfilled') {
    evalsState.items = evaluations.value?.data?.items || []
    evalsState.status = 'success'
  } else {
    evalsState.status = 'error'
  }

  if (appeals.status === 'fulfilled') {
    appealsState.items = appeals.value?.data || []
    appealsState.status = 'success'
  } else {
    appealsState.status = 'error'
  }

  if (training.status === 'fulfilled') {
    trainingState.completed = training.value?.data?.completed_count || 0
    trainingState.pending = training.value?.data?.pending_count || 0
    trainingState.status = 'success'
  } else {
    trainingState.status = 'error'
  }
}

onMounted(loadDashboard)
</script>

<style scoped>
.welcome-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 26px 28px;
  margin-bottom: 20px;
  background: linear-gradient(120deg, rgba(255, 255, 255, 0.96), rgba(239, 242, 255, 0.92));
}

.welcome-card__eyebrow {
  margin: 0 0 8px;
  color: var(--wm-primary);
  font-size: 12px;
  letter-spacing: 1px;
}

.welcome-card h2 {
  margin: 0 0 10px;
  font-size: 25px;
}

.welcome-card p:not(.welcome-card__eyebrow) {
  margin: 0;
  max-width: 760px;
  color: var(--wm-text-secondary);
  font-size: 13px;
  line-height: 1.9;
}

.welcome-card__meta {
  min-width: 150px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid var(--wm-border);
}

.welcome-card__meta span,
.welcome-card__meta small {
  color: var(--wm-text-secondary);
  font-size: 11px;
}

.welcome-card__meta strong {
  font-size: 20px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 20px;
  align-items: start;
}

.workspace-main,
.workspace-aside {
  display: grid;
  gap: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  min-height: 112px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-card > span {
  color: var(--wm-text-secondary);
  font-size: 12px;
}

.stat-card strong {
  color: var(--wm-primary);
  font-size: 28px;
}

.stat-card strong small {
  color: var(--wm-text-secondary);
  font-size: 12px;
}

.stat-card em {
  color: var(--wm-text-secondary);
  font-size: 12px;
  font-style: normal;
}

.muted {
  color: var(--wm-text-secondary);
  font-size: 12px;
}

.dimension-chips {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dim-chip {
  display: flex;
  align-items: baseline;
  gap: 6px;
  color: var(--wm-text-secondary);
  font-size: 11px;
}

.dim-chip strong {
  color: var(--wm-text-main);
  font-size: 13px;
}

.dim-chip em {
  color: var(--wm-primary);
  font-size: 10px;
  font-style: normal;
}

.review-tag {
  font-size: 11px;
}

.review-tag.is-reviewed {
  color: #15803d;
}

.review-tag.is-pending {
  color: #b45309;
}

.progress-bar {
  height: 6px;
  border-radius: 99px;
  background: var(--wm-bg-soft);
  overflow: hidden;
}

.progress-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--wm-primary);
}

.workspace-section {
  padding: 20px;
}

.workspace-section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.workspace-section__head h2 {
  margin: 0;
  font-size: 16px;
}

.workspace-section__head span {
  color: var(--wm-text-secondary);
  font-size: 12px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.recent-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.recent-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--wm-border);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.recent-list li:hover {
  border-color: var(--wm-primary-soft);
  background: var(--wm-bg-soft);
}

.recent-list li > div {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.recent-list strong {
  font-size: 13px;
}

.recent-list small {
  color: var(--wm-text-secondary);
  font-size: 11px;
}

.recent-grade {
  max-width: 280px;
  color: var(--wm-text-secondary);
  font-size: 11px;
}

.workflow-steps {
  margin-top: 8px;
}

.workflow-steps :deep(.el-step__title) {
  font-size: 12px;
}

@media (max-width: 1250px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .welcome-card {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 600px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>