<template>
  <section class="wm-card evidence-panel">
    <div class="section-head">
      <h2>原文证据追溯</h2>
      <span>仅将通过后端核验的引用高亮；未核验内容不会伪装成学生原文</span>
    </div>
    <div class="evidence-layout">
      <div class="essay-viewer">
        <div class="essay-viewer__head">
          <strong>作文原文</strong><span>{{ verifiedRecords.length }} 处可定位证据</span>
        </div>
        <el-alert
          v-if="verifiedRecords.length === 0"
          type="warning"
          :closable="false"
          show-icon
          title="当前没有通过原文核验的评价证据"
        />
        <div class="essay-content">
          <template
            v-for="segment in segments"
            :key="`${segment.start}-${segment.end}`"
          >
            <span
              v-if="segment.records.length"
              class="evidence-mark"
              :class="{ 'is-active': segment.records.some((record) => record.key === selectedRecordKey) }"
              :data-records="segment.records.map((record) => record.key).join(' ')"
              @click="selectRecord(segment.records[0])"
            >{{ segment.text }}</span>
            <span v-else>{{ segment.text }}</span>
          </template>
        </div>
        <div
          v-if="selectedRecord"
          class="selected-evidence"
        >
          <el-tag
            type="success"
            size="small"
          >
            原文已核验
          </el-tag>
          <span>位置 {{ selectedRecord.start_char }}–{{ selectedRecord.end_char }} · {{ selectedRecord.match_type }}</span>
          <p>{{ selectedRecord.reason }}</p>
        </div>
      </div>

      <div class="feedback-list">
        <article
          v-for="item in feedbackItems"
          :key="item.id"
          class="feedback-item"
          :class="{ 'is-active': selectedFeedbackId === item.id }"
        >
          <div class="feedback-item__head">
            <div>
              <el-tag
                size="small"
                effect="plain"
              >
                {{ dimensionLabel(item.dimension) }} · {{ categoryLabel(item.category) }}
              </el-tag>
            </div>
            <el-tag
              size="small"
              :type="item.verified_status === 'verified' ? 'success' : 'warning'"
            >
              {{ item.verified_status === 'verified' ? '证据已核验' : '证据待核验' }}
            </el-tag>
          </div>
          <p class="feedback-item__content">
            {{ item.content }}
          </p>
          <p
            v-if="item.suggestion"
            class="feedback-item__suggestion"
          >
            建议：{{ item.suggestion }}
          </p>
          <div
            v-for="(evidence, index) in item.evidence"
            :key="index"
            class="feedback-evidence"
          >
            <div>
              <el-tag
                size="small"
                :type="evidence.verified_status === 'verified' ? 'success' : 'warning'"
                effect="plain"
              >
                {{ evidence.verified_status === 'verified' ? '已核验' : '待核验' }}
              </el-tag>
              <span>{{ evidence.start_char }}–{{ evidence.end_char }}</span>
            </div>
            <blockquote>“{{ evidence.quote }}”</blockquote>
            <p>{{ evidence.reason }}</p>
          </div>
          <div class="feedback-item__actions">
            <el-button
              size="small"
              :disabled="!hasVerifiedEvidence(item)"
              @click="locateFeedback(item)"
            >
              定位原文
            </el-button>
            <el-button
              size="small"
              type="warning"
              plain
              @click="emit('appeal', item)"
            >
              质疑此项
            </el-button>
          </div>
        </article>
        <el-empty
          v-if="feedbackItems.length === 0"
          description="评价完成后将显示优点、问题和修改建议"
        />
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'

const props = defineProps({
  essayContent: { type: String, required: true },
  feedbackItems: { type: Array, default: () => [] },
})
const emit = defineEmits(['appeal'])

const selectedRecordKey = ref('')
const selectedFeedbackId = ref(null)

const allRecords = computed(() => props.feedbackItems.flatMap((item) =>
  (item.evidence || []).map((evidence, evidenceIndex) => ({
    ...evidence,
    feedbackId: item.id,
    evidenceIndex,
    key: `${item.id}-${evidenceIndex}`,
  })),
))
const verifiedRecords = computed(() => allRecords.value.filter((record) =>
  record.verified_status === 'verified'
  && Number.isInteger(record.start_char)
  && Number.isInteger(record.end_char)
  && record.start_char >= 0
  && record.end_char > record.start_char
  && record.end_char <= props.essayContent.length
  && props.essayContent.slice(record.start_char, record.end_char) === record.quote,
))
const selectedRecord = computed(() => allRecords.value.find((record) => record.key === selectedRecordKey.value))

