<template>
  <div>
    <PageHeader
      title="作文提交"
      subtitle="拍照或上传作文图片，识别后可校对再提交；也可以直接粘贴文本。"
    >
      <template #tag>
        <el-tag
          type="success"
          effect="plain"
        >
          真实持久化
        </el-tag>
      </template>
    </PageHeader>
    <div class="submit-layout">
      <section class="wm-card editor-card">
        <el-tabs
          v-model="activeTab"
          class="submit-tabs"
        >
          <el-tab-pane
            label="拍照上传"
            name="image"
          >
            <div class="upload-zone">
              <el-upload
                drag
                :auto-upload="false"
                :show-file-list="false"
                accept="image/jpeg,image/png,image/webp"
                class="desktop-upload"
                :on-change="onUploadChange"
              >
                <el-icon class="el-icon--upload">
                  <UploadFilled />
                </el-icon>
                <div class="el-upload__text">
                  拖拽图片到此处，或<em>点击选择</em>
                </div>
                <div class="el-upload__tip">
                  支持 JPG / PNG / WebP，单张不超过 5MB
                </div>
              </el-upload>
              <el-button
                class="mobile-capture"
                :icon="Camera"
                @click="fileInput?.click()"
              >
                拍照 / 选择图片
              </el-button>
              <input
                ref="fileInput"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                class="hidden-input"
                @change="onFileInputChange"
              >
            </div>

            <div
              v-if="image.previewUrl"
              class="preview-row"
            >
              <img
                :src="image.previewUrl"
                class="preview-thumb"
                alt="作文图片预览"
              >
              <div class="preview-meta">
                <span>{{ formatSize(image.sizeBytes) }}</span>
                <div class="preview-actions">
                  <el-button
                    size="small"
                    :disabled="image.uploading"
                    @click="fileInput?.click()"
                  >
                    重新选择
                  </el-button>
                  <el-button
                    size="small"
                    type="danger"
                    plain
                    @click="removeImage"
                  >
                    移除
                  </el-button>
                </div>
              </div>
            </div>

            <el-alert
              v-if="image.uploading"
              type="info"
              :closable="false"
              show-icon
              title="正在上传图片…"
              class="state-alert"
            />
            <div
              v-if="image.error"
              class="error-bar"
            >
              <span>{{ image.error }}</span>
              <el-button
                size="small"
                @click="fileInput?.click()"
              >
                重试上传
              </el-button>
            </div>

            <div
              v-if="image.token && ocrEnabled"
              class="recognize-row"
            >
              <el-button
                type="primary"
                :loading="image.recognizing"
                @click="recognizeImage"
              >
                {{ image.recognizing ? '正在识别…' : image.ocrDone ? '重新识别' : '识别图片文字' }}
              </el-button>
              <span class="hint">识别后请核对并修改，再提交</span>
            </div>
            <el-alert
              v-if="image.recognizing"
              type="info"
              :closable="false"
              show-icon
              title="正在识别文字，约需 10~30 秒…"
              class="state-alert"
            />
            <el-alert
              v-if="image.ocrDone"
              type="success"
              :closable="false"
              show-icon
              :title="`识别完成，请核对并修改后提交（当前 ${contentLength} 字）`"
              class="state-alert"
            />
            <div
              v-if="image.recognizeFailed"
              class="error-bar"
            >
              <span>识别失败，请重传图片或手动输入正文</span>
              <el-button
                size="small"
                @click="recognizeImage"
              >
                重新识别
              </el-button>
              <el-button
                size="small"
                text
                @click="activeTab = 'text'"
              >
                改用文本输入
              </el-button>
            </div>
            <div
              v-if="!ocrEnabled && image.token"
              class="hint-bar"
            >
              当前仅支持图片存档，请手动录入正文
            </div>
          </el-tab-pane>
          <el-tab-pane
            label="粘贴文本"
            name="text"
          >
            <p class="hint panel-hint">
              可以直接在下方「作文正文」中输入或粘贴作文内容。
            </p>
          </el-tab-pane>
        </el-tabs>

        <el-form
          label-position="top"
          @submit.prevent
        >
          <el-form-item
            label="作文题目"
            required
          >
            <el-select
              v-model="form.prompt_id"
              placeholder="请选择作文题目"
              style="width: 100%"
              :loading="promptsLoading"
            >
              <el-option
                v-for="prompt in prompts"
                :key="prompt.id"
                :value="prompt.id"
                :label="prompt.title"
              />
            </el-select>
          </el-form-item>
          <el-alert
            v-if="selectedPrompt"
            type="info"
            :closable="false"
            show-icon
            title="写作要求"
            :description="selectedPrompt.requirements"
            class="prompt-alert"
          />
          <el-form-item
            label="作文正文"
            required
          >
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="16"
              maxlength="20000"
              show-word-limit
              placeholder="上传图片识别后会自动填入，可在此校对修改；也可直接输入或粘贴。"
            />
          </el-form-item>
          <div class="editor-meta">
            <span>正文字数：<strong>{{ contentLength }}</strong> / 20000</span>
            <span v-if="editingEssayId">正在编辑草稿 #{{ editingEssayId }}，修改正文会生成新内容版本</span>
            <span v-else>新作文将从内容版本 v1 开始</span>
          </div>
          <el-alert
            v-if="error"
            type="error"
            :closable="false"
            show-icon
            :title="error"
            class="form-alert"
          />
          <div class="editor-actions">
            <el-button
              :loading="savingMode === 'draft'"
              :disabled="!canSave"
              @click="saveEssay('draft')"
            >
              保存草稿
            </el-button>
            <el-button
              type="primary"
              :loading="savingMode === 'submit'"
              :disabled="!canSave"
              @click="saveEssay('submit')"
            >
              {{ editingEssayId ? '提交草稿' : '提交作文' }}
            </el-button>
            <el-button
              text
              @click="resetForm"
            >
              清空重填
            </el-button>
          </div>
        </el-form>
      </section>

      <aside class="wm-card history-card">
        <div class="history-card__head">
          <h2>最近提交</h2><el-button
            text
            type="primary"
            @click="router.push('/student/essays')"
          >
            全部作文
          </el-button>
        </div>
        <el-empty
          v-if="!historyLoading && recentEssays.length === 0"
          description="暂无作文记录"
          :image-size="70"
        />
        <button
          v-for="essay in recentEssays"
          :key="essay.id"
          type="button"
          class="history-item"
          @click="openEssay(essay)"
        >
          <span><strong>#{{ essay.id }}</strong> {{ essay.prompt_title || '自由作文' }}</span>
          <el-tag
            size="small"
            :type="statusType(essay.status)"
          >
            {{ statusLabel(essay.status) }}
          </el-tag>
          <small>v{{ essay.content_version }} · {{ essay.char_count }} 字 · {{ formatDateTime(essay.updated_at) }}</small>
        </button>
        <div
          v-if="historyLoading"
          class="history-loading"
        >
          正在读取提交历史…
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Camera, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import PageHeader from '@/components/PageHeader.vue'
import {
  createEssay,
  fetchEssay,
  fetchEssayPrompts,
  fetchEssays,
  fetchOcrStatus,
  ocrEssay,
  updateEssay,
  uploadEssayImage,
} from '@/api/essay'
import { formatDateTime } from '@/utils/format'

