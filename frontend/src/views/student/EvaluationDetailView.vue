<template>
  <div>
    <PageHeader
      title="AI 评价结果"
      subtitle="选择本人真实作文，触发多 Agent 评价，并查看原文证据、追问记录和申诉进度。"
    >
      <template #tag>
        <el-tag
          type="success"
          effect="plain"
        >
          真实工作流已接入
        </el-tag>
      </template>
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadAll"
        >
          刷新任务
        </el-button>
      </template>
    </PageHeader>

    <div class="evaluation-layout">
      <aside class="evaluation-sidebar">
        <section class="wm-card side-panel">
          <h2>发起新评价</h2>
          <el-form label-position="top">
            <el-form-item
              label="选择我的作文"
              required
            >
              <el-select
                v-model="selectedEssayId"
                placeholder="请选择作文"
                style="width: 100%"
                :loading="essaysLoading"
              >
                <el-option
                  v-for="essay in essays"
                  :key="essay.id"
                  :value="essay.id"
                  :disabled="essay.status === 'draft'"
                  :label="`#${essay.id} ${essay.prompt_title || '自由作文'}${essay.status === 'draft' ? '（草稿需先提交）' : ''}`"
                />
              </el-select>
            </el-form-item>
            <el-button
              type="primary"
              style="width: 100%"
              :loading="creating"
              :disabled="!selectedEssayId"
              @click="submitEvaluation"
            >
              创建并执行多 Agent 评价
            </el-button>
          </el-form>
          <p class="side-panel__notice">
            重复创建活动任务会被后端拦截。新任务通过 FastAPI BackgroundTasks 执行。
          </p>
        </section>

        <section class="wm-card side-panel">
          <div class="side-panel__head">
            <h2>我的评价任务</h2><span>{{ evaluations.length }} 条</span>
          </div>
          <div
            v-if="evaluations.length === 0"
            class="task-empty"
          >
            暂无评价任务
          </div>
          <button
            v-for="item in evaluations"
            :key="item.id"
            type="button"
            class="task-entry"
            :class="{ 'is-active': currentEvaluation?.id === item.id }"
            @click="selectEvaluation(item.id)"
          >
            <span><strong>#{{ item.id }}</strong> 作文 #{{ item.essay_id }}</span>
            <el-tag
              size="small"
              :type="statusType(item.status)"
            >
              {{ statusLabel(item.status) }}
            </el-tag>
            <small>{{ formatDateTime(item.created_at) }}</small>
          </button>
        </section>
      </aside>

      <main class="evaluation-main">
        <section
          v-if="currentEvaluation"
          class="current-actions"
        >
          <el-button
            v-if="['pending', 'failed'].includes(currentEvaluation.status)"
            type="primary"
            :loading="executing"
            @click="startCurrentEvaluation"
          >
            {{ currentEvaluation.status === 'failed' ? '重新执行失败任务' : '启动评价任务' }}
          </el-button>
          <el-button
            v-if="currentEvaluation.status === 'completed'"
            type="warning"
            plain
            @click="openAppeal(null)"
          >
            对本次评价有异议
          </el-button>
          <el-button
            v-if="currentEvaluation.status === 'completed'"
            text
            type="primary"
            @click="router.push('/student/appeals')"
          >
            查看申诉进度
          </el-button>
          <el-tag
            v-if="polling"
            type="warning"
            effect="plain"
          >
            正在轮询任务状态，Agent 结果会自动更新
          </el-tag>
        </section>
        <el-alert
          v-if="pageError"
          type="error"
          :closable="false"
          show-icon
          :title="pageError"
          class="page-error"
          @close="pageError = ''"
        />
        <section
          v-if="currentEvaluation && ['pending', 'processing'].includes(currentEvaluation.status)"
          class="wm-card progress-card"
        >
          <div class="progress-head">
            <h2>AI 正在分析</h2>
            <el-tag
              type="warning"
              effect="plain"
            >
              {{ statusLabel(currentEvaluation.status) }}
            </el-tag>
          </div>
          <p class="progress-hint">
            AI 正在分析，通常需要 30~120 秒
          </p>
          <el-progress :percentage="progressPercent" />
          <div class="progress-meta">
            <span>已完成 Agent：{{ completedAgents }} / {{ agentTotal }}</span>
            <span>已耗时：{{ elapsedSeconds }} 秒</span>
          </div>
          <div
            v-if="(currentEvaluation.agent_runs || []).length"
            class="agent-list"
          >
            <span
              v-for="run in currentEvaluation.agent_runs"
              :key="run.id"
              class="agent-chip"
              :class="`is-${run.status}`"
            >
              {{ agentLabel(run.agent_name) }} · {{ run.status === 'completed' ? '完成' : run.status === 'failed' ? '失败' : '执行中' }}
            </span>
          </div>
          <el-alert
            v-if="pollTimedOut"
            type="warning"
            :closable="false"
            show-icon
            title="评价耗时较长，可稍后在「AI 评价结果」查看"
            class="progress-timeout"
          />
        </section>
        <el-alert
          v-if="currentEvaluation?.status === 'failed'"
          type="error"
          :closable="false"
          show-icon
          title="评价失败"
          :description="currentEvaluation.error_message || '请点击「重新执行失败任务」重试'"
          class="page-error"
        />
        <el-collapse
          v-if="currentEvaluation?.status === 'failed'"
          class="failure-detail"
        >
          <el-collapse-item
            title="技术详情（可复制）"
            name="detail"
          >
            <pre class="failure-message">{{ currentEvaluation.error_message || '暂无更详细的技术信息' }}</pre>
          </el-collapse-item>
        </el-collapse>
        <div
          v-if="currentEvaluation"
          class="essay-titles"
        >
          <span>作文题目（教师布置）：<strong>{{ currentEvaluation.prompt_title || '自由作文' }}</strong></span>
          <span>作文标题（学生自拟）：<strong>{{ currentEvaluation.essay_title || '未填写标题' }}</strong></span>
        </div>
        <EvaluationProcess
          v-if="currentEvaluation?.status === 'completed'"
          :evaluation="currentEvaluation"
          :essay-content="essayContent"
          @appeal="openAppeal"
        />
        <section
          v-else
          class="wm-card empty-evaluation"
        >
          <el-empty description="请选择一篇作文发起评价，或从左侧选择已有任务">
            <el-button
              type="primary"
              :disabled="!selectedEssayId"
              @click="submitEvaluation"
            >
              开始首次评价
            </el-button>
          </el-empty>
        </section>
      </main>
    </div>

    <AppealDialog
      v-if="currentEvaluation"
      v-model="appealVisible"
      :evaluation="currentEvaluation"
      :feedback-item="appealFeedbackItem"
      @submitted="handleAppealSubmitted"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import AppealDialog from '@/components/AppealDialog.vue'
