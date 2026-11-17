<template>
  <div>
    <PageHeader
      title="我的写作任务"
      subtitle="查看教师下发的作文任务，提交后可自动进入多 Agent 评价。"
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
            作文题
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
      :title="imageDialogTitle"
      width="900px"
      :close-on-click-modal="false"
      :before-close="handleImageDialogClose"
      @closed="resetImageFlow"
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
        <div
          v-if="recognizing"
          class="recognize-progress"
        >
          <span>正在识别…已用 {{ recognizeElapsed }} 秒（通常 15~40 秒）</span>
          <el-alert
            v-if="recognizeElapsed >= 60"
            type="warning"
            :closable="false"
            show-icon
            title="图片较复杂，识别可能稍久，请勿关闭"
          />
        </div>
        <p
          v-if="lastRecognizeSeconds && !recognizing && imageStep === 'recognize'"
          class="recognize-cost"
        >
          识别耗时 {{ lastRecognizeSeconds }} 秒
        </p>

        <template v-if="imageStep === 'upload'">
          <ImageUploader
            v-if="imageSubmissionId"
            ref="imageUploaderRef"
            :submission-id="imageSubmissionId"
            @changed="handleImageChanged"
          />
          <el-alert
            v-if="imageError"
            type="error"
            :closable="false"
            show-icon
            :title="imageError"
            class="submit-error"
          />
        </template>

        <template v-else-if="imageStep === 'recognize'">
          <el-alert
            type="success"
            :closable="false"
            show-icon
            title="识别完成，请逐页核对并修改识别结果"
            class="submit-notice"
          />
          <el-alert
            v-if="imageError"
            type="error"
            :closable="false"
            show-icon
            :title="imageError"
            class="submit-error"
          />
          <div class="page-list">
            <article
              v-for="(file, index) in imageFiles"
              :key="file.id"
              class="page-card"
            >
              <div class="page-card__head">
                <strong>第 {{ index + 1 }} 页</strong>
                <el-tag
                  size="small"
                  :type="file.extraction_status === 'done' ? 'success' : 'danger'"
                >
                  {{ file.extraction_status === 'done' ? '已识别' : '识别失败' }}
                </el-tag>
              </div>
              <div class="page-card__body">
                <el-image
                  v-if="imagePreviews[file.id]"
                  :src="imagePreviews[file.id]"
                  :preview-src-list="[imagePreviews[file.id]]"
                  fit="contain"
                  class="page-thumb"
                />
                <div
                  v-else
                  class="page-thumb page-thumb--empty"
                >
                  图片加载中…
                </div>
                <div class="page-editor">
                  <p
                    v-if="file.extraction_status !== 'done'"
                    class="page-warn"
                  >
                    该页识别失败，可手动输入
                  </p>
                  <el-input
                    v-model="imageTexts[file.id]"
                    type="textarea"
                    :rows="8"
                    maxlength="20000"
                    show-word-limit
                    :placeholder="`请输入第 ${index + 1} 页的作文正文`"
                  />
                  <div class="page-meta">
                    当前 {{ (imageTexts[file.id] || '').trim().length }} 字
                  </div>
                </div>
              </div>
            </article>
          </div>
        </template>

        <template v-else-if="imageStep === 'confirm'">
          <div class="confirm-summary">
            <div>
              <span>共 {{ imageFiles.length }} 页</span>
              <span>合计 {{ imageTotalChars }} 字</span>
            </div>
            <div>
              <span>所属任务：{{ activeTask.title }}</span>
              <span>作文题：1 篇</span>
            </div>
          </div>
          <el-alert
            type="warning"
            :closable="false"
            show-icon
            title="确认后将进入 AI 评价队列，确认前可返回修改"
            class="submit-notice"
          />
          <el-alert
            v-if="imageError"
            type="error"
            :closable="false"
            show-icon
            :title="imageError"
            class="submit-error"
          />
        </template>

        <template v-else>
          <el-result
            icon="success"
            title="已提交，正在进入评价队列"
          />
          <p
            v-if="activeTask.questions.length > 1"
            class="done-hint"
          >
            请继续完成其余子题作答。
          </p>
        </template>
      </template>

      <template #footer>
        <template v-if="imageStep === 'upload'">
          <el-button
            :disabled="recognizing"
            @click="closeImageDialog"
          >
            关闭
          </el-button>
          <el-button
            v-if="imageError"
            :disabled="recognizing"
            @click="manualEntry"
          >
            手动录入
          </el-button>
          <el-button
            type="primary"
            :disabled="imageFileCount === 0"
            :loading="recognizing"
            @click="startRecognize"
          >
            {{ recognizing ? '正在识别文字，请稍候…' : '下一步：识别文字' }}
          </el-button>
        </template>
        <template v-else-if="imageStep === 'recognize'">
          <el-button
            :disabled="recognizing"
            @click="imageStep = 'upload'"
          >
            上一步
          </el-button>
          <el-button
            :disabled="recognizing"
            :loading="recognizing"
            @click="startRecognize"
          >
            {{ recognizing ? '正在重新识别…' : '重新识别' }}
          </el-button>
          <el-button
            type="primary"
            :disabled="recognizing"
            @click="goConfirm"
          >
            下一步：确认
          </el-button>
        </template>
        <template v-else-if="imageStep === 'confirm'">
          <el-button
            :disabled="confirming"
            @click="imageStep = 'recognize'"
          >
            上一步
          </el-button>
          <el-button
            type="primary"
            :loading="confirming"
            @click="confirmAndSubmit"
          >
            {{ confirming ? '提交中…' : '确认并提交' }}
          </el-button>
        </template>
        <template v-else>
          <el-button
            type="primary"
            @click="closeImageDialog"
          >
            关闭
          </el-button>
        </template>
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
            v-for="question in activeTask.questions.slice(0, 1)"
            :key="question.id"
            required
          >
            <template #label>
              <strong>作文正文</strong>
              <span class="question-requirement">{{ question.requirements || question.question_text }}</span>
            </template>
            <el-input
              v-model="answerMap[question.id]"
              type="textarea"
              :rows="8"
              maxlength="20000"
              show-word-limit
              placeholder="请输入作文正文"
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
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

