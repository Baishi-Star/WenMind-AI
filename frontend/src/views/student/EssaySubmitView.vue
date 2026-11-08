<template>
  <div>
    <PageHeader
      title="作文提交"
      subtitle="选择题目、输入正文并保存草稿或正式提交；所有内容均通过后端写入 SQLite。"
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
              :rows="18"
              maxlength="20000"
              show-word-limit
              placeholder="请输入或粘贴作文正文；草稿也必须包含非空内容。"
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import PageHeader from '@/components/PageHeader.vue'
import { createEssay, fetchEssay, fetchEssayPrompts, fetchEssays, updateEssay } from '@/api/essay'
import { formatDateTime } from '@/utils/format'

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

const selectedPrompt = computed(() => prompts.value.find((item) => item.id === form.prompt_id))
const contentLength = computed(() => form.content.trim().length)
const canSave = computed(() => Boolean(form.prompt_id && contentLength.value > 0 && contentLength.value <= 20000 && !savingMode.value))

function statusType(status) { return { completed: 'success', failed: 'danger', evaluating: 'warning', submitted: 'primary', draft: 'info' }[status] || 'info' }
function statusLabel(status) { return { completed: '评价完成', failed: '评价失败', evaluating: '评价中', submitted: '已提交', draft: '草稿' }[status] || status }

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
}

async function saveEssay(mode) {
  if (!canSave.value) return
  savingMode.value = mode
  error.value = ''
  try {
    const payload = { prompt_id: form.prompt_id, content: form.content.trim(), submission_mode: mode }
    const response = editingEssayId.value
      ? await updateEssay(editingEssayId.value, payload)
      : await createEssay(payload)
    ElMessage.success(response.message)
    if (mode === 'submit') {
      await router.push('/student/essays')
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
}

function openEssay(essay) {
  if (essay.status === 'draft') router.push({ path: '/student/essays/new', query: { draft: essay.id } })
  else router.push('/student/evaluations')
}

onMounted(async () => {
  await Promise.all([loadPrompts(), loadHistory()])
  await loadDraft()
})
</script>

<style scoped>
.submit-layout { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 18px; align-items: start; }
.editor-card, .history-card { padding: 20px; }
.prompt-alert, .form-alert { margin-bottom: 16px; }
.editor-meta { display: flex; justify-content: space-between; gap: 12px; margin: -4px 0 16px; color: var(--wm-text-secondary); font-size: 12px; }
.editor-actions { display: flex; gap: 10px; }
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
</style>