import EvaluationProcess from '@/components/EvaluationProcess.vue'
import PageHeader from '@/components/PageHeader.vue'

import { fetchEssay } from '@/api/essay'
import {
  createEvaluation,
  executeEvaluation,
  fetchEssays,
  fetchEvaluation,
  fetchEvaluations,
} from '@/api/evaluation'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const essays = ref([])
const evaluations = ref([])
const selectedEssayId = ref(null)
const currentEvaluation = ref(null)
const essayContent = ref('')
const loadedEssayId = ref(null)
const essaysLoading = ref(false)
const loading = ref(false)
const creating = ref(false)
const executing = ref(false)
const polling = ref(false)
const elapsedSeconds = ref(0)
const pollTimedOut = ref(false)
const pageError = ref('')
const appealVisible = ref(false)
const appealFeedbackItem = ref(null)
let pollTimer = null
let pollStartedAt = 0
const agentTotal = 6
const completedAgents = computed(
  () => (currentEvaluation.value?.agent_runs || []).filter((run) => run.status === 'completed').length,
)
const progressPercent = computed(() => Math.min(100, Math.round((completedAgents.value / agentTotal) * 100)))

function agentLabel(name) {
  return {
    topic_agent: '审题',
    content_agent: '内容',
    expression_agent: '表达',
    development_agent: '发展',
    feedback_agent: '综合',
    quality_agent: '质量',
  }[name] || name
}

function statusType(status) { return { completed: 'success', failed: 'danger', processing: 'warning', pending: 'info' }[status] || 'info' }
function statusLabel(status) { return { completed: '已完成', failed: '失败', processing: '执行中', pending: '待处理' }[status] || status }

async function loadEssays() {
  essaysLoading.value = true
  try {
    const response = await fetchEssays()
    essays.value = response.data.items
    if (!selectedEssayId.value) selectedEssayId.value = essays.value.find((item) => item.status !== 'draft')?.id || null
  } finally {
    essaysLoading.value = false
  }
}

async function loadEvaluations() {
  const response = await fetchEvaluations()
  evaluations.value = response.data.items
  return evaluations.value
}

async function loadEssayContent(essayId) {
  if (loadedEssayId.value === essayId && essayContent.value) return
  const response = await fetchEssay(essayId)
  essayContent.value = response.data.content
  loadedEssayId.value = essayId
}

async function loadEvaluation(evaluationId, showLoading = true) {
  if (showLoading) loading.value = true
  try {
    const response = await fetchEvaluation(evaluationId)
    currentEvaluation.value = response.data
    await loadEssayContent(response.data.essay_id)
    return response.data
  } catch (error) {
    pageError.value = error.message || '评价任务加载失败'
    stopPolling()
    return null
  } finally {
    if (showLoading) loading.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadEssays(), loadEvaluations()])
    const queryId = Number(route.query.evaluationId)
    const targetId = Number.isFinite(queryId) && queryId > 0
      ? queryId
      : currentEvaluation.value?.id || evaluations.value[0]?.id
    if (targetId) await selectEvaluation(targetId)
  } finally {
    loading.value = false
  }
}

