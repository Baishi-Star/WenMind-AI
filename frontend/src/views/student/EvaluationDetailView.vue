<template>
  <div>
    <PageHeader
      title="AI 评价结果"
      subtitle="选择本人真实作文，触发 Orchestrator 与多 Agent 后台评价，并轮询查看 RAG、独立分析、证据审核和综合报告。"
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
                  :label="`#${essay.id} ${essay.prompt_title || '自由作文'}`"
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
        <EvaluationProcess
          v-if="currentEvaluation"
          :evaluation="currentEvaluation"
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
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import EvaluationProcess from '@/components/EvaluationProcess.vue'
import PageHeader from '@/components/PageHeader.vue'
import {
  createEvaluation,
  executeEvaluation,
  fetchEssays,
  fetchEvaluation,
  fetchEvaluations,
} from '@/api/evaluation'
import { formatDateTime } from '@/utils/format'

const essays = ref([])
const evaluations = ref([])
const selectedEssayId = ref(null)
const currentEvaluation = ref(null)
const essaysLoading = ref(false)
const loading = ref(false)
const creating = ref(false)
const executing = ref(false)
const polling = ref(false)
const pageError = ref('')
let pollTimer = null


function statusType(status) { return { completed: 'success', failed: 'danger', processing: 'warning', pending: 'info' }[status] || 'info' }
function statusLabel(status) { return { completed: '已完成', failed: '失败', processing: '执行中', pending: '待处理' }[status] || status }

async function loadEssays() {
  essaysLoading.value = true
  try {
    const response = await fetchEssays()
    essays.value = response.data.items
    if (!selectedEssayId.value && essays.value.length) selectedEssayId.value = essays.value[0].id
  } finally {
    essaysLoading.value = false
  }
}

async function loadEvaluations() {
  const response = await fetchEvaluations()
  evaluations.value = response.data.items
  return evaluations.value
}

async function loadEvaluation(evaluationId, showLoading = true) {
  if (showLoading) loading.value = true
  try {
    const response = await fetchEvaluation(evaluationId)
    currentEvaluation.value = response.data
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
    if (currentEvaluation.value) await loadEvaluation(currentEvaluation.value.id, false)
    else if (evaluations.value.length) await selectEvaluation(evaluations.value[0].id)
  } finally {
    loading.value = false
  }
}

async function selectEvaluation(evaluationId) {
  stopPolling()
  const evaluation = await loadEvaluation(evaluationId)
  if (evaluation?.status === 'processing') startPolling()
}

async function submitEvaluation() {
  if (!selectedEssayId.value || creating.value) return
  creating.value = true
  pageError.value = ''
  try {
    const response = await createEvaluation(selectedEssayId.value)
    currentEvaluation.value = response.data
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
    ElMessage.success('评价任务已启动')
    startPolling()
  } catch (error) {
    pageError.value = error.message || '任务启动失败'
  } finally {
    executing.value = false
  }
}

function startPolling() {
  stopPolling()
  if (!currentEvaluation.value) return
  polling.value = true
  pollTimer = window.setInterval(async () => {
    const evaluation = await loadEvaluation(currentEvaluation.value.id, false)
    if (!evaluation || ['completed', 'failed'].includes(evaluation.status)) {
      stopPolling()
      await loadEvaluations()
    }
  }, 1500)
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
.current-actions { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; }
.page-error { margin-bottom: 14px; }
.empty-evaluation { padding: 50px 20px; }

@media (max-width: 1050px) {
  .evaluation-layout { grid-template-columns: 1fr; }
  .evaluation-sidebar { position: static; }
}
</style>