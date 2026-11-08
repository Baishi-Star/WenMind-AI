<template>
  <section class="wm-card training-section">
    <div class="section-head">
      <h2>个性化训练</h2>
      <span>推荐由近期真实弱项规则生成</span>
    </div>
    <el-alert
      v-if="notice"
      type="info"
      :closable="false"
      show-icon
      :title="notice"
      class="training-notice"
    />
    <el-empty
      v-if="!loading && tasks.length === 0"
      description="暂无训练任务，需至少一篇有效评价后才能生成建议"
    />
    <div class="task-grid">
      <article
        v-for="task in tasks"
        :key="task.id"
        class="task-card"
        :class="{ 'is-completed': task.status === 'completed' }"
      >
        <div class="task-card__head">
          <div>
            <span class="task-card__ability">{{ abilityLabel(task.ability) }}</span>
            <h3>{{ task.objective }}</h3>
          </div>
          <el-tag
            size="small"
            :type="task.status === 'completed' ? 'success' : 'warning'"
          >
            {{ task.status === 'completed' ? '已完成' : '待完成' }}
          </el-tag>
        </div>
        <p class="task-reason">
          <strong>推荐理由：</strong>{{ task.reason }}
        </p>
        <div class="task-content">
          {{ task.content }}
        </div>
        <div class="task-meta">
          <span>来源评价：{{ task.source_evaluation_ids.map((id) => `#${id}`).join('、') || '—' }}</span>
          <span>创建：{{ formatDateTime(task.created_at) }}</span>
        </div>
        <div
          v-if="task.result_text"
          class="task-result"
        >
          <strong>训练结果：</strong>{{ task.result_text }}
        </div>
        <el-button
          v-if="allowComplete && task.status === 'pending'"
          type="primary"
          plain
          size="small"
          @click="openComplete(task)"
        >
          完成训练并填写结果
        </el-button>
      </article>
    </div>

    <el-dialog
      v-model="dialogVisible"
      title="完成训练任务"
      width="520px"
      :close-on-click-modal="false"
    >
      <template v-if="selectedTask">
        <p class="dialog-objective">
          {{ selectedTask.objective }}
        </p>
        <el-form label-position="top">
          <el-form-item
            label="训练结果 / 反思"
            required
          >
            <el-input
              v-model.trim="resultText"
              type="textarea"
              :rows="5"
              maxlength="2000"
              show-word-limit
              placeholder="记录完成了什么、发现了什么问题、下次如何继续改进。"
            />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="dialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="resultText.length < 2"
          @click="submitComplete"
        >
          保存训练结果
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import { completeTrainingTask } from '@/api/growth'
import { formatDateTime } from '@/utils/format'

defineProps({
  tasks: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  notice: { type: String, default: '' },
  allowComplete: { type: Boolean, default: true },
})
const emit = defineEmits(['completed'])

const dialogVisible = ref(false)
const selectedTask = ref(null)
const resultText = ref('')
const submitting = ref(false)

function abilityLabel(value) {
  return { content: '内容 · 论证', organization: '结构 · 组织', language: '语言 · 表达', overall: '综合挑战' }[value] || value
}

function openComplete(task) {
  selectedTask.value = task
  resultText.value = ''
  dialogVisible.value = true
}

async function submitComplete() {
  if (!selectedTask.value || resultText.value.length < 2 || submitting.value) return
  submitting.value = true
  try {
    await completeTrainingTask(selectedTask.value.id, resultText.value)
    ElMessage.success('训练结果已保存')
    dialogVisible.value = false
    emit('completed')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.training-section { padding: 20px; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.section-head h2 { margin: 0; font-size: 17px; }
.section-head span { color: var(--wm-text-secondary); font-size: 11px; }
.training-notice { margin-bottom: 14px; }
.task-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.task-card { padding: 16px; border: 1px solid var(--wm-border); border-radius: 12px; }
.task-card.is-completed { background: #f8fbfa; }
.task-card__head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.task-card__ability { color: var(--wm-primary); font-size: 10px; letter-spacing: 0.08em; }
.task-card h3 { margin: 5px 0 0; font-size: 15px; }
.task-reason { margin: 10px 0; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.8; }
.task-content { padding: 10px 12px; border-radius: 9px; background: var(--wm-bg-soft); font-size: 12px; line-height: 1.85; }
.task-meta { display: flex; flex-wrap: wrap; gap: 6px 14px; margin: 10px 0; color: var(--wm-text-secondary); font-size: 10px; }
.task-result { margin: 10px 0; padding: 9px; border-radius: 8px; background: #ecfdf5; color: #166534; font-size: 11px; line-height: 1.7; }
.dialog-objective { margin: 0 0 14px; font-weight: 600; }

@media (max-width: 900px) {
  .task-grid { grid-template-columns: 1fr; }
}
</style>