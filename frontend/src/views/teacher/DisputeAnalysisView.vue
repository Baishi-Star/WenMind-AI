<template>
  <div>
    <PageHeader
      title="争议分析"
      subtitle="仅统计教师确认的复核记录；申诉提交量不等同于模型错误率。"
    >
      <template #actions>
        <el-button
          type="primary"
          :loading="generating"
          @click="generateProposals"
        >
          生成待审核规则建议
        </el-button>
      </template>
    </PageHeader>
    <section class="wm-card filter-card">
      <el-form inline>
        <el-form-item label="时间范围">
          <el-select
            v-model="filters.days"
            style="width: 140px"
            @change="loadStats"
          >
            <el-option
              :value="7"
              label="近 7 天"
            />
            <el-option
              :value="30"
              label="近 30 天"
            />
            <el-option
              :value="90"
              label="近 90 天"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select
            v-model="filters.class_id"
            clearable
            placeholder="全部授权班级"
            style="width: 190px"
            @change="loadStats"
          >
            <el-option
              v-for="item in classes"
              :key="item.id"
              :value="item.id"
              :label="item.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="争议类型">
          <el-select
            v-model="filters.tag_code"
            clearable
            placeholder="全部标签"
            style="width: 190px"
            @change="loadStats"
          >
            <el-option
              v-for="item in tagOptions"
              :key="item.value"
              :value="item.value"
              :label="item.label"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </section>

    <el-alert
      v-if="stats?.small_sample_warning"
      type="warning"
      :closable="false"
      show-icon
      title="样本量较少，仅供问题排查参考"
      description="当前筛选范围少于 3 条申诉，不能据此推断模型错误率或总体趋势。"
      class="notice"
    />

    <section class="stats-grid">
      <div class="wm-card stat-card">
        <span>申诉样本</span><strong>{{ stats?.sample_count ?? '—' }}</strong><small>{{ filters.days }} 天内</small>
      </div>
      <div class="wm-card stat-card">
        <span>已复核</span><strong>{{ stats?.reviewed_count ?? '—' }}</strong><small>有复核记录</small>
      </div>
      <div class="wm-card stat-card">
        <span>确认标签</span><strong>{{ stats?.tag_counts?.length ?? '—' }}</strong><small>教师确认的类别</small>
      </div>
      <div class="wm-card stat-card">
        <span>涉及 Agent</span><strong>{{ stats?.agent_counts?.length ?? '—' }}</strong><small>按争议维度映射</small>
      </div>
    </section>

    <div class="analysis-grid">
      <section class="wm-card panel">
        <div class="panel__head">
          <h2>争议类型分布</h2><span>仅教师确认标签</span>
        </div>
        <el-empty
          v-if="!stats?.tag_counts?.length"
          description="暂无已确认争议标签"
          :image-size="70"
        />
        <div
          v-for="item in stats?.tag_counts || []"
          :key="item.tag_code"
          class="bar-row"
        >
          <div class="bar-row__label">
            <span>{{ item.label }}</span><strong>{{ item.count }}</strong>
          </div>
          <div class="bar-track">
            <div
              class="bar-fill"
              :style="{ width: `${item.percentage}%` }"
            />
          </div>
          <small>{{ item.percentage }}%</small>
        </div>
      </section>

      <section class="wm-card panel">
        <div class="panel__head">
          <h2>争议维度与 Agent 追溯</h2><span>维度映射，不代表因果</span>
        </div>
        <el-empty
          v-if="!stats?.agent_counts?.length"
          description="暂无已确认 Agent 关联"
          :image-size="70"
        />
        <div
          v-for="item in stats?.agent_counts || []"
          :key="item.agent_name"
          class="bar-row"
        >
          <div class="bar-row__label">
            <span>{{ item.agent_name }}</span><strong>{{ item.count }}</strong>
          </div>
          <div class="bar-track">
            <div
              class="bar-fill is-teal"
              :style="{ width: `${agentPercent(item.count)}%` }"
            />
          </div>
        </div>
        <div class="reason-list">
          <span
            v-for="(count, reason) in stats?.reason_counts || {}"
            :key="reason"
          >{{ reasonLabel(reason) }}：{{ count }}</span>
        </div>
      </section>

      <section class="wm-card panel">
        <div class="panel__head">
          <h2>量规版本争议</h2><span>评价绑定的版本</span>
        </div>
        <el-empty
          v-if="!stats?.rubric_version_counts?.length"
          description="暂无已确认争议关联版本"
          :image-size="70"
        />
        <el-table
          v-if="stats?.rubric_version_counts?.length"
          :data="stats.rubric_version_counts"
          size="small"
        >
          <el-table-column
            label="规则版本"
            prop="rubric_version_id"
          >
            <template #default="{ row }">
              量规 #{{ row.rubric_version_id }}
            </template>
          </el-table-column>
          <el-table-column
            prop="count"
            label="确认争议数"
          />
        </el-table>
        <p class="panel-note">
          不同版本争议数量受样本分布影响，不能直接解释为规则变好或变差。
        </p>
      </section>

      <section class="wm-card panel">
        <div class="panel__head">
          <h2>申诉状态构成</h2><span>全部样本</span>
        </div>
        <el-empty
          v-if="!Object.keys(stats?.status_counts || {}).length"
          description="暂无申诉数据"
          :image-size="70"
        />
        <el-descriptions
          v-else
          :column="1"
          border
          size="small"
        >
          <el-descriptions-item
            v-for="(count, status) in stats.status_counts"
            :key="status"
            :label="statusLabel(status)"
          >
            {{ count }}
          </el-descriptions-item>
        </el-descriptions>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import PageHeader from '@/components/PageHeader.vue'