import PageHeader from '@/components/PageHeader.vue'
import ImageUploader from '@/components/ImageUploader.vue'
import {
  confirmSubmissionExtraction,
  createImageSubmission,
  createSubmission,
  fetchStudentTasks,
  fetchSubmissionFiles,
  loadAuthorizedImage,
  submitImageSubmission,
  transcribeSubmission,
} from '@/api/submission'
import { formatDateTime } from '@/utils/format'

const tasks = ref([])
const loading = ref(false)
const router = useRouter()
const submitVisible = ref(false)
const submitting = ref(false)
const submitError = ref('')
const activeTask = ref(null)
const answerMap = reactive({})
const imageVisible = ref(false)
const imageSubmissionId = ref(null)
const imageCreating = ref(false)
const imageUploaderRef = ref(null)
const imageStep = ref('upload')
const imageFiles = ref([])
const imageTexts = reactive({})
const imagePreviews = reactive({})
const imageFileCount = ref(0)
const imageError = ref('')
const recognizing = ref(false)
const confirming = ref(false)
let imageObjectUrls = []
const recognizeElapsed = ref(0)
const lastRecognizeSeconds = ref(null)
let recognizeTimer = null

const imageDialogTitle = computed(() => {
  if (!activeTask.value) return '上传作文照片'
  const suffix = { upload: '上传作文照片', recognize: '识别与校对', confirm: '确认提交', done: '提交完成' }[imageStep.value] || ''
  return `${suffix}：${activeTask.value.title}`
})
const imageTotalChars = computed(() =>
  imageFiles.value.reduce((total, file) => total + (imageTexts[file.id] || '').trim().length, 0),
)

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
  const question = activeTask.value.questions[0]
  if (!question) {
    submitError.value = '该任务暂无可作答题目'
    return
  }
  const content = (answerMap[question.id] || '').trim()
  if (!content) {
    submitError.value = '请先填写作文正文'
    return
  }
  if (activeTask.value.word_min && content.length < activeTask.value.word_min) {
    submitError.value = `作文正文字数不足：${content.length} / ${activeTask.value.word_min}`
    return
  }
  if (activeTask.value.word_max && content.length > activeTask.value.word_max) {
    submitError.value = `作文正文字数超限：${content.length} / ${activeTask.value.word_max}`
    return
  }
  const answers = [{ question_id: question.id, content }]
  submitting.value = true
  try {
    const response = await createSubmission({ task_id: activeTask.value.id, answers })
    const evaluationId = response.data.answers?.find((item) => item.evaluation_id)?.evaluation_id
    submitVisible.value = false
    await loadTasks()
    if (evaluationId) {
      ElMessage.success('已提交，正在生成评价')
      router.push({ path: '/student/evaluations', query: { evaluationId } })
    } else {
      ElMessage.success('提交成功，评价任务已进入后台队列')
    }
  } catch (error) {
    submitError.value = error.message || '提交失败'
  } finally {
    submitting.value = false
  }
}

