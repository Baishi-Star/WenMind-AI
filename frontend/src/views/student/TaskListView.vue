<template>
  <div>
    <PageHeader
      title="我的写作任务"
      subtitle="查看教师下发的写作任务，按子问题逐条作答并提交；提交后系统自动执行多 Agent 评价。"
    >
      <template #tag>
        <el-tag
          type="success"
          effect="plain"
        >
          真实提交闭环
        </el-tag>
      </template>
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadTasks"
        >
          刷新
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="tasks.length === 0 && !loading"
      type="info"
      :closable="false"
      show-icon
      title="暂无待完成写作任务"
      description="教师发布任务后会显示在这里；你也可以使用「作文提交」按旧流程自由提交作文。"
      class="notice"
    />

    <div
      v-loading="loading"
      class="task-grid"
    >
      <article
        v-for="task in tasks"
        :key="task.id"
        class="wm-card task-card"
        :class="{ 'is-overdue': task.is_overdue }"
      >
        <div class="task-card__head">
          <div>
            <h2>{{ task.title }}</h2>
            <div class="task-card__meta">
              <span>{{ task.teacher_name || '教师' }}</span>
              <span v-if="task.class_names.length">· {{ task.class_names.join('、') }}</span>
              <span v-if="task.due_at">· 截止 {{ formatDateTime(task.due_at) }}</span>
            </div>
          </div>
          <el-tag
            size="small"
            :type="task.is_overdue ? 'danger' : statusType(task.status)"
          >
            {{ task.is_overdue ? '已截止' : statusLabel(task.status) }}
          </el-tag>
        </div>
        <p class="task-card__prompt">
          {{ task.prompt_text }}
        </p>
        <div class="task-card__tags">
          <el-tag
            size="small"
            effect="plain"
          >
            {{ task.questions.length }} 道子问题
          </el-tag>
          <el-tag
            size="small"
            effect="plain"
          >
            {{ wordLabel(task) }}
          </el-tag>
          <el-tag
            v-if="task.submission_status"
            size="small"
            :type="submissionType(task.submission_status)"
          >
            我的提交：{{ submissionLabel(task.submission_status) }}
          </el-tag>
        </div>
        <div class="task-card__actions">
          <el-button
            type="primary"
            :disabled="task.is_overdue || (task.submission_status && !task.allow_resubmit)"
            @click="openSubmit(task)"
          >
            {{ task.submission_status && !task.allow_resubmit ? '已提交' : task.submission_status ? '再次提交文字' : '在线作答' }}
          </el-button>
          <el-button
            :disabled="task.is_overdue"
            @click="openImageSubmit(task)"
          >
            上传作文照片
          </el-button>
        </div>
      </article>
    </div>

    <el-dialog
      v-model="imageVisible"
      :title="activeTask ? `上传作文照片：${activeTask.title}` : '上传作文照片'"
      width="860px"
      :close-on-click-modal="false"
    >
      <template v-if="activeTask">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="作文题目 / 材料"
          :description="activeTask.prompt_text"
          class="submit-notice"
        />
        <el-alert
          type="warning"
          :closable="false"
          show-icon
          title="当前阶段说明"
          description="本步仅完成图片上传、页序与查看。视觉模型识别与批改将在下一步接入；确认前不会进入评价队列。"
          class="submit-notice"
        />
        <ImageUploader
          v-if="imageSubmissionId"
          :submission-id="imageSubmissionId"
          @changed="handleImageChanged"
        />
      </template>
      <template #footer>
        <el-button @click="imageVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="submitVisible"
      :title="activeTask ? `作答：${activeTask.title}` : '作答'"
      width="820px"
      :close-on-click-modal="false"
    >
      <template v-if="activeTask">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="作文题目 / 材料"
          :description="activeTask.prompt_text"
          class="submit-notice"
        />
        <el-alert
          v-if="activeTask.requirements"
          type="warning"
          :closable="false"
          show-icon
          title="写作要求"
          :description="activeTask.requirements"
          class="submit-notice"
        />

        <el-form label-position="top">
          <el-form-item
            v-for="question in activeTask.questions"
            :key="question.id"
            required
          >
            <template #label>
              <strong>{{ question.label }}</strong>
              <span class="question-requirement">{{ question.requirements || question.question_text }}</span>
            </template>
            <el-input
              v-model="answerMap[question.id]"
              type="textarea"
              :rows="8"
              maxlength="20000"
              show-word-limit
              :placeholder="`请输入${question.label}的作答内容`"
            />
            <div class="answer-meta">
              当前 {{ (answerMap[question.id] || '').trim().length }} 字
              <span v-if="activeTask.word_min"> · 要求不少于 {{ activeTask.word_min }} 字</span>
              <span v-if="activeTask.word_max"> · 不超过 {{ activeTask.word_max }} 字</span>
            </div>
          </el-form-item>
        </el-form>
        <el-alert
          v-if="submitError"
          type="error"
          :closable="false"
          show-icon
          :title="submitError"
          class="submit-error"
        />
      </template>
      <template #footer>
        <el-button @click="submitVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="submitAnswers"
        >
          提交并开始评价
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import PageHeader from '@/components/PageHeader.vue'
import ImageUploader from '@/components/ImageUploader.vue'
import { createImageSubmission, createSubmission, fetchStudentTasks } from '@/api/submission'
import { formatDateTime } from '@/utils/format'

