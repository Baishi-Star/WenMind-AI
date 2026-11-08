<template>
  <div>
    <PageHeader
      title="我的申诉"
      subtitle="查看申诉原因、关联评价项、原文证据和处理状态；申诉不会自动改分，最终结果由教师复核。"
    >
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadAppeals"
        >
          刷新进度
        </el-button>
      </template>
    </PageHeader>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="状态说明"
      description="pending 待复核、reviewing 复核中、accepted 申诉被接受、rejected 申诉未被接受、resolved 已形成最终处理结果。本阶段先由学生提交并跟踪，教师处理在下一阶段接入。"
      class="status-alert"
    />
    <section class="wm-card appeals-card">
      <el-table
        v-loading="loading"
        :data="appeals"
        empty-text="暂无申诉记录"
      >
        <el-table-column
          prop="id"
          label="申诉编号"
          width="100"
        >
          <template #default="{ row }">
            #{{ row.id }}
          </template>
        </el-table-column>
        <el-table-column
          label="关联评价"
          width="150"
        >
          <template #default="{ row }">
            评价 #{{ row.evaluation_id }}<br><small>作文 #{{ row.essay_id }}</small>
          </template>
        </el-table-column>
        <el-table-column
          label="申诉原因"
          min-width="180"
        >
          <template #default="{ row }">
            {{ reasonLabel(row.reason_type) }}
          </template>
        </el-table-column>
        <el-table-column
          label="争议维度"
          width="110"
        >
          <template #default="{ row }">
            {{ dimensionLabel(row.dimension) }}
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="110"
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
          width="175"
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
              @click="openDetail(row.id)"
            >
              查看进度
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-drawer
      v-model="detailVisible"
      title="申诉详情与处理进度"
      size="600px"
    >
      <div v-loading="detailLoading">
        <template v-if="appealDetail">
          <el-steps
            direction="vertical"
            :active="statusStep(appealDetail.status)"
            class="appeal-steps"
          >
            <el-step
              title="提交申诉"
              :description="formatDateTime(appealDetail.submitted_at)"
              status="finish"
            />
            <el-step
              title="教师复核"
              :description="['pending', 'reviewing'].includes(appealDetail.status) ? '等待教师处理' : '已开始复核'"
            />
            <el-step
              title="形成结论"
              :description="['accepted', 'rejected', 'resolved'].includes(appealDetail.status) ? statusLabel(appealDetail.status) : '尚未形成结论'"
            />
          </el-steps>
          <el-descriptions
            :column="1"
            border
          >
            <el-descriptions-item label="申诉编号">
              #{{ appealDetail.id }}
            </el-descriptions-item>
            <el-descriptions-item label="关联评价">
              评价 #{{ appealDetail.evaluation_id }} · 作文 #{{ appealDetail.essay_id }}
            </el-descriptions-item>
            <el-descriptions-item label="申诉原因">
              {{ reasonLabel(appealDetail.reason_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="争议维度">
              {{ dimensionLabel(appealDetail.dimension) }}
            </el-descriptions-item>
            <el-descriptions-item label="学生说明">
              {{ appealDetail.description }}
            </el-descriptions-item>
          </el-descriptions>
          <div
            v-for="item in appealDetail.items"
            :key="item.id"
            class="appeal-evidence"
          >
            <h3>关联评价项与原文证据</h3>
            <p>评价项 ID：{{ item.feedback_item_id ?? '未指定具体条目' }}</p>
            <div
              v-for="(evidence, index) in item.evidence"
              :key="index"
            >
              <el-tag
                size="small"
                :type="evidence.verified_status === 'verified' ? 'success' : 'warning'"
              >
                {{ evidence.verified_status === 'verified' ? '原文已核验' : '待核验' }}
              </el-tag>
              <blockquote>“{{ evidence.quote }}”</blockquote>
            </div>
            <el-empty
              v-if="item.evidence.length === 0"
              description="本次未附加单独原文证据"
              :image-size="60"
            />
          </div>
          <div class="review-records">
            <h3>教师复核记录</h3>
            <el-empty
              v-if="appealDetail.review_records.length === 0"
              description="教师尚未复核，不会自动改分"
              :image-size="70"
            />
            <div
              v-for="(review, index) in appealDetail.review_records"
              :key="index"
            >
              {{ review.review_comment }}
            </div>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import PageHeader from '@/components/PageHeader.vue'
import { fetchAppeal, fetchAppeals } from '@/api/appeal'
import { formatDateTime } from '@/utils/format'

const appeals = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const appealDetail = ref(null)

function statusType(status) { return { pending: 'info', reviewing: 'warning', accepted: 'success', rejected: 'danger', resolved: 'success' }[status] || 'info' }
function statusLabel(status) { return { pending: '待复核', reviewing: '复核中', accepted: '已接受', rejected: '未接受', resolved: '已处理' }[status] || status }
function statusStep(status) { return { pending: 1, reviewing: 2, accepted: 3, rejected: 3, resolved: 3 }[status] || 1 }
function reasonLabel(reason) { return { score_low: '评分偏低', evidence_mismatch: '原文证据不准确', intent_misunderstood: '表达意图理解偏差', creative_expression_misjudged: '个性表达被误判', missed_strength: '遗漏重要优点', rubric_disagreement: '评分标准理解分歧', other: '其他' }[reason] || reason }
function dimensionLabel(value) { return { content: '内容', organization: '组织结构', language: '语言', overall: '整体评价', topic: '审题' }[value] || value }

async function loadAppeals() {
  loading.value = true
  try {
    const response = await fetchAppeals()
    appeals.value = response.data
  } finally {
    loading.value = false
  }
}

async function openDetail(appealId) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    const response = await fetchAppeal(appealId)
    appealDetail.value = response.data
  } finally {
    detailLoading.value = false
  }
}

onMounted(loadAppeals)
</script>

<style scoped>
.status-alert { margin-bottom: 18px; }
.appeals-card { padding: 20px; }
.appeal-steps { margin-bottom: 22px; }
.appeal-evidence, .review-records { margin-top: 20px; }
.appeal-evidence h3, .review-records h3 { margin: 0 0 12px; font-size: 15px; }
.appeal-evidence p { color: var(--wm-text-secondary); font-size: 12px; }
.appeal-evidence blockquote { margin: 10px 0; padding: 12px; border-left: 3px solid var(--wm-primary); background: var(--wm-bg-soft); line-height: 1.8; }
</style>