const MAX_IMAGE_MB = 5

const route = useRoute()
const router = useRouter()
const prompts = ref([])
const recentEssays = ref([])
const promptsLoading = ref(false)
const historyLoading = ref(false)
const savingMode = ref('')
const editingEssayId = ref(null)
const error = ref('')
const form = reactive({ prompt_id: null, content: '' })
const activeTab = ref('image')
const ocrEnabled = ref(false)
const fileInput = ref(null)
const image = reactive({
  token: '',
  previewUrl: '',
  sizeBytes: 0,
  uploading: false,
  recognizing: false,
  ocrText: '',
  ocrDone: false,
  recognizeFailed: false,
  error: '',
})

const selectedPrompt = computed(() => prompts.value.find((item) => item.id === form.prompt_id))
const contentLength = computed(() => form.content.trim().length)
const canSave = computed(() => Boolean(form.prompt_id && contentLength.value > 0 && contentLength.value <= 20000 && !savingMode.value))

function statusType(status) { return { completed: 'success', failed: 'danger', evaluating: 'warning', submitted: 'primary', draft: 'info' }[status] || 'info' }
function statusLabel(status) { return { completed: '评价完成', failed: '评价失败', evaluating: '评价中', submitted: '已提交', draft: '草稿' }[status] || status }
function formatSize(bytes) { return bytes ? `${(bytes / 1024 / 1024).toFixed(2)} MB` : '' }

