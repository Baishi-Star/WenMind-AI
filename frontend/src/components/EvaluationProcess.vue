<template>
  <div class="evaluation-process">
    <el-alert
      v-if="executionMode === 'mock'"
      type="warning"
      :closable="false"
      show-icon
      title="Mock 流程演示：本次未调用真实大模型"
      description="Agent 输出由可解释的文本规则生成，仅验证 Orchestrator、结构化校验、证据核验和数据库流程，不能冒充真实语义评价。"
    />
    <el-alert
      v-else-if="executionMode === 'remote'"
      type="success"
      :closable="false"
      show-icon
      title="本次为真实模型调用"
      description="每个 Agent 的运行记录包含真实模型名称、耗时和 Token 用量；输出仍经后端 Schema 与原文证据校验。"
    />

    <section class="wm-card task-card">
      <div class="task-card__head">
        <div>
          <span class="task-card__eyebrow">当前评价任务</span>
          <h2>#{{ evaluation.id }} · 作文 #{{ evaluation.essay_id }}</h2>
        </div>
        <el-tag
          :type="statusType(evaluation.status)"
          effect="dark"
        >
          {{ statusLabel(evaluation.status) }}
        </el-tag>
      </div>
      <div class="task-meta">
        <span>作文版本 v{{ evaluation.essay_version }}</span>
        <span>量规版本 #{{ evaluation.rubric_version_id ?? '—' }}</span>
        <span>Prompt {{ evaluation.prompt_version }}</span>
        <span>开始 {{ formatDateTime(evaluation.report?.started_at) }}</span>
        <span>完成 {{ formatDateTime(evaluation.report?.completed_at) }}</span>
      </div>
      <el-alert
        v-if="evaluation.error_message"
        type="error"
        :closable="false"
        show-icon
        :title="evaluation.error_message"
        class="task-error"
      />
      <p class="diagnostic-notice">
        {{ evaluation.diagnostic_notice }} 当前仅使用 1–5 诊断等级，不计算加权总分。
      </p>
    </section>

    <section class="wm-card process-section">
      <div class="section-head">
        <h2>Agent 执行顺序与独立分析</h2><span>{{ evaluation.agent_runs.length }} 条真实运行记录</span>
      </div>
      <el-empty
        v-if="evaluation.agent_runs.length === 0"
        description="Agent 尚未执行，任务启动后此处会逐条更新"
      />
      <div
        v-else
        class="agent-list"
      >
        <article
          v-for="(run, index) in evaluation.agent_runs"
          :key="run.id"
          class="agent-item"
        >
          <div class="agent-item__rail">
            <span
              class="agent-item__number"
              :class="`is-${run.status}`"
            >{{ index + 1 }}</span>
            <span
              v-if="index < evaluation.agent_runs.length - 1"
              class="agent-item__line"
            />
          </div>
          <div class="agent-item__body">
            <div class="agent-item__head">
              <div><strong>{{ agentLabel(run.agent_name) }}</strong><small>{{ run.input_summary.task }}</small></div>
              <el-tag
                size="small"
                :type="statusType(run.status)"
              >
                {{ statusLabel(run.status) }}
              </el-tag>
            </div>
            <div class="agent-item__meta">
              <span class="wm-mono">{{ run.agent_name }}</span> · {{ run.model_name }} · {{ run.latency_ms }} ms
              <span v-if="run.token_usage"> · prompt {{ run.token_usage.prompt_tokens ?? '—' }} / completion {{ run.token_usage.completion_tokens ?? '—' }} tokens</span>
              <span v-else-if="executionMode === 'mock'"> · 无 Token 用量（未调用模型）</span>
            </div>
            <el-alert
              v-if="run.error_message"
              type="error"
              :closable="false"
              :title="run.error_message"
            />
            <template v-if="run.output && run.output.analysis">
              <p class="agent-analysis">
                {{ run.output.analysis }}
              </p>
              <div
                v-if="run.output.diagnostic_score"
                class="diagnostic-score"
              >
                诊断等级 <strong>{{ run.output.diagnostic_score }}/5</strong><span>非正式分数</span>
              </div>
              <div
                v-if="run.output.evidence?.length"
                class="evidence-list"
              >
                <div
                  v-for="(evidence, evidenceIndex) in run.output.evidence"
                  :key="evidenceIndex"
                  class="evidence-item"
                >
                  <div class="evidence-item__status">
                    <el-tag
                      size="small"
                      :type="evidence.verified_status === 'verified' ? 'success' : 'warning'"
                      effect="plain"
                    >
                      {{ evidence.verified_status === 'verified' ? '原文已核验' : '待核验' }}
                    </el-tag>
                    <span>{{ evidence.match_type }} · {{ evidence.start_char }}–{{ evidence.end_char }}</span>
                  </div>
                  <blockquote>“{{ evidence.quote }}”</blockquote>
                  <p>{{ evidence.reason }}</p>
                  <small>建议：{{ evidence.suggestion }}</small>
                </div>
              </div>
              <ul
                v-if="run.output.suggestions?.length"
                class="suggestion-list"
              >
                <li
                  v-for="suggestion in run.output.suggestions"
                  :key="suggestion"
                >
                  {{ suggestion }}
                </li>
              </ul>
            </template>
          </div>
        </article>
      </div>
    </section>

    <section class="wm-card process-section">
      <div class="section-head">
        <h2>知识库检索依据</h2><span>{{ evaluation.retrievals.length }} 次检索</span>
      </div>
      <el-empty
        v-if="evaluation.retrievals.length === 0"
        description="任务启动后将记录真实 RAG 检索"
      />
      <div
        v-for="retrieval in evaluation.retrievals"
        :key="retrieval.id"
        class="retrieval-log"
      >
        <div class="retrieval-log__query">
          <strong>查询：</strong>{{ retrieval.query }}
        </div>
        <el-alert
          v-if="!retrieval.semantic"
          type="info"
          :closable="false"
          show-icon
          title="本次使用 TF-IDF 词汇相似度检索，非语义 Embedding；相似度不是准确率。"
        />
        <div
          v-if="retrieval.results.length === 0"
          class="retrieval-empty"
        >
          本次未检索到足够相关的知识片段，未编造来源。
        </div>
        <article
          v-for="item in retrieval.results"
          :key="item.chunk_id"
          class="knowledge-item"
        >
          <div>
            <strong>{{ item.document_name }}</strong><el-tag
              size="small"
              effect="plain"
            >
              score {{ item.score }}
            </el-tag>
          </div>
          <small>document #{{ item.document_id }} · chunk #{{ item.chunk_id }} · {{ item.metadata.page_or_section }}</small>
          <p>{{ item.content }}</p>
        </article>
      </div>
    </section>

    <section
      v-if="evaluation.report?.overall_summary || evaluation.dimension_scores.length"
      class="wm-card process-section final-report"
    >
      <div class="section-head">
        <h2>综合评价与质量审核</h2><el-tag :type="qualityType">
          {{ qualityLabel }}
        </el-tag>
      </div>
      <div class="dimension-grid">
        <div
          v-for="item in evaluation.dimension_scores"
          :key="item.dimension"
          class="dimension-card"
        >
          <span>{{ dimensionLabel(item.dimension) }}</span>
          <strong>{{ item.original_score ?? '—' }}<small>/ {{ item.max_score }}</small></strong>
          <p>AI 原始诊断值 · 教师最终值 {{ item.final_score ?? '未复核' }}</p>
        </div>
      </div>
      <p class="overall-summary">
        {{ evaluation.report.overall_summary }}
      </p>
      <div
        v-if="evaluation.report.quality_issues.length"
        class="quality-issues"
      >
        <h3>质量审核问题</h3>
        <ul>
          <li
            v-for="issue in evaluation.report.quality_issues"
            :key="issue"
          >
            {{ issue }}
          </li>
        </ul>
      </div>
      <div
        v-if="evaluation.report.training_suggestions.length"
        class="training-suggestions"
      >
        <h3>个性化训练方向</h3>
        <ul>
          <li
            v-for="item in evaluation.report.training_suggestions"
            :key="item"
          >
            {{ item }}
          </li>
        </ul>
      </div>
      <p class="final-note">
        AI 原始诊断与教师最终复核分字段保存；当前无教师复核时 final_score 为空，不覆盖 AI 原始记录。
      </p>
    </section>

    <EvidencePanel
      v-if="evaluation.status === 'completed' && essayContent"
      :essay-content="essayContent"
      :feedback-items="evaluation.feedback_items"
      @appeal="forwardAppeal"
    />
    <EvaluationChat
      v-if="evaluation.status === 'completed'"
      :evaluation-id="evaluation.id"
      :feedback-items="evaluation.feedback_items"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

