<template>
  <el-dialog
    v-model="visible"
    title="对本次评价提出异议"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      title="申诉用于核对评价依据，不代表自动加分"
      description="提交后将生成 pending 申诉记录，最终结果由教师复核；AI 原始评价不会被覆盖。"
      class="appeal-notice"
    />
    <el-descriptions
      v-if="feedbackItem"
      :column="1"
      border
      class="appeal-target"
    >
      <el-descriptions-item label="争议评价项">
        #{{ feedbackItem.id }} · {{ feedbackItem.content }}
      </el-descriptions-item>
    </el-descriptions>
    <el-form label-position="top">
      <el-form-item
        label="申诉原因"
        required
      >
        <el-select
          v-model="form.reason_type"
          style="width: 100%"
        >
          <el-option
            v-for="item in reasonOptions"
            :key="item.value"
            :value="item.value"
            :label="item.label"
          />
        </el-select>
      </el-form-item>
      <el-form-item
        label="争议维度"
        required
      >
        <el-select
          v-model="form.dimension"
          style="width: 100%"
        >
          <el-option
            value="content"
            label="内容"
          />
          <el-option
            value="organization"
            label="组织结构"
          />
          <el-option
            value="language"
            label="语言"
          />
          <el-option
            value="topic"
            label="审题"
          />
          <el-option
            value="overall"
            label="整体评价"
          />
        </el-select>
      </el-form-item>
      <el-form-item
        label="学生补充说明"
        required
      >
        <el-input
          v-model.trim="form.description"
          type="textarea"
          :rows="5"
          minlength="5"
          maxlength="2000"
          show-word-limit
          placeholder="请说明哪一处评价不准确、你的表达意图，以及希望教师重点核对什么。"
        />
      </el-form-item>
      <el-form-item
        v-if="selectedEvidence"
        label="关联原文证据（后端将再次核验）"
      >
        <div class="appeal-evidence">
          <el-tag
            type="success"
            size="small"
          >
            原文已核验
          </el-tag>
          <span>{{ selectedEvidence.start_char }}–{{ selectedEvidence.end_char }}</span>
          <blockquote>“{{ selectedEvidence.quote }}”</blockquote>
        </div>
      </el-form-item>
      <el-alert
        v-else
        type="info"
        :closable="false"
        show-icon
        title="未选择单独原文证据，将保留评价项已有证据快照。"
      />
    </el-form>
    <template #footer>
      <el-button @click="visible = false">
        取消
      </el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="form.description.trim().length < 5"
        @click="submitAppeal"
      >
        提交申诉
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { createAppeal } from '@/api/appeal'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  evaluation: { type: Object, required: true },
  feedbackItem: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'submitted'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})
const submitting = ref(false)
const selectedEvidence = ref(null)
const form = reactive({
  reason_type: 'creative_expression_misjudged',
  dimension: 'overall',
  description: '',
})

const reasonOptions = [
  { value: 'score_low', label: '评分偏低' },
  { value: 'evidence_mismatch', label: '原文证据不准确或引用错误' },
  { value: 'intent_misunderstood', label: 'AI 对观点或表达意图理解有偏差' },
  { value: 'creative_expression_misjudged', label: '个性表达被误判' },
  { value: 'missed_strength', label: '遗漏重要优点或问题' },
  { value: 'rubric_disagreement', label: '评分标准理解存在分歧' },
  { value: 'other', label: '其他' },
]

watch(visible, (value) => {
  if (!value) return
  form.reason_type = 'creative_expression_misjudged'
  form.dimension = props.feedbackItem?.dimension || 'overall'
  form.description = ''
  selectedEvidence.value = props.feedbackItem?.evidence?.find((item) => item.verified_status === 'verified') || null
})

async function submitAppeal() {
  if (form.description.trim().length < 5 || submitting.value) return
  submitting.value = true
  try {
    const response = await createAppeal({
      evaluation_id: props.evaluation.id,
      feedback_item_id: props.feedbackItem?.id || null,
      reason_type: form.reason_type,
      dimension: form.dimension,
      description: form.description,
      evidence: selectedEvidence.value,
    })
    ElMessage.success(`申诉 #${response.data.id} 已提交，等待教师复核`)
    visible.value = false
    emit('submitted', response.data)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.appeal-notice, .appeal-target { margin-bottom: 16px; }
.appeal-evidence { width: 100%; padding: 12px; border-radius: 10px; background: var(--wm-bg-soft); }
.appeal-evidence > span { margin-left: 8px; color: var(--wm-text-secondary); font-size: 11px; }
.appeal-evidence blockquote { margin: 8px 0 0; line-height: 1.8; }
</style>