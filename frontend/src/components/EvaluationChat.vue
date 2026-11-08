<template>
  <section class="wm-card evaluation-chat">
    <div class="section-head">
      <h2>多轮追问</h2>
      <span>对话关联当前作文、评价、证据与历史记录，全部保存到 SQLite</span>
    </div>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="可以质疑评价，也可以要求保留个人表达风格"
      description="系统不会因为表达非标准就直接判错；Mock 追问只演示流程，真实语义回答需配置 LLM。"
      class="chat-notice"
    />

    <div
      ref="historyContainer"
      class="chat-history"
    >
      <el-empty
        v-if="!loading && questions.length === 0"
        description="暂无追问记录，可以从下方推荐问题开始"
      />
      <article
        v-for="record in questions"
        :key="record.id"
        class="chat-turn"
      >
        <div class="chat-question">
          <span>你</span><p>{{ record.question }}</p><small>{{ formatDateTime(record.created_at) }}</small>
        </div>
        <div
          class="chat-answer"
          :class="{ 'is-failed': record.status === 'failed' }"
        >
          <div class="chat-answer__meta">
            <strong>WenMind AI</strong>
            <el-tag
              size="small"
              :type="record.execution_mode === 'mock' ? 'warning' : 'success'"
              effect="plain"
            >
              {{ record.execution_mode === 'mock' ? 'Mock 非模型推理' : record.model_name }}
            </el-tag>
            <el-tag
              size="small"
              :type="record.status === 'completed' ? 'success' : 'danger'"
              effect="plain"
            >
              {{ record.status }}
            </el-tag>
          </div>
          <p>{{ record.answer || record.error_message }}</p>
          <div
            v-if="record.evidence?.length"
            class="chat-evidence"
          >
            <div
              v-for="(evidence, index) in record.evidence"
              :key="index"
            >
              <el-tag
                size="small"
                :type="evidence.verified_status === 'verified' ? 'success' : 'warning'"
                effect="plain"
              >
                {{ evidence.verified_status === 'verified' ? '原文已核验' : '待核验' }}
              </el-tag>
              “{{ evidence.quote }}”
            </div>
          </div>
          <ul v-if="record.suggestions?.length">
            <li
              v-for="suggestion in record.suggestions"
              :key="suggestion"
            >
              {{ suggestion }}
            </li>
          </ul>
        </div>
      </article>
      <div
        v-if="loading"
        class="chat-loading"
      >
        <el-icon class="is-loading">
          <Loading />
        </el-icon> 正在读取历史追问
      </div>
    </div>

    <div class="quick-questions">
      <el-button
        v-for="item in quickQuestions"
        :key="item"
        size="small"
        round
        @click="questionText = item"
      >
        {{ item }}
      </el-button>
    </div>
    <el-form
      class="chat-form"
      @submit.prevent="submitQuestion"
    >
      <el-select
        v-model="selectedFeedbackId"
        clearable
        placeholder="关联具体评价项（可选）"
        class="chat-form__select"
      >
        <el-option
          v-for="item in feedbackItems"
          :key="item.id"
          :value="item.id"
          :label="`#${item.id} ${item.content.slice(0, 45)}`"
        />
      </el-select>
      <el-input
        v-model.trim="questionText"
        type="textarea"
        :rows="3"
        maxlength="1000"
        show-word-limit
        placeholder="例如：如果保留我的表达风格，应该如何修改？"
        @keydown.ctrl.enter="submitQuestion"
      />
      <div class="chat-form__actions">
        <span>Ctrl + Enter 发送；每次提问都会生成数据库记录</span>
        <el-button
          type="primary"
          native-type="submit"
          :loading="sending"
          :disabled="questionText.length < 2"
        >
          发送追问
        </el-button>
      </div>
    </el-form>
    <el-alert
      v-if="error"
      type="error"
      :closable="false"
      show-icon
      :title="error"
      class="chat-error"
    />
  </section>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'

import { createQuestion, fetchQuestions } from '@/api/question'
import { formatDateTime } from '@/utils/format'

const props = defineProps({
  evaluationId: { type: Number, required: true },
  feedbackItems: { type: Array, default: () => [] },
})

const questions = ref([])
const questionText = ref('')
const selectedFeedbackId = ref(null)
const loading = ref(false)
const sending = ref(false)
const error = ref('')
const historyContainer = ref(null)

const quickQuestions = [
  '为什么这一项得分较低？',
  '这句话具体有什么问题？',
  '我认为这个表达是有意设计的，为什么被判定为问题？',
  '如果保留我的表达风格，应该如何修改？',
  '有没有其他修改方式？',
]

async function loadQuestions() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetchQuestions(props.evaluationId)
    questions.value = response.data
    await scrollToBottom()
  } catch (requestError) {
    error.value = requestError.message || '追问记录加载失败'
  } finally {
    loading.value = false
  }
}

async function submitQuestion() {
  if (questionText.value.length < 2 || sending.value) return
  sending.value = true
  error.value = ''
  try {
    const response = await createQuestion(props.evaluationId, {
      question: questionText.value,
      feedback_item_id: selectedFeedbackId.value || null,
    })
    questions.value.push(response.data)
    questionText.value = ''
    await scrollToBottom()
  } catch (requestError) {
    error.value = requestError.message || '追问失败，请稍后重试'
    await loadQuestions()
  } finally {
    sending.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  if (historyContainer.value) historyContainer.value.scrollTop = historyContainer.value.scrollHeight
}

watch(() => props.evaluationId, loadQuestions, { immediate: true })
</script>

<style scoped>
.evaluation-chat { padding: 20px; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.section-head h2 { margin: 0; font-size: 17px; }
.section-head span { color: var(--wm-text-secondary); font-size: 12px; }
.chat-notice { margin-bottom: 14px; }
.chat-history { max-height: 520px; overflow: auto; padding: 4px 4px 4px 0; }
.chat-turn { margin-bottom: 16px; }
.chat-question { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; gap: 10px; align-items: start; margin-left: 12%; }
.chat-question > span { padding: 5px 8px; border-radius: 8px; background: var(--wm-primary); color: #fff; font-size: 12px; text-align: center; }
.chat-question p { margin: 0; padding: 10px 12px; border-radius: 10px; background: #eef0ff; font-size: 13px; line-height: 1.8; }
.chat-question small { color: var(--wm-text-secondary); font-size: 10px; }
.chat-answer { margin: 8px 12% 0 0; padding: 12px; border-radius: 10px; background: var(--wm-bg-soft); }
.chat-answer.is-failed { background: #fef2f2; }
.chat-answer__meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.chat-answer > p { margin: 10px 0 0; font-size: 13px; line-height: 1.85; white-space: pre-wrap; }
.chat-answer ul { margin: 10px 0 0; padding-left: 18px; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.8; }
.chat-evidence { margin-top: 10px; display: grid; gap: 6px; font-size: 12px; }
.chat-evidence > div { display: flex; gap: 8px; align-items: flex-start; }
.chat-loading { padding: 20px; text-align: center; color: var(--wm-text-secondary); }
.quick-questions { display: flex; flex-wrap: wrap; gap: 7px; margin: 14px 0; }
.chat-form { display: grid; gap: 10px; }
.chat-form__actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.chat-form__actions span { color: var(--wm-text-secondary); font-size: 11px; }
.chat-error { margin-top: 12px; }
</style>