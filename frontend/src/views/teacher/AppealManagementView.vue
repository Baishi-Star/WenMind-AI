<template>
  <div>
    <PageHeader
      title="申诉管理"
      subtitle="查看授权班级的学生申诉、作文原文、AI 原始评价和证据，并完成可追溯的人工复核。"
    >
      <template #tag>
        <el-tag
          type="success"
          effect="plain"
        >
          真实复核记录
        </el-tag>
      </template>
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadAppeals"
        >
          刷新
        </el-button>
      </template>
    </PageHeader>

    <section class="wm-card filter-card">
      <el-form inline>
        <el-form-item label="班级">
          <el-select
            v-model="filters.class_id"
            clearable
            placeholder="全部授权班级"
            style="width: 190px"
            @change="loadAppeals"
          >
            <el-option
              v-for="item in classes"
              :key="item.id"
              :value="item.id"
              :label="item.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="处理状态">
          <el-select
            v-model="filters.status"
            clearable
            placeholder="全部状态"
            style="width: 150px"
            @change="loadAppeals"
          >
            <el-option
              v-for="item in statusOptions"
              :key="item.value"
              :value="item.value"
              :label="item.label"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="申诉原因">
          <el-select
            v-model="filters.reason_type"
            clearable
            placeholder="全部类型"
            style="width: 190px"
            @change="loadAppeals"
          >
            <el-option
              v-for="item in reasonOptions"
              :key="item.value"
              :value="item.value"
              :label="item.label"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </section>

    <section class="wm-card list-card">
      <el-table
        v-loading="loading"
        :data="appeals"
        empty-text="当前筛选条件下没有申诉"
      >
        <el-table-column
          prop="id"
          label="申诉"
          width="80"
        >
          <template #default="{ row }">
            #{{ row.id }}
          </template>
        </el-table-column>
        <el-table-column
          label="学生 / 班级"
          min-width="190"
        >
          <template #default="{ row }">
            <strong>{{ row.student_name }}</strong>
            <div class="muted">
              {{ row.class_names.join('、') || '未分班' }}
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="作文 / 评价"
          min-width="220"
        >
          <template #default="{ row }">
            {{ row.essay_title }}
            <div class="muted">
              评价 #{{ row.evaluation_id }} · 作文 #{{ row.essay_id }}
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="争议维度"
          width="105"
        >
          <template #default="{ row }">
            {{ dimensionLabel(row.dimension) }}
          </template>
        </el-table-column>
        <el-table-column
          label="申诉原因"
          min-width="160"
        >
          <template #default="{ row }">
            {{ reasonLabel(row.reason_type) }}
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="105"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="statusType(row.status)"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="提交时间"
          width="165"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.submitted_at) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="110"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              size="small"
              :loading="detailLoadingId === row.id"
              @click="openDetail(row.id)"
            >
              {{ ['pending', 'reviewing'].includes(row.status) ? '去复核' : '查看复核' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-drawer
      v-model="drawerVisible"
      size="82%"
      :title="detail ? `申诉 #${detail.id} 复核工作台` : '申诉复核'"
      class="review-drawer"
    >
      <div v-loading="detailLoadingId !== null">
        <template v-if="detail">
          <section class="review-summary">
            <div>
              <span class="eyebrow">STUDENT APPEAL</span>
              <h2>{{ detail.student_name }} · {{ detail.essay_title }}</h2>
              <p>{{ detail.class_names.join('、') }} · 申诉提交 {{ formatDateTime(detail.submitted_at) }}</p>
            </div>
            <el-tag
              :type="statusType(detail.status)"
              effect="dark"
            >
              {{ statusLabel(detail.status) }}
            </el-tag>
          </section>

          <el-tabs
            v-model="activeTab"
            class="review-tabs"
          >
            <el-tab-pane
              label="申诉与作文原文"
              name="appeal"
            >
              <div class="two-column">
                <section class="sub-card">
                  <h3>学生申诉理由</h3>
                  <el-descriptions
                    :column="1"
                    border
                  >
                    <el-descriptions-item label="申诉原因">
                      {{ reasonLabel(detail.reason_type) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="争议维度">
                      {{ dimensionLabel(detail.dimension) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="学生说明">
                      {{ detail.description }}
                    </el-descriptions-item>
                  </el-descriptions>
                  <div
                    v-for="item in detail.appeal_items"
                    :key="item.id"
                    class="appeal-evidence"
                  >
                    <span>关联评价项 #{{ item.feedback_item_id ?? '未指定' }}</span>
                    <blockquote
                      v-for="(evidence, index) in item.evidence"
                      :key="index"
                    >
                      “{{ evidence.quote }}”
                    </blockquote>
                  </div>
                </section>
                <section class="sub-card">
                  <h3>作文原文</h3>
                  <div class="essay-text">
                    {{ detail.essay_content }}
                  </div>
                </section>
              </div>
            </el-tab-pane>

            <el-tab-pane
              label="AI 原始评价"
              name="ai"
            >
              <div class="dimension-strip">
                <div
                  v-for="item in detail.evaluation.dimension_scores"
                  :key="item.dimension"
                >
                  <span>{{ dimensionLabel(item.dimension) }}</span>
                  <strong>{{ item.original_score ?? '—' }}/{{ item.max_score }}</strong>
                  <small>教师最终值 {{ item.final_score ?? '未复核' }}</small>
                </div>
              </div>
              <el-alert
                type="info"
                :closable="false"
                show-icon
                title="以下为不可覆盖的 AI 原始反馈"
                description="教师修改、删除和新增内容会以叠加记录保存，不修改原始文本。"
                class="review-alert"
              />
              <article
                v-for="item in detail.feedback_items.filter((row) => !row.teacher_feedback)"
                :key="item.id"
                class="ai-feedback"
              >
                <div class="ai-feedback__head">
                  <el-tag
                    size="small"
                    effect="plain"
                  >
                    {{ dimensionLabel(item.dimension) }}
                  </el-tag>
                  <el-tag
                    size="small"
                    :type="item.verified_status === 'verified' ? 'success' : 'warning'"
                  >
                    {{ item.verified_status }}
                  </el-tag>
                  <span>#{{ item.id }}</span>
                </div>
                <p><strong>AI：</strong>{{ item.content }}</p>
                <p v-if="item.suggestion">
                  <strong>建议：</strong>{{ item.suggestion }}
                </p>
                <blockquote
                  v-for="(evidence, index) in item.evidence"
                  :key="index"
                >
                  “{{ evidence.quote }}”
                </blockquote>
              </article>
            </el-tab-pane>

            <el-tab-pane
              label="教师复核"
              name="review"
            >
              <el-alert
                v-if="!['pending', 'reviewing'].includes(detail.status)"
                type="success"
                :closable="false"
                show-icon
                title="该申诉已完成复核"
                description="可查看历史复核记录；不能重复提交复核。"
                class="review-alert"
              />
              <section
                v-for="record in detail.review_records"
                :key="record.id"
                class="history-review"
              >
                <strong>复核 #{{ record.id }} · {{ record.decision }} · {{ formatDateTime(record.reviewed_at) }}</strong>
                <p>{{ record.review_comment }}</p>
                <small>原始分 {{ JSON.stringify(record.original_scores) }} / 教师最终分 {{ JSON.stringify(record.revised_scores) }}</small>
              </section>

              <template v-if="['pending', 'reviewing'].includes(detail.status)">
                <el-form
                  label-position="top"
                  class="review-form"
                >
                  <div class="form-row">
                    <el-form-item
                      label="复核结论"
                      required
                    >
                      <el-radio-group v-model="reviewForm.decision">
                        <el-radio-button value="adjust">
                          调整评价
                        </el-radio-button>
                        <el-radio-button value="uphold">
                          维持 AI 评价
                        </el-radio-button>
                        <el-radio-button value="need_more_info">
                          要求补充说明
                        </el-radio-button>
                      </el-radio-group>
                    </el-form-item>
                  </div>

                  <template v-if="reviewForm.decision === 'adjust'">
                    <div class="section-title">
                      维度最终诊断值（1–5，不计算加权总分）
                    </div>
                    <div class="score-row">
                      <el-form-item
                        v-for="item in detail.evaluation.dimension_scores"
                        :key="item.dimension"
                        :label="dimensionLabel(item.dimension)"
                      >
                        <el-input-number
                          v-model="reviewForm.dimension_scores[item.dimension]"
                          :min="1"
                          :max="5"
                        />
                      </el-form-item>
                    </div>

                    <div class="section-title">
                      AI 反馈处理（原文保持不变，仅叠加教师结果）
                    </div>
                    <article
                      v-for="item in detail.feedback_items.filter((row) => !row.teacher_feedback)"
                      :key="item.id"
                      class="change-row"
                    >
                      <div class="change-row__title">
                        <strong>#{{ item.id }} · {{ item.content }}</strong>
                        <el-select
                          v-model="reviewForm.feedback_changes[item.id].action"
                          style="width: 110px"
                        >
                          <el-option
                            value="kept"
                            label="保留"
                          />
                          <el-option
                            value="modified"
                            label="修改"
                          />
                          <el-option
                            value="deleted"
                            label="删除"
                          />
                        </el-select>
                      </div>
                      <template v-if="reviewForm.feedback_changes[item.id].action === 'modified'">
                        <el-input
                          v-model="reviewForm.feedback_changes[item.id].content"
                          type="textarea"
                          :rows="2"
                          placeholder="教师修改后的评价文字"
                        />
                        <el-input
                          v-model="reviewForm.feedback_changes[item.id].suggestion"
                          type="textarea"
                          :rows="2"
                          placeholder="教师修改后的建议（可选）"
                        />
                      </template>
                    </article>

                    <div class="section-title">
                      新增教师反馈
                    </div>
                    <div
                      v-for="(row, index) in reviewForm.added_feedback"
                      :key="index"
                      class="added-feedback"
                    >
                      <el-select
                        v-model="row.dimension"
                        style="width: 130px"
                      >
                        <el-option
                          v-for="item in dimensions"
                          :key="item.value"
                          :value="item.value"
                          :label="item.label"
                        />
                      </el-select>
                      <el-input
                        v-model="row.content"
                        placeholder="教师新增反馈内容"
                      />
                      <el-input
                        v-model="row.suggestion"
                        placeholder="建议（可选）"
                      />
                      <el-button
                        text
                        type="danger"
                        @click="reviewForm.added_feedback.splice(index, 1)"
                      >
                        移除
                      </el-button>
                    </div>
                    <el-button
                      size="small"
                      @click="reviewForm.added_feedback.push({ dimension: 'overall', content: '', suggestion: '' })"
                    >
                      + 新增反馈
                    </el-button>

                    <el-form-item label="教师综合评价（可选，作为叠加意见保存）">
                      <el-input
                        v-model="reviewForm.revised_summary"
                        type="textarea"
                        :rows="3"
                        maxlength="2000"
                        show-word-limit
                        placeholder="不覆盖 AI 综合反馈，另存教师意见"
                      />
                    </el-form-item>
                  </template>

                  <div class="section-title">
                    争议归因（必须由教师确认）
                  </div>
                  <el-alert
                    v-if="detail.classification_suggestions.length"
                    type="info"
                    :closable="false"
                    show-icon
                    title="规则辅助预归类（非真实模型）"
                    class="suggestion-alert"
                  >
                    <template #default>
                      <button
                        v-for="suggestion in detail.classification_suggestions"
                        :key="suggestion.tag_code"
                        type="button"
                        class="suggestion-chip"
                        @click="toggleTag(suggestion.tag_code)"
                      >
                        {{ suggestion.label }}
                      </button>
                    </template>
                  </el-alert>
                  <el-checkbox-group v-model="reviewForm.classification_codes">
                    <el-checkbox
                      v-for="item in tagOptions"
                      :key="item.value"
                      :value="item.value"
                    >
                      {{ item.label }}
                    </el-checkbox>
                  </el-checkbox-group>
                  <el-form-item label="归因说明">
                    <el-input
                      v-model="reviewForm.classification_note"
                      type="textarea"
                      :rows="2"
                      maxlength="1000"
                    />
                  </el-form-item>

                  <el-form-item
                    label="修改 / 复核原因"
                    required
                  >
                    <el-input
                      v-model="reviewForm.change_reason"
                      type="textarea"
                      :rows="3"
                      maxlength="2000"
                      show-word-limit
                      placeholder="必须说明复核依据；该原因会进入复核记录并展示给学生"
                    />
                  </el-form-item>
                  <el-alert
                    v-if="reviewError"
                    type="error"
                    :closable="false"
                    show-icon
                    :title="reviewError"
                    class="review-alert"
                  />
                  <el-button
                    type="primary"
                    :loading="submitting"
                    @click="submitReview"
                  >
                    提交复核并记录争议
                  </el-button>
                </el-form>
              </template>
            </el-tab-pane>
          </el-tabs>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import PageHeader from '@/components/PageHeader.vue'
import {
  fetchTeacherAppeal,
  fetchTeacherAppeals,
  fetchTeacherClasses,
  submitTeacherReview,
} from '@/api/teacher'
import { formatDateTime } from '@/utils/format'

const appeals = ref([])
const classes = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const detail = ref(null)
const detailLoadingId = ref(null)
const activeTab = ref('appeal')
const submitting = ref(false)
const reviewError = ref('')
const filters = reactive({ class_id: null, status: '', reason_type: '' })

const statusOptions = [
  { value: 'pending', label: '待复核' },
  { value: 'reviewing', label: '复核中' },
  { value: 'accepted', label: '已接受' },
  { value: 'rejected', label: '已驳回' },
  { value: 'resolved', label: '已处理' },
]
const reasonOptions = [
  { value: 'score_low', label: '评分偏低' },
  { value: 'evidence_mismatch', label: '原文证据不准确' },
  { value: 'intent_misunderstood', label: '表达意图理解偏差' },
  { value: 'creative_expression_misjudged', label: '个性表达被误判' },
  { value: 'missed_strength', label: '遗漏重要优点' },
  { value: 'rubric_disagreement', label: '评分标准理解分歧' },
  { value: 'other', label: '其他' },
]
const tagOptions = [
  { value: 'factual_error', label: '事实性错误' },
  { value: 'scoring_bias', label: '评分偏差' },
  { value: 'expression_misjudgment', label: '表达误判' },
  { value: 'evaluation_omission', label: '评价遗漏' },
  { value: 'unreasonable_suggestion', label: '建议不合理' },
  { value: 'other', label: '其他问题' },
]
const dimensions = [
  { value: 'content', label: '内容' },
  { value: 'organization', label: '组织结构' },
  { value: 'language', label: '语言' },
  { value: 'overall', label: '整体' },
  { value: 'topic', label: '审题' },
]

const reviewForm = reactive({
  decision: 'adjust',
  dimension_scores: {},
  feedback_changes: {},
  added_feedback: [],
  classification_codes: [],
  classification_note: '',
  revised_summary: '',
  change_reason: '',
})

function statusType(status) { return { pending: 'info', reviewing: 'warning', accepted: 'success', rejected: 'danger', resolved: 'success' }[status] || 'info' }
function statusLabel(status) { return { pending: '待复核', reviewing: '复核中', accepted: '已接受', rejected: '已驳回', resolved: '已处理' }[status] || status }
function dimensionLabel(value) { return { content: '内容', organization: '组织结构', language: '语言', overall: '整体', topic: '审题' }[value] || value }
function reasonLabel(value) { return reasonOptions.find((item) => item.value === value)?.label || value }

async function loadAppeals() {
  loading.value = true
  try {
    const response = await fetchTeacherAppeals({
      class_id: filters.class_id || undefined,
      status: filters.status || undefined,
      reason_type: filters.reason_type || undefined,
    })
    appeals.value = response.data
  } finally {
    loading.value = false
  }
}

async function loadClasses() {
  const response = await fetchTeacherClasses()
  classes.value = response.data
}

async function openDetail(appealId) {
  drawerVisible.value = true
  detailLoadingId.value = appealId
  activeTab.value = 'appeal'
  reviewError.value = ''
  try {
    const response = await fetchTeacherAppeal(appealId)
    detail.value = response.data
    initializeReviewForm()
  } finally {
    detailLoadingId.value = null
  }
}

function initializeReviewForm() {
  reviewForm.decision = 'adjust'
  reviewForm.dimension_scores = {}
  detail.value.evaluation.dimension_scores.forEach((item) => {
    reviewForm.dimension_scores[item.dimension] = item.final_score ?? item.original_score ?? 3
  })
  reviewForm.feedback_changes = {}
  detail.value.feedback_items.filter((item) => !item.teacher_feedback).forEach((item) => {
    reviewForm.feedback_changes[item.id] = { action: 'kept', content: item.content, suggestion: item.suggestion || '' }
  })
  reviewForm.added_feedback = []
  reviewForm.classification_codes = []
  reviewForm.classification_note = ''
  reviewForm.revised_summary = ''
  reviewForm.change_reason = ''
}

function toggleTag(code) {
  if (reviewForm.classification_codes.includes(code)) {
    reviewForm.classification_codes = reviewForm.classification_codes.filter((item) => item !== code)
  } else {
    reviewForm.classification_codes.push(code)
  }
}

async function submitReview() {
  if (submitting.value) return
  reviewError.value = ''
  if (reviewForm.change_reason.trim().length < 5) {
    reviewError.value = '请填写至少 5 个字的复核原因'
    return
  }
  if (reviewForm.classification_codes.length === 0) {
    reviewError.value = '请至少确认一个争议归因分类'
    return
  }
  const payload = {
    decision: reviewForm.decision,
    change_reason: reviewForm.change_reason,
    classification_codes: reviewForm.classification_codes,
    classification_note: reviewForm.classification_note || null,
    dimension_updates: [],
    feedback_changes: [],
    added_feedback: [],
    revised_summary: null,
  }
  if (reviewForm.decision === 'adjust') {
    payload.dimension_updates = detail.value.evaluation.dimension_scores.map((item) => ({
      dimension: item.dimension,
      final_score: reviewForm.dimension_scores[item.dimension],
    }))
    payload.feedback_changes = Object.entries(reviewForm.feedback_changes)
      .filter(([, value]) => value.action !== 'kept')
      .map(([feedbackItemId, value]) => ({
        feedback_item_id: Number(feedbackItemId),
        action: value.action,
        content: value.action === 'modified' ? value.content : null,
        suggestion: value.action === 'modified' ? value.suggestion : null,
      }))
    payload.added_feedback = reviewForm.added_feedback.filter((item) => item.content.trim())
    payload.revised_summary = reviewForm.revised_summary.trim() || null
  }
  submitting.value = true
  try {
    await submitTeacherReview(detail.value.id, payload)
    ElMessage.success('复核已保存，AI 原始评价保持不变')
    drawerVisible.value = false
    await loadAppeals()
  } catch (error) {
    reviewError.value = error.message || '复核提交失败'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadClasses(), loadAppeals()])
})
</script>

<style scoped>
.filter-card, .list-card { padding: 18px; }
.filter-card { margin-bottom: 18px; }
.muted { color: var(--wm-text-secondary); font-size: 11px; margin-top: 3px; }
.review-summary { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 0 4px 16px; border-bottom: 1px solid var(--wm-border); }
.eyebrow { color: var(--wm-primary); font-size: 10px; letter-spacing: 0.16em; }
.review-summary h2 { margin: 6px 0; font-size: 21px; }
.review-summary p { margin: 0; color: var(--wm-text-secondary); font-size: 12px; }
.review-tabs { margin-top: 12px; }
.two-column { display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 18px; align-items: start; }
.sub-card { padding: 16px; border: 1px solid var(--wm-border); border-radius: 12px; }
.sub-card h3 { margin: 0 0 12px; font-size: 15px; }
.essay-text { max-height: 560px; overflow: auto; padding: 14px; border-radius: 9px; background: #fffdf8; line-height: 2; white-space: pre-wrap; }
.appeal-evidence { margin-top: 12px; color: var(--wm-text-secondary); font-size: 12px; }
.appeal-evidence blockquote { margin: 8px 0; padding: 8px 10px; border-left: 3px solid var(--wm-primary); background: var(--wm-bg-soft); }
.dimension-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
.dimension-strip div { padding: 14px; border-radius: 10px; background: var(--wm-bg-soft); }
.dimension-strip span { display: block; color: var(--wm-text-secondary); font-size: 12px; }
.dimension-strip strong { font-size: 22px; color: var(--wm-primary); }
.dimension-strip small { display: block; color: var(--wm-text-secondary); font-size: 10px; }
.review-alert { margin-bottom: 14px; }
.ai-feedback { padding: 14px; margin-bottom: 10px; border: 1px solid var(--wm-border); border-radius: 10px; }
.ai-feedback__head { display: flex; align-items: center; gap: 8px; color: var(--wm-text-secondary); font-size: 11px; }
.ai-feedback p { margin: 8px 0 0; font-size: 13px; line-height: 1.8; }
.ai-feedback blockquote { margin: 8px 0 0; padding-left: 10px; border-left: 2px solid var(--wm-primary-soft); color: var(--wm-text-secondary); font-size: 12px; }
.history-review { padding: 12px; margin-bottom: 10px; border-radius: 9px; background: var(--wm-bg-soft); font-size: 12px; }
.history-review p { margin: 6px 0; }
.section-title { margin: 20px 0 10px; font-weight: 650; font-size: 14px; }
.score-row { display: flex; gap: 20px; flex-wrap: wrap; }
.change-row { padding: 12px; margin-bottom: 10px; border: 1px solid var(--wm-border); border-radius: 9px; }
.change-row__title { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; font-size: 12px; }
.change-row :deep(.el-textarea) { margin-top: 8px; }
.added-feedback { display: grid; grid-template-columns: 130px 1fr 1fr auto; gap: 8px; align-items: center; margin-bottom: 8px; }
.suggestion-alert { margin-bottom: 12px; }
.suggestion-chip { margin: 3px 6px 3px 0; padding: 3px 9px; border: 1px solid var(--wm-border); border-radius: 999px; background: #fff; color: var(--wm-primary); font-size: 11px; cursor: pointer; }

@media (max-width: 980px) {
  .two-column { grid-template-columns: 1fr; }
  .added-feedback { grid-template-columns: 1fr; }
}
</style>