const segments = computed(() => {
  const content = props.essayContent
  const records = verifiedRecords.value
  if (!content) return []
  const points = new Set([0, content.length])
  records.forEach((record) => {
    points.add(record.start_char)
    points.add(record.end_char)
  })
  const sorted = [...points].sort((a, b) => a - b)
  const result = []
  for (let index = 0; index < sorted.length - 1; index += 1) {
    const start = sorted[index]
    const end = sorted[index + 1]
    if (start === end) continue
    result.push({
      start,
      end,
      text: content.slice(start, end),
      records: records.filter((record) => record.start_char <= start && record.end_char >= end),
    })
  }
  return result
})

function hasVerifiedEvidence(item) {
  return verifiedRecords.value.some((record) => record.feedbackId === item.id)
}

async function selectRecord(record) {
  selectedRecordKey.value = record.key
  selectedFeedbackId.value = record.feedbackId
  await nextTick()
  document.querySelector(`[data-records~="${record.key}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function locateFeedback(item) {
  const record = verifiedRecords.value.find((entry) => entry.feedbackId === item.id)
  if (record) selectRecord(record)
}

function dimensionLabel(value) {
  return { content: '内容', organization: '组织结构', language: '语言', overall: '综合', topic: '审题' }[value] || value
}

function categoryLabel(value) {
  return { strength: '主要优点', problem: '主要问题', summary: '综合评价', analysis: '分析' }[value] || value
}
</script>

<style scoped>
.evidence-panel { padding: 20px; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.section-head h2 { margin: 0; font-size: 17px; }
.section-head span { color: var(--wm-text-secondary); font-size: 12px; }
.evidence-layout { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr); gap: 18px; align-items: start; }
.essay-viewer { position: sticky; top: 86px; }
.essay-viewer__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.essay-viewer__head span { color: var(--wm-text-secondary); font-size: 11px; }
.essay-content { max-height: 680px; overflow: auto; padding: 18px; border: 1px solid var(--wm-border); border-radius: 12px; background: #fffdf8; font-size: 14px; line-height: 2.1; white-space: pre-wrap; }
.evidence-mark { padding: 2px 0; border-radius: 3px; background: #fff0a8; border-bottom: 2px solid #eab308; cursor: pointer; transition: background 0.2s ease; }
.evidence-mark:hover { background: #fde68a; }
.evidence-mark.is-active { background: #c7d2fe; border-bottom-color: var(--wm-primary); box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.14); }
.selected-evidence { margin-top: 12px; padding: 12px; border-radius: 10px; background: var(--wm-bg-soft); font-size: 12px; }
.selected-evidence > span { margin-left: 8px; color: var(--wm-text-secondary); }
.selected-evidence p { margin: 8px 0 0; line-height: 1.7; }
.feedback-list { display: grid; gap: 12px; max-height: 760px; overflow: auto; padding-right: 4px; }
.feedback-item { padding: 14px; border: 1px solid var(--wm-border); border-radius: 12px; background: #fff; }
.feedback-item.is-active { border-color: var(--wm-primary); box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08); }
.feedback-item__head { display: flex; justify-content: space-between; gap: 10px; }
.feedback-item__content { margin: 10px 0 0; font-size: 13px; line-height: 1.8; }
.feedback-item__suggestion { margin: 8px 0 0; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.8; }
.feedback-evidence { margin-top: 10px; padding: 10px; border-radius: 8px; background: var(--wm-bg-soft); }
.feedback-evidence > div { display: flex; align-items: center; gap: 8px; color: var(--wm-text-secondary); font-size: 11px; }
.feedback-evidence blockquote { margin: 8px 0; padding-left: 10px; border-left: 3px solid var(--wm-primary-soft); font-size: 12px; line-height: 1.8; }
.feedback-evidence p { margin: 0; color: var(--wm-text-secondary); font-size: 11px; line-height: 1.7; }
.feedback-item__actions { display: flex; gap: 8px; margin-top: 12px; }

@media (max-width: 1100px) {
  .evidence-layout { grid-template-columns: 1fr; }
  .essay-viewer { position: static; }
  .feedback-list { max-height: none; }
}
</style>