async function selectEvaluation(evaluationId) {
  stopPolling()
  const evaluation = await loadEvaluation(evaluationId)
  if (evaluation && ['pending', 'processing'].includes(evaluation.status)) startPolling()
}

async function submitEvaluation() {
  if (!selectedEssayId.value || creating.value) return
  creating.value = true
  pageError.value = ''
  try {
    const response = await createEvaluation(selectedEssayId.value)
    currentEvaluation.value = response.data
    await loadEssayContent(response.data.essay_id)
    ElMessage.success(`评价任务 #${response.data.id} 已创建，后台开始执行`)
    await loadEvaluations()
    startPolling()
  } catch (error) {
    pageError.value = error.message || '评价任务创建失败'
    await loadEvaluations()
  } finally {
    creating.value = false
  }
}

async function startCurrentEvaluation() {
  if (!currentEvaluation.value || executing.value) return
  executing.value = true
  try {
    const response = await executeEvaluation(currentEvaluation.value.id)
    currentEvaluation.value = response.data
    await loadEssayContent(response.data.essay_id)
    ElMessage.success('评价任务已启动')
    startPolling()
  } catch (error) {
    pageError.value = error.message || '任务启动失败'
  } finally {
    executing.value = false
  }
}

function openAppeal(feedbackItem) {
  appealFeedbackItem.value = feedbackItem
  appealVisible.value = true
}

function handleAppealSubmitted() {
  ElMessage.success('申诉记录已持久化，可在“我的申诉”中查看进度')
}

function startPolling() {
  stopPolling()
  if (!currentEvaluation.value) return
  polling.value = true
  pollTimedOut.value = false
  elapsedSeconds.value = 0
  pollStartedAt = Date.now()
  pollTimer = window.setInterval(async () => {
    const elapsed = Math.round((Date.now() - pollStartedAt) / 1000)
    elapsedSeconds.value = elapsed
    if (elapsed >= 180) {
      pollTimedOut.value = true
      stopPolling()
      return
    }
    const evaluation = await loadEvaluation(currentEvaluation.value?.id, false)
    if (!evaluation || ['completed', 'failed'].includes(evaluation.status)) {
      stopPolling()
      await loadEvaluations()
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) window.clearInterval(pollTimer)
  pollTimer = null
  polling.value = false
}

onMounted(loadAll)
onUnmounted(stopPolling)
</script>

<style scoped>
.evaluation-layout { display: grid; grid-template-columns: 300px minmax(0, 1fr); gap: 18px; align-items: start; }
.evaluation-sidebar { display: grid; gap: 18px; position: sticky; top: 88px; }
.side-panel { padding: 18px; }
.side-panel h2 { margin: 0 0 14px; font-size: 16px; }
.side-panel__notice { margin: 12px 0 0; color: var(--wm-text-secondary); font-size: 11px; line-height: 1.8; }
.side-panel__head { display: flex; align-items: center; justify-content: space-between; }
.side-panel__head span { color: var(--wm-text-secondary); font-size: 12px; }
.task-empty { color: var(--wm-text-secondary); font-size: 13px; text-align: center; padding: 20px 0; }
.task-entry { width: 100%; display: grid; grid-template-columns: 1fr auto; gap: 6px; padding: 11px 10px; margin-bottom: 7px; text-align: left; border: 1px solid var(--wm-border); border-radius: 9px; background: #fff; cursor: pointer; }
.task-entry.is-active { border-color: var(--wm-primary); background: #f2f4ff; }
.task-entry small { grid-column: 1 / -1; color: var(--wm-text-secondary); }
.evaluation-main { min-width: 0; }
.current-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }
.essay-titles { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; padding: 12px 14px; border-radius: 10px; background: var(--wm-bg-soft); color: var(--wm-text-secondary); font-size: 12px; }
.essay-titles strong { color: var(--wm-text-main); }
.page-error { margin-bottom: 14px; }
.failure-detail { margin-bottom: 14px; }
.failure-message { margin: 0; white-space: pre-wrap; word-break: break-all; font-size: 12px; color: var(--wm-text-secondary); }
.progress-card { padding: 20px; margin-bottom: 14px; }
.progress-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.progress-head h2 { margin: 0; font-size: 16px; }
.progress-hint { margin: 8px 0 14px; color: var(--wm-text-secondary); font-size: 12px; }
.progress-meta { display: flex; gap: 20px; flex-wrap: wrap; margin: 12px 0; color: var(--wm-text-secondary); font-size: 12px; }
.agent-list { display: flex; flex-wrap: wrap; gap: 8px; }
.agent-chip { padding: 4px 10px; border-radius: 999px; background: var(--wm-bg-soft); color: var(--wm-text-secondary); font-size: 11px; }
.agent-chip.is-completed { background: #ecfdf5; color: #047857; }
.agent-chip.is-failed { background: #fef2f2; color: #b91c1c; }
.progress-timeout { margin-top: 12px; }
.empty-evaluation { padding: 50px 20px; }

@media (max-width: 1050px) {
  .evaluation-layout { grid-template-columns: 1fr; }
  .evaluation-sidebar { position: static; }
}
</style>