const tasks = ref([])
const loading = ref(false)
const submitVisible = ref(false)
const submitting = ref(false)
const submitError = ref('')
const activeTask = ref(null)
const answerMap = reactive({})
const imageVisible = ref(false)
const imageSubmissionId = ref(null)
const imageCreating = ref(false)

function statusType(status) { return { published: 'success', closed: 'warning' }[status] || 'info' }
function statusLabel(status) { return { published: '进行中', closed: '已关闭' }[status] || status }
function submissionType(status) { return { draft: 'info', submitted: 'primary', evaluating: 'warning', evaluated: 'success', failed: 'danger' }[status] || 'info' }
function submissionLabel(status) { return { draft: '草稿', submitted: '已提交', evaluating: '评价中', evaluated: '评价完成', failed: '评价失败' }[status] || status }
function wordLabel(task) {
  if (!task.word_min && !task.word_max) return '字数不限'
  return `${task.word_min || 0} ~ ${task.word_max || '不限'} 字`
}

async function loadTasks() {
  loading.value = true
  try {
    const response = await fetchStudentTasks()
    tasks.value = response.data
  } finally {
    loading.value = false
  }
}

function openSubmit(task) {
  activeTask.value = task
  submitError.value = ''
  Object.keys(answerMap).forEach((key) => delete answerMap[key])
  task.questions.forEach((question) => {
    answerMap[question.id] = ''
  })
  submitVisible.value = true
}

async function submitAnswers() {
  if (!activeTask.value || submitting.value) return
  submitError.value = ''
  const answers = []
  for (const question of activeTask.value.questions) {
    const content = (answerMap[question.id] || '').trim()
    if (!content) {
      submitError.value = `${question.label} 尚未作答`
      return
    }
    if (activeTask.value.word_min && content.length < activeTask.value.word_min) {
      submitError.value = `${question.label} 字数不足：${content.length} / ${activeTask.value.word_min}`
      return
    }
    if (activeTask.value.word_max && content.length > activeTask.value.word_max) {
      submitError.value = `${question.label} 字数超限：${content.length} / ${activeTask.value.word_max}`
      return
    }
    answers.push({ question_id: question.id, content })
  }
  submitting.value = true
  try {
    const response = await createSubmission({ task_id: activeTask.value.id, answers })
    ElMessage.success(`提交成功，评价任务 #${response.data.answers.map((item) => item.evaluation_id).filter(Boolean).join('、')} 已进入后台队列`)
    submitVisible.value = false
    await loadTasks()
  } catch (error) {
    submitError.value = error.message || '提交失败'
  } finally {
    submitting.value = false
  }
}

function handleImageChanged(count) {
  if (count > 0) ElMessage.success(`当前已上传 ${count} 张作文照片`)
}

async function openImageSubmit(task) {
  activeTask.value = task
  imageSubmissionId.value = null
  imageVisible.value = true
  imageCreating.value = true
  try {
    const response = await createImageSubmission(task.id)
    imageSubmissionId.value = response.data.id
  } catch (requestError) {
    ElMessage.error(requestError.message || '无法创建图片提交流程')
    imageVisible.value = false
  } finally {
    imageCreating.value = false
  }
}

onMounted(loadTasks)
</script>

<style scoped>
.notice { margin-bottom: 16px; }
.task-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.task-card { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.task-card.is-overdue { opacity: 0.72; }
.task-card__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.task-card__head h2 { margin: 0 0 6px; font-size: 16px; }
.task-card__meta { color: var(--wm-text-secondary); font-size: 11px; }
.task-card__prompt { margin: 0; max-height: 72px; overflow: auto; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.8; }
.task-card__tags { display: flex; flex-wrap: wrap; gap: 6px; }
.task-card__actions { display: flex; flex-wrap: wrap; gap: 8px; }
.submit-notice { margin-bottom: 12px; }
.question-requirement { margin-left: 8px; color: var(--wm-text-secondary); font-size: 11px; font-weight: 400; }
.answer-meta { margin-top: 5px; color: var(--wm-text-secondary); font-size: 11px; }
.submit-error { margin-top: 12px; }

@media (max-width: 900px) {
  .task-grid { grid-template-columns: 1fr; }
}
</style>