function handleImageChanged(count) {
  imageFileCount.value = count
}

function revokeImagePreviews() {
  imageObjectUrls.forEach((url) => URL.revokeObjectURL(url))
  imageObjectUrls = []
  Object.keys(imagePreviews).forEach((key) => delete imagePreviews[key])
}

async function loadImagePreviews(files) {
  revokeImagePreviews()
  await Promise.all(
    files.map(async (file) => {
      try {
        const url = await loadAuthorizedImage(file.id)
        imageObjectUrls.push(url)
        imagePreviews[file.id] = url
      } catch {
        // 单页预览失败不阻塞校对
      }
    }),
  )
}

function startRecognizeTimer() {
  stopRecognizeTimer()
  recognizeElapsed.value = 0
  recognizeTimer = window.setInterval(() => {
    recognizeElapsed.value += 1
  }, 1000)
}

function stopRecognizeTimer() {
  if (recognizeTimer) window.clearInterval(recognizeTimer)
  recognizeTimer = null
}

function resetImageFlow() {
  stopRecognizeTimer()
  revokeImagePreviews()
  imageStep.value = 'upload'
  imageFiles.value = []
  Object.keys(imageTexts).forEach((key) => delete imageTexts[key])
  imageFileCount.value = 0
  imageError.value = ''
  recognizing.value = false
  confirming.value = false
  recognizeElapsed.value = 0
  lastRecognizeSeconds.value = null
  imageSubmissionId.value = null
}

async function startRecognize() {
  if (!imageSubmissionId.value || recognizing.value) return
  if (!imageFiles.value.length && imageFileCount.value === 0) {
    imageError.value = '请先上传至少 1 张作文照片'
    return
  }
  imageError.value = ''
  recognizing.value = true
  const startedAt = Date.now()
  startRecognizeTimer()
  try {
    const response = await transcribeSubmission(imageSubmissionId.value)
    const files = response.data || []
    if (!files.length) {
      imageError.value = '未获取到识别结果，请确认已上传图片'
      return
    }
    imageFiles.value = files
    files.forEach((file) => {
      if (!(imageTexts[file.id] || '').trim()) {
        imageTexts[file.id] = file.extracted_text || ''
      }
    })
    await loadImagePreviews(files)
    lastRecognizeSeconds.value = Math.max(1, Math.round((Date.now() - startedAt) / 1000))
    imageStep.value = 'recognize'
    const failed = files.filter((file) => file.extraction_status !== 'done')
    if (failed.length) {
      imageError.value = `第 ${failed.map((file) => file.sort_order).join('、')} 页识别失败，可手动输入后继续`
    }
  } catch (error) {
    imageError.value = error.message || '识别失败，请重试'
  } finally {
    stopRecognizeTimer()
    recognizing.value = false
  }
}