import EvidencePanel from '@/components/EvidencePanel.vue'
import EvaluationChat from '@/components/EvaluationChat.vue'
import { formatDateTime } from '@/utils/format'

const props = defineProps({
  evaluation: { type: Object, required: true },
  essayContent: { type: String, default: '' },
})
const emit = defineEmits(['appeal'])

function forwardAppeal(item) {
  emit('appeal', item)
}

const agentNames = {
  topic_agent: '审题分析 Agent',
  content_agent: '内容评价 Agent',
  structure_agent: '结构评价 Agent',
  language_agent: '语言评价 Agent',
  feedback_agent: '综合反馈 Agent',
  quality_agent: '评价质量审核 Agent',
}

const executionMode = computed(() => props.evaluation.report?.execution_mode || 'pending')
const qualityType = computed(() => ({ passed: 'success', needs_review: 'warning', failed: 'danger', processing: 'info' }[props.evaluation.report?.quality_status] || 'info'))
const qualityLabel = computed(() => ({ passed: '审核通过', needs_review: '需要人工复核', failed: '审核失败', processing: '审核中' }[props.evaluation.report?.quality_status] || '待审核'))

function agentLabel(name) { return agentNames[name] || name }
function statusType(status) { return { completed: 'success', failed: 'danger', processing: 'warning', pending: 'info' }[status] || 'info' }
function statusLabel(status) { return { completed: '已完成', failed: '失败', processing: '执行中', pending: '待处理' }[status] || status }
function dimensionLabel(dimension) { return { content: '内容', organization: '组织（结构）', language: '语言' }[dimension] || dimension }
</script>