async function loadPrompts() {
  promptsLoading.value = true
  try {
    const response = await fetchEssayPrompts()
    prompts.value = response.data
    if (!form.prompt_id && prompts.value.length) form.prompt_id = prompts.value[0].id
  } finally {
    promptsLoading.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const response = await fetchEssays({ page: 1, page_size: 6 })
    recentEssays.value = response.data.items
  } finally {
    historyLoading.value = false
  }
}

async function loadOcrFlag() {
  try {
    const response = await fetchOcrStatus()
    ocrEnabled.value = Boolean(response.data.enabled)
  } catch {
    ocrEnabled.value = false
  }
}

async function loadDraft() {
  const draftId = Number(route.query.draft)
  if (!draftId) return
  const response = await fetchEssay(draftId)
  if (response.data.status !== 'draft') {
    ElMessage.warning('已提交作文不能在原记录上编辑，请新建作文')
    return
  }
  editingEssayId.value = draftId
  form.prompt_id = response.data.prompt_id
  form.content = response.data.content
  if (response.data.source_type === 'image') {
    image.token = response.data.image_path || ''
    image.ocrText = response.data.ocr_text || ''
    image.ocrDone = Boolean(response.data.ocr_text)
  }
}

async function compressImage(file) {
  if (!window.createImageBitmap) return file
  try {
    const bitmap = await createImageBitmap(file)
    const largest = Math.max(bitmap.width, bitmap.height)
    const scale = largest > 1600 ? 1600 / largest : 1
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85))
    if (!blob) return file
    return new File([blob], `${file.name.replace(/\.[^.]+$/, '')}.jpg`, { type: 'image/jpeg' })
  } catch {
    return file
  }
}

function setPreview(file) {
  if (image.previewUrl) URL.revokeObjectURL(image.previewUrl)
  image.previewUrl = URL.createObjectURL(file)
}

async function handleFile(rawFile) {
  if (!rawFile) return
  image.error = ''
  image.recognizeFailed = false
  image.ocrDone = false
  image.ocrText = ''
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(rawFile.type)) {
    image.error = '仅支持 JPG、PNG、WebP 格式的图片'
    return
  }
  if (rawFile.size > MAX_IMAGE_MB * 1024 * 1024) {
    image.error = `图片大小不能超过 ${MAX_IMAGE_MB} MB`
    return
  }
  const compressed = await compressImage(rawFile)
  if (compressed.size > MAX_IMAGE_MB * 1024 * 1024) {
    image.error = `图片大小不能超过 ${MAX_IMAGE_MB} MB`
    return
  }
  setPreview(compressed)
  image.sizeBytes = compressed.size
  image.uploading = true
  image.token = ''
  try {
    const formData = new FormData()
    formData.append('image', compressed)
    const response = await uploadEssayImage(formData)
    image.token = response.data.image_token
    image.sizeBytes = response.data.size_bytes
    ocrEnabled.value = Boolean(response.data.ocr_enabled)
  } catch (requestError) {
    image.error = requestError.message || '图片上传失败，请重试'
  } finally {
    image.uploading = false
  }
}

function onUploadChange(uploadFile) {
  handleFile(uploadFile.raw)
}

function onFileInputChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  handleFile(file)
}

async function recognizeImage() {
  if (!image.token) return
  if (!ocrEnabled.value) {
    ElMessage.warning('当前未启用图片识别，请手动录入正文')
    return
  }
  image.recognizing = true
  image.recognizeFailed = false
  image.error = ''
  try {
    const response = await ocrEssay(image.token)
    if (response.data.status === 'parsed') {
      image.ocrText = response.data.text
      image.ocrDone = true
      form.content = response.data.text
      ElMessage.success('识别完成，请核对并修改后提交')
    } else {
      image.recognizeFailed = true
      image.ocrDone = false
    }
  } catch {
    image.recognizeFailed = true
    image.ocrDone = false
  } finally {
    image.recognizing = false
  }
}

function removeImage() {
  if (image.previewUrl) URL.revokeObjectURL(image.previewUrl)
  image.previewUrl = ''
  image.token = ''
  image.sizeBytes = 0
  image.ocrText = ''
  image.ocrDone = false
  image.recognizeFailed = false
  image.error = ''
}