async function manualEntry() {
  if (!imageSubmissionId.value) return
  imageError.value = ''
  try {
    const response = await fetchSubmissionFiles(imageSubmissionId.value)
    const files = response.data || []
    if (!files.length) {
      imageError.value = '没有可录入的页面，请先上传图片'
      return
    }
    imageFiles.value = files
    files.forEach((file) => {
      if (!(imageTexts[file.id] || '').trim()) imageTexts[file.id] = file.extracted_text || ''
    })
    await loadImagePreviews(files)
    imageStep.value = 'recognize'
  } catch (error) {
    imageError.value = error.message || '无法进入手动录入'
  }
}

function goConfirm() {
  if (recognizing.value) return
  if (!imageFiles.value.length) {
    imageError.value = '没有可确认的页面'
    return
  }
  for (const [index, file] of imageFiles.value.entries()) {
    if (!(imageTexts[file.id] || '').trim()) {
      imageError.value = `请补全第 ${index + 1} 页的识别文本`
      return
    }
  }
  imageError.value = ''
  imageStep.value = 'confirm'
}

async function confirmAndSubmit() {
  if (confirming.value || !imageSubmissionId.value) return
  const pages = imageFiles.value.map((file) => ({
    file_id: file.id,
    confirmed_text: (imageTexts[file.id] || '').trim(),
  }))
  if (pages.some((page) => !page.confirmed_text)) {
    imageError.value = '请补全所有页的识别文本'
    return
  }
  confirming.value = true
  imageError.value = ''
  try {
    await confirmSubmissionExtraction(imageSubmissionId.value, pages)
    const submitted = await submitImageSubmission(imageSubmissionId.value)
    const evaluationId = submitted.data.answers?.find((item) => item.evaluation_id)?.evaluation_id
    await loadTasks()
    ElMessage.success('已提交，正在生成评价')
    if (activeTask.value?.questions?.length > 1) {
      ElMessage.warning('请继续完成其余子题作答')
    }
    imageVisible.value = false
    if (evaluationId) {
      router.push({ path: '/student/evaluations', query: { evaluationId } })
    }
  } catch (error) {
    imageError.value = error.message || '提交失败，请重试当前步骤'
  } finally {
    confirming.value = false
  }
}

function handleImageDialogClose(done) {
  if (recognizing.value) {
    ElMessage.warning('正在识别文字，请稍候…')
    return
  }
  if (imageStep.value === 'recognize' || imageStep.value === 'confirm') {
    ElMessageBox.confirm('已识别的文本不会自动保存，确认关闭？', '确认关闭', { type: 'warning' })
      .then(() => done())
      .catch(() => {})
    return
  }
  done()
}

function closeImageDialog() {
  handleImageDialogClose(() => {
    imageVisible.value = false
  })
}

async function openImageSubmit(task) {
  activeTask.value = task
  resetImageFlow()
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

onBeforeUnmount(() => {
  stopRecognizeTimer()
  revokeImagePreviews()
})
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
.recognize-progress { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; color: var(--wm-text-secondary); font-size: 12px; }
.recognize-cost { margin: 0 0 12px; color: #047857; font-size: 12px; }
.page-list { display: grid; gap: 14px; max-height: 56vh; overflow: auto; padding-right: 4px; }
.page-card { border: 1px solid var(--wm-border); border-radius: 12px; padding: 12px; }
.page-card__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.page-card__body { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 12px; }
.page-thumb { width: 100%; height: 180px; border-radius: 8px; background: #f6f7fb; cursor: zoom-in; }
.page-thumb--empty { display: grid; place-items: center; color: var(--wm-text-secondary); font-size: 11px; cursor: default; }
.page-editor { display: flex; flex-direction: column; gap: 6px; }
.page-warn { margin: 0; color: #b45309; font-size: 11px; }
.page-meta { color: var(--wm-text-secondary); font-size: 11px; text-align: right; }
.confirm-summary { display: grid; gap: 6px; margin-bottom: 12px; padding: 12px 14px; border-radius: 10px; background: var(--wm-bg-soft); font-size: 12px; color: var(--wm-text-secondary); }
.confirm-summary div { display: flex; gap: 18px; flex-wrap: wrap; }
.done-hint { margin: 12px 0 0; color: #b45309; font-size: 12px; text-align: center; }

@media (max-width: 900px) {
  .task-grid { grid-template-columns: 1fr; }
}
</style>