import { fetchAppealPatterns, fetchTeacherClasses, generateRuleProposals } from '@/api/teacher'

const stats = ref(null)
const classes = ref([])
const generating = ref(false)
const filters = reactive({ days: 30, class_id: null, tag_code: '' })
const tagOptions = [
  { value: 'factual_error', label: '事实性错误' },
  { value: 'scoring_bias', label: '评分偏差' },
  { value: 'expression_misjudgment', label: '表达误判' },
  { value: 'evaluation_omission', label: '评价遗漏' },
  { value: 'unreasonable_suggestion', label: '建议不合理' },
  { value: 'other', label: '其他问题' },
]

function statusLabel(status) { return { pending: '待复核', reviewing: '复核中', accepted: '已接受', rejected: '已驳回', resolved: '已处理' }[status] || status }
function reasonLabel(value) { return { score_low: '评分偏低', evidence_mismatch: '证据不准确', intent_misunderstood: '意图理解偏差', creative_expression_misjudged: '个性表达误判', missed_strength: '遗漏优点', rubric_disagreement: '标准分歧', other: '其他' }[value] || value }
function agentPercent(count) {
  const maximum = Math.max(...(stats.value?.agent_counts || []).map((item) => item.count), 1)
  return Math.round((count / maximum) * 100)
}

async function loadStats() {
  const response = await fetchAppealPatterns({
    days: filters.days,
    class_id: filters.class_id || undefined,
    tag_code: filters.tag_code || undefined,
  })
  stats.value = response.data
}

async function loadClasses() {
  const response = await fetchTeacherClasses()
  classes.value = response.data
}

async function generateProposals() {
  generating.value = true
  try {
    const response = await generateRuleProposals(filters.days)
    if (response.data.length === 0) {
      ElMessage.info('当前没有达到阈值的新争议类型；或已有待处理建议')
    } else {
      ElMessage.success(`已生成 ${response.data.length} 条待审核建议：${response.data.map((id) => `#${id}`).join('、')}`)
    }
  } finally {
    generating.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadClasses(), loadStats()])
})
</script>

<style scoped>
.filter-card { padding: 16px 18px 0; margin-bottom: 16px; }
.notice { margin-bottom: 16px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.stat-card { padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.stat-card span, .stat-card small { color: var(--wm-text-secondary); font-size: 11px; }
.stat-card strong { font-size: 26px; }
.analysis-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.panel { padding: 20px; }
.panel__head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 16px; }
.panel__head h2 { margin: 0; font-size: 16px; }
.panel__head span { color: var(--wm-text-secondary); font-size: 11px; }
.bar-row { margin-bottom: 13px; }
.bar-row__label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 5px; }
.bar-track { height: 7px; border-radius: 999px; background: var(--wm-bg-soft); overflow: hidden; }
.bar-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, #6366f1, #a5b4fc); }
.bar-fill.is-teal { background: linear-gradient(90deg, #0d9488, #5eead4); }
.bar-row small { color: var(--wm-text-secondary); font-size: 10px; }
.reason-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; color: var(--wm-text-secondary); font-size: 11px; }
.reason-list span { padding: 3px 8px; border-radius: 999px; background: var(--wm-bg-soft); }
.panel-note { margin: 12px 0 0; color: var(--wm-text-secondary); font-size: 11px; line-height: 1.8; }

@media (max-width: 1100px) {
  .stats-grid, .analysis-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 720px) {
  .stats-grid, .analysis-grid { grid-template-columns: 1fr; }
}
</style>