async function saveEssay(mode) {
  if (!canSave.value) return
  savingMode.value = mode
  error.value = ''
  try {
    const payload = { prompt_id: form.prompt_id, content: form.content.trim(), submission_mode: mode }
    if (activeTab.value === 'image' && image.token) {
      payload.source_type = 'image'
      payload.image_path = image.token
      payload.ocr_text = image.ocrText || null
    }
    const response = editingEssayId.value
      ? await updateEssay(editingEssayId.value, payload)
      : await createEssay(payload)
    ElMessage.success(response.message)
    if (mode === 'submit') {
      await router.push('/student/evaluations')
    } else {
      editingEssayId.value = response.data.id
      await loadHistory()
    }
  } catch (requestError) {
    error.value = requestError.message || '保存失败'
  } finally {
    savingMode.value = ''
  }
}

async function resetForm() {
  if (form.content) {
    try {
      await ElMessageBox.confirm('清空当前未保存的正文？已保存的草稿不会受影响。', '确认清空', { type: 'warning' })
    } catch {
      return
    }
  }
  form.content = ''
  editingEssayId.value = null
  error.value = ''
  removeImage()
}

function openEssay(essay) {
  if (essay.status === 'draft') router.push({ path: '/student/essays/new', query: { draft: essay.id } })
  else router.push('/student/evaluations')
}

onMounted(async () => {
  await Promise.all([loadPrompts(), loadHistory(), loadOcrFlag()])
  await loadDraft()
})

onBeforeUnmount(() => {
  if (image.previewUrl) URL.revokeObjectURL(image.previewUrl)
})
</script>

<style scoped>
.submit-layout { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 18px; align-items: start; }
.editor-card, .history-card { padding: 20px; }
.submit-tabs { margin-bottom: 12px; }
.prompt-alert, .form-alert, .state-alert { margin-bottom: 14px; }
.upload-zone { display: grid; gap: 10px; }
.desktop-upload :deep(.el-upload-dragger) { width: 100%; }
.mobile-capture { display: none; width: 100%; }
.hidden-input { display: none; }
.preview-row { display: flex; align-items: flex-start; gap: 14px; margin-top: 14px; }
.preview-thumb { width: 132px; height: 132px; object-fit: cover; border-radius: 10px; border: 1px solid var(--wm-border); }
.preview-meta { display: flex; flex-direction: column; gap: 8px; }
.preview-meta span { color: var(--wm-text-secondary); font-size: 12px; }
.preview-actions { display: flex; gap: 8px; }
.recognize-row { display: flex; align-items: center; gap: 12px; margin: 14px 0; flex-wrap: wrap; }
.hint { color: var(--wm-text-secondary); font-size: 12px; }
.panel-hint { margin: 4px 0 12px; }
.hint-bar { margin: 12px 0; padding: 10px 12px; border-radius: 8px; background: var(--wm-bg-soft); color: var(--wm-text-secondary); font-size: 12px; }
.error-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 12px 0; padding: 10px 12px; border-radius: 8px; background: #fef2f2; color: #b91c1c; font-size: 12px; }
.editor-meta { display: flex; justify-content: space-between; gap: 12px; margin: -4px 0 16px; color: var(--wm-text-secondary); font-size: 12px; }
.editor-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.history-card__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.history-card__head h2 { margin: 0; font-size: 16px; }
.history-item { width: 100%; display: grid; grid-template-columns: 1fr auto; gap: 7px; padding: 11px 8px; text-align: left; border: 0; border-bottom: 1px solid var(--wm-border); background: transparent; cursor: pointer; }
.history-item:hover { background: var(--wm-bg-soft); }
.history-item small { grid-column: 1 / -1; color: var(--wm-text-secondary); }
.history-loading { padding: 20px; text-align: center; color: var(--wm-text-secondary); }

@media (max-width: 1000px) {
  .submit-layout { grid-template-columns: 1fr; }
  .editor-meta { flex-direction: column; }
}

@media (max-width: 760px) {
  .desktop-upload { display: none; }
  .mobile-capture { display: block; }
  .preview-row { flex-direction: column; }
  .preview-thumb { width: 100%; height: auto; max-height: 260px; }
  .editor-actions .el-button { flex: 1; margin-left: 0; }
  .recognize-row .el-button { width: 100%; }
}
</style>