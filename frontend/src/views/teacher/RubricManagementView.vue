<template>
  <div>
    <PageHeader
      title="规则版本管理"
      subtitle="规则建议只作为问题排查线索。教师审批后生成 testing 版本，回归测试通过才能正式启用。"
    >
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadAll"
        >
          刷新
        </el-button>
        <el-button
          type="primary"
          :loading="generating"
          @click="generateProposal"
        >
          生成规则建议
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      title="正式规则必须人工审批"
      description="系统不会自动修改量规或 Prompt，不会自动发布规则；历史评价继续绑定其原量规版本。"
      class="notice"
    />

    <el-tabs
      v-model="activeTab"
      class="wm-card tabs-card"
    >
      <el-tab-pane
        :label="`规则建议（${proposals.length}）`"
        name="proposals"
      >
        <el-table
          v-loading="loading"
          :data="proposals"
          empty-text="暂无规则建议，可点击右上角生成"
        >
          <el-table-column
            prop="id"
            label="建议"
            width="75"
          >
            <template #default="{ row }">
              #{{ row.id }}
            </template>
          </el-table-column>
          <el-table-column
            prop="title"
            label="建议标题"
            min-width="250"
          />
          <el-table-column
            label="争议类型"
            width="160"
          >
            <template #default="{ row }">
              {{ tagLabel(row.source_tag) }}
            </template>
          </el-table-column>
          <el-table-column
            label="关联申诉"
            width="100"
          >
            <template #default="{ row }">
              {{ row.related_appeal_ids.length }} 条
            </template>
          </el-table-column>
          <el-table-column
            label="状态"
            width="115"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="proposalStatusType(row.status)"
              >
                {{ proposalStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="生成时间"
            width="165"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="140"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                text
                type="primary"
                size="small"
                @click="openProposal(row)"
              >
                {{ ['proposed', 'reviewing'].includes(row.status) ? '查看 / 审批' : '查看' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane
        :label="`量规版本（${versions.length}）`"
        name="versions"
      >
        <el-table
          v-loading="loading"
          :data="versions"
          empty-text="暂无量规版本"
        >
          <el-table-column
            label="版本"
            width="100"
          >
            <template #default="{ row }">
              {{ row.version }}
            </template>
          </el-table-column>
          <el-table-column
            prop="name"
            label="量规名称"
            min-width="230"
          />
          <el-table-column
            label="状态"
            width="110"
          >
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="versionStatusType(row.status)"
              >
                {{ versionStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column
            label="审批"
            width="180"
          >
            <template #default="{ row }">
              <span v-if="row.approver_id">审批人 #{{ row.approver_id }}<br><small>{{ formatDateTime(row.approved_at) }}</small></span>
              <span
                v-else
                class="muted"
              >—</span>
            </template>
          </el-table-column>
          <el-table-column
            label="生效时间"
            width="165"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.effective_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="回归测试"
            min-width="170"
          >
            <template #default="{ row }">
              <el-tag
                v-if="row.regression_result?.status"
                size="small"
                :type="row.regression_result.status === 'passed' ? 'success' : 'danger'"
              >
                {{ row.regression_result.status }}
              </el-tag>
              <span
                v-else
                class="muted"
              >未执行</span>
              <div
                v-if="row.regression_result?.mode"
                class="muted"
              >
                {{ row.regression_result.mode }}
              </div>
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="190"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                v-if="['testing', 'draft'].includes(row.status)"
                text
                type="primary"
                size="small"
                :loading="testingId === row.id"
                @click="runRegression(row)"
              >
                回归测试
              </el-button>
              <el-button
                v-if="row.status === 'testing'"
                text
                type="success"
                size="small"
                :disabled="row.regression_result?.status !== 'passed'"
                :loading="publishingId === row.id"
                @click="publishVersion(row)"
              >
                发布
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="proposalVisible"
      title="规则建议与教师审批"
      width="780px"
      :close-on-click-modal="false"
    >
      <template v-if="selectedProposal">
        <el-descriptions
          :column="2"
          border
        >
          <el-descriptions-item label="建议编号">
            #{{ selectedProposal.id }}
          </el-descriptions-item>
          <el-descriptions-item label="争议类型">
            {{ tagLabel(selectedProposal.source_tag) }}
          </el-descriptions-item>
          <el-descriptions-item label="关联维度">
            {{ dimensionLabel(selectedProposal.dimension) }}
          </el-descriptions-item>
          <el-descriptions-item label="关联 Agent">
            {{ selectedProposal.agent_name || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            {{ proposalStatusLabel(selectedProposal.status) }}
          </el-descriptions-item>
          <el-descriptions-item label="生成时间">
            {{ formatDateTime(selectedProposal.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="关联申诉">
            {{ selectedProposal.related_appeal_ids.map((id) => `#${id}`).join('、') }}
          </el-descriptions-item>
          <el-descriptions-item label="典型争议">
            {{ selectedProposal.typical_cases.length }} 条
          </el-descriptions-item>
        </el-descriptions>
        <section class="detail-section">
          <h3>问题描述</h3><p>{{ selectedProposal.problem_description }}</p>
        </section>
        <section class="detail-section">
          <h3>当前规则（原文快照）</h3><pre>{{ prettyRule(selectedProposal.current_rule) }}</pre>
        </section>
        <el-collapse class="cases-collapse">
          <el-collapse-item :title="`典型案例（${selectedProposal.typical_cases.length}）`">
            <div
              v-for="item in selectedProposal.typical_cases"
              :key="item.appeal_id"
              class="case-row"
            >
              <strong>申诉 #{{ item.appeal_id }}</strong>
              <span>{{ dimensionLabel(item.dimension) }} · {{ item.reason_type }}</span>
              <p>{{ item.description }}</p>
            </div>
          </el-collapse-item>
        </el-collapse>

        <template v-if="['proposed', 'reviewing'].includes(selectedProposal.status)">
          <el-divider>教师审批</el-divider>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="审批通过后生成 testing 新版本"
            description="可修改建议文字和新规则内容；新版本必须完成回归测试后才能发布。"
            class="approve-notice"
          />
          <el-form label-position="top">
            <el-form-item label="建议标题">
              <el-input
                v-model="approveForm.title"
                maxlength="200"
              />
            </el-form-item>
            <el-form-item
              label="建议修改内容 / 新规则澄清（将加入新版本 dimensions_json 的 clarification 字段）"
              required
            >
              <el-input
                v-model="approveForm.rule_content"
                type="textarea"
                :rows="3"
                maxlength="4000"
                show-word-limit
              />
            </el-form-item>
            <el-form-item label="预期改善效果">
              <el-input
                v-model="approveForm.expected_effect"
                type="textarea"
                :rows="2"
                maxlength="2000"
              />
            </el-form-item>
            <el-form-item
              label="变更说明"
              required
            >
              <el-input
                v-model="approveForm.change_reason"
                type="textarea"
                :rows="2"
                maxlength="2000"
                show-word-limit
              />
            </el-form-item>
            <el-form-item
              label="审批意见"
              required
            >
              <el-input
                v-model="approveForm.decision_note"
                type="textarea"
                :rows="2"
                maxlength="2000"
              />
            </el-form-item>
          </el-form>
        </template>
      </template>
      <template #footer>
        <el-button
          v-if="selectedProposal && ['proposed', 'reviewing'].includes(selectedProposal.status)"
          type="danger"
          plain
          :loading="rejecting"
          @click="rejectProposal"
        >
          驳回建议
        </el-button>
        <el-button @click="proposalVisible = false">
          {{ selectedProposal && ['proposed', 'reviewing'].includes(selectedProposal.status) ? '取消' : '关闭' }}
        </el-button>
        <el-button
          v-if="selectedProposal && ['proposed', 'reviewing'].includes(selectedProposal.status)"
          type="primary"
          :loading="approving"
          @click="approveProposal"
        >
          通过并生成新版本
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import PageHeader from '@/components/PageHeader.vue'
import {
  approveRuleProposal,
  fetchRubricVersions,
  fetchRuleProposals,
  generateRuleProposals,
  publishRubricVersion,
  rejectRuleProposal,
  runRubricRegression,
} from '@/api/teacher'
import { formatDateTime } from '@/utils/format'

const activeTab = ref('proposals')
const proposals = ref([])
const versions = ref([])
const loading = ref(false)
const generating = ref(false)
const proposalVisible = ref(false)
const selectedProposal = ref(null)
const approving = ref(false)
const rejecting = ref(false)
const testingId = ref(null)
const publishingId = ref(null)
const approveForm = reactive({
  title: '',
  rule_content: '',
  expected_effect: '',
  change_reason: '',
  decision_note: '',
})

function tagLabel(code) { return { factual_error: '事实性错误', scoring_bias: '评分偏差', expression_misjudgment: '表达误判', evaluation_omission: '评价遗漏', unreasonable_suggestion: '建议不合理', other: '其他' }[code] || code }
function dimensionLabel(value) { return { content: '内容', organization: '组织结构', language: '语言', overall: '整体', topic: '审题' }[value] || value || '—' }
function proposalStatusType(status) { return { proposed: 'warning', reviewing: 'warning', approved: 'primary', testing: 'warning', published: 'success', rejected: 'danger', archived: 'info' }[status] || 'info' }
function proposalStatusLabel(status) { return { proposed: '待审核', reviewing: '审核中', approved: '已通过', testing: '测试中', published: '已发布', rejected: '已驳回', archived: '已归档' }[status] || status }
function versionStatusType(status) { return { published: 'success', testing: 'warning', archived: 'info', draft: 'info' }[status] || 'info' }
function versionStatusLabel(status) { return { published: '已生效', testing: '测试中', archived: '历史版本', draft: '草稿' }[status] || status }

function prettyRule(rule) {
  try {
    return JSON.stringify(JSON.parse(rule), null, 2)
  } catch {
    return rule
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [proposalResponse, versionResponse] = await Promise.all([fetchRuleProposals(), fetchRubricVersions()])
    proposals.value = proposalResponse.data
    versions.value = versionResponse.data
  } finally {
    loading.value = false
  }
}

async function generateProposal() {
  generating.value = true
  try {
    const response = await generateRuleProposals(30)
    if (response.data.length === 0) ElMessage.info('当前没有达到阈值的新争议类型，或已有待处理建议')
    else ElMessage.success(`已生成 ${response.data.length} 条待审核建议`)
    await loadAll()
    activeTab.value = 'proposals'
  } finally {
    generating.value = false
  }
}

function openProposal(proposal) {
  selectedProposal.value = proposal
  approveForm.title = proposal.title
  approveForm.rule_content = proposal.suggestion
  approveForm.expected_effect = proposal.expected_effect
  approveForm.change_reason = `依据教师确认的「${tagLabel(proposal.source_tag)}」重复争议，澄清相关评价要求。`
  approveForm.decision_note = ''
  proposalVisible.value = true
}

async function approveProposal() {
  if (approveForm.rule_content.trim().length < 2 || approveForm.change_reason.trim().length < 5 || approveForm.decision_note.trim().length < 2) {
    ElMessage.warning('请完整填写新规则内容、变更说明和审批意见')
    return
  }
  approving.value = true
  try {
    const response = await approveRuleProposal(selectedProposal.value.id, {
      decision_note: approveForm.decision_note,
      title: approveForm.title,
      suggestion: approveForm.rule_content,
      expected_effect: approveForm.expected_effect,
      rule_content: approveForm.rule_content,
      change_reason: approveForm.change_reason,
    })
    ElMessage.success(`已生成版本 ${response.data.version}（${response.data.status}），请运行回归测试`)
    proposalVisible.value = false
    await loadAll()
    activeTab.value = 'versions'
  } finally {
    approving.value = false
  }
}

async function rejectProposal() {
  let note = ''
  try {
    const result = await ElMessageBox.prompt('请填写驳回原因', '驳回规则建议', {
      inputPlaceholder: '例如：样本不足，暂不修改正式规则',
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputValidator: (value) => value.trim().length >= 2 || '至少填写 2 个字',
    })
    note = result.value
  } catch {
    return
  }
  rejecting.value = true
  try {
    await rejectRuleProposal(selectedProposal.value.id, { decision_note: note })
    ElMessage.success('规则建议已驳回')
    proposalVisible.value = false
    await loadAll()
  } finally {
    rejecting.value = false
  }
}

async function runRegression(version) {
  testingId.value = version.id
  try {
    const response = await runRubricRegression(version.id)
    const result = response.data
    if (result.status === 'passed') ElMessage.success(`回归测试通过：${result.message}`)
    else ElMessage.error(`回归测试失败，检查项：${result.checks.filter((item) => !item.passed).map((item) => item.name).join('、')}`)
    await loadAll()
  } finally {
    testingId.value = null
  }
}

async function publishVersion(version) {
  if (version.regression_result?.status !== 'passed') {
    ElMessage.warning('必须先通过回归测试')
    return
  }
  try {
    await ElMessageBox.confirm(
      `发布 ${version.version} 后将归档当前已发布版本，历史评价仍保留原量规版本。是否继续？`,
      '正式发布规则版本',
      { type: 'warning', confirmButtonText: '确认发布', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  publishingId.value = version.id
  try {
    await publishRubricVersion(version.id)
    ElMessage.success(`${version.version} 已正式启用`)
    await loadAll()
  } finally {
    publishingId.value = null
  }
}

onMounted(loadAll)
</script>

<style scoped>
.notice { margin-bottom: 16px; }
.tabs-card { padding: 18px; }
.detail-section { margin-top: 16px; }
.detail-section h3 { margin: 0 0 8px; font-size: 14px; }
.detail-section p { margin: 0; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.8; }
.detail-section pre { max-height: 220px; overflow: auto; padding: 12px; border-radius: 9px; background: var(--wm-bg-soft); font-size: 11px; line-height: 1.7; white-space: pre-wrap; }
.cases-collapse { margin-top: 14px; }
.case-row { padding: 10px 0; border-bottom: 1px solid var(--wm-border); font-size: 12px; }
.case-row span { margin-left: 10px; color: var(--wm-text-secondary); }
.case-row p { margin: 5px 0 0; color: var(--wm-text-secondary); line-height: 1.7; }
.approve-notice { margin-bottom: 14px; }
.muted { color: var(--wm-text-secondary); font-size: 11px; }
</style>