<style scoped>
.evaluation-process { display: grid; gap: 18px; }
.task-card, .process-section { padding: 20px; }
.task-card__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.task-card__eyebrow { color: var(--wm-text-secondary); font-size: 12px; }
.task-card h2 { margin: 6px 0 0; font-size: 21px; }
.task-meta { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 14px; color: var(--wm-text-secondary); font-size: 12px; }
.task-error { margin-top: 14px; }
.diagnostic-notice { margin: 14px 0 0; color: #92600a; font-size: 12px; line-height: 1.8; }
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.section-head h2 { margin: 0; font-size: 17px; }
.section-head span { color: var(--wm-text-secondary); font-size: 12px; }
.agent-list { display: grid; }
.agent-item { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 12px; }
.agent-item__rail { display: flex; flex-direction: column; align-items: center; }
.agent-item__number { width: 26px; height: 26px; display: grid; place-items: center; border-radius: 50%; background: var(--wm-bg-soft); color: var(--wm-primary); font-size: 12px; font-weight: 700; }
.agent-item__number.is-completed { background: #dcfce7; color: #15803d; }
.agent-item__number.is-failed { background: #fee2e2; color: #b91c1c; }
.agent-item__line { flex: 1; width: 1px; background: var(--wm-border); }
.agent-item__body { padding-bottom: 24px; }
.agent-item__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.agent-item__head strong { display: block; font-size: 15px; }
.agent-item__head small { display: block; margin-top: 4px; color: var(--wm-text-secondary); }
.agent-item__meta { margin-top: 8px; color: var(--wm-text-secondary); font-size: 11px; overflow-wrap: anywhere; }
.agent-analysis { margin: 12px 0; padding: 12px 14px; border-radius: 10px; background: var(--wm-bg-soft); font-size: 13px; line-height: 1.85; }
.diagnostic-score { display: flex; align-items: baseline; gap: 8px; margin-bottom: 12px; font-size: 13px; }
.diagnostic-score strong { color: var(--wm-primary); font-size: 21px; }
.diagnostic-score span { color: var(--wm-text-secondary); font-size: 11px; }
.evidence-list { display: grid; gap: 10px; }
.evidence-item { padding: 12px; border: 1px solid var(--wm-border); border-radius: 10px; }
.evidence-item__status { display: flex; align-items: center; gap: 8px; color: var(--wm-text-secondary); font-size: 11px; }
.evidence-item blockquote { margin: 10px 0; padding-left: 12px; border-left: 3px solid var(--wm-primary-soft); line-height: 1.8; }
.evidence-item p { margin: 0 0 6px; color: var(--wm-text-secondary); font-size: 12px; }
.evidence-item small { color: var(--wm-text-secondary); }
.suggestion-list { margin: 10px 0 0; padding-left: 18px; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.8; }
.retrieval-log__query { margin-bottom: 10px; font-size: 13px; }
.retrieval-empty { margin-top: 12px; color: var(--wm-text-secondary); font-size: 13px; }
.knowledge-item { margin-top: 12px; padding: 12px; border: 1px solid var(--wm-border); border-radius: 10px; }
.knowledge-item > div { display: flex; align-items: center; gap: 10px; }
.knowledge-item small { display: block; margin-top: 6px; color: var(--wm-text-secondary); }
.knowledge-item p { margin: 8px 0 0; max-height: 150px; overflow: auto; white-space: pre-wrap; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.8; }
.dimension-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.dimension-card { padding: 14px; border-radius: 12px; background: var(--wm-bg-soft); }
.dimension-card > span { color: var(--wm-text-secondary); font-size: 12px; }
.dimension-card strong { display: block; margin-top: 5px; color: var(--wm-primary); font-size: 26px; }
.dimension-card strong small { font-size: 13px; }
.dimension-card p { margin: 4px 0 0; color: var(--wm-text-secondary); font-size: 11px; }
.overall-summary { margin: 18px 0 0; font-size: 14px; line-height: 1.9; }
.quality-issues, .training-suggestions { margin-top: 16px; padding: 14px; border-radius: 10px; background: #fff8e8; }
.training-suggestions { background: #eef8f6; }
.quality-issues h3, .training-suggestions h3 { margin: 0 0 8px; font-size: 14px; }
.quality-issues ul, .training-suggestions ul { margin: 0; padding-left: 18px; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.8; }
.final-note { margin: 16px 0 0; color: var(--wm-text-secondary); font-size: 11px; }

@media (max-width: 760px) {
  .dimension-grid { grid-template-columns: 1fr; }
}
</style>