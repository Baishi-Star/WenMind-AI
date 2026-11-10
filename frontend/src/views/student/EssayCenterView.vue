<template>
  <div>
    <PageHeader
      title="我的作文"
      subtitle="查看本人草稿、提交记录、内容版本和评价状态；数据全部来自当前学生的后端记录。"
    >
      <template #actions>
        <el-button
          type="primary"
          @click="router.push('/student/essays/new')"
        >
          新建作文
        </el-button>
      </template>
    </PageHeader>
    <section class="wm-card list-card">
      <div class="list-toolbar">
        <el-radio-group
          v-model="statusFilter"
          @change="loadEssays"
        >
          <el-radio-button value="">
            全部
          </el-radio-button>
          <el-radio-button value="draft">
            草稿
          </el-radio-button>
          <el-radio-button value="submitted">
            已提交
          </el-radio-button>
          <el-radio-button value="evaluating">
            评价中
          </el-radio-button>
          <el-radio-button value="completed">
            评价完成
          </el-radio-button>
          <el-radio-button value="failed">
            评价失败
          </el-radio-button>
        </el-radio-group>
        <el-button
          :loading="loading"
          @click="loadEssays"
        >
          刷新
        </el-button>
      </div>
      <el-table
        v-loading="loading"
        :data="essays"
        empty-text="当前筛选条件下没有作文"
      >
        <el-table-column
          prop="id"
          label="ID"
          width="70"
        />
        <el-table-column
          label="作文题目"
          min-width="240"
        >
          <template #default="{ row }">
            <strong>{{ row.prompt_title || '自由作文' }}</strong><el-tag
              v-if="row.is_demo"
              size="small"
              effect="plain"
              class="demo-tag"
            >
              演示
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="content_version"
          label="版本"
          width="75"
        >
          <template #default="{ row }">
            v{{ row.content_version }}
          </template>
        </el-table-column>
        <el-table-column
          prop="char_count"
          label="字数"
          width="90"
        />
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
          label="更新时间"
          width="170"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="230"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              size="small"
              @click="openDetail(row.id)"
            >
              查看原文
            </el-button>
            <el-button
              v-if="row.status === 'draft'"
              text
              type="primary"
              size="small"
              @click="editDraft(row.id)"
            >
              编辑草稿
            </el-button>
            <el-button
              v-else
              text
              type="primary"
              size="small"
              @click="router.push('/student/evaluations')"
            >
              评价任务
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="list-footer">
        共 {{ total }} 篇作文 · 当前展示 {{ essays.length }} 篇
      </div>
    </section>

    <el-drawer
      v-model="detailVisible"
      title="作文原文"
      size="900px"
    >
      <div v-loading="detailLoading">
        <template v-if="essayDetail">
          <h3>{{ essayDetail.prompt_title || '自由作文' }}</h3>
          <div class="detail-meta">
            作文 #{{ essayDetail.id }} · 内容版本 v{{ essayDetail.content_version }} · {{ essayDetail.char_count }} 字
            <el-tag
              size="small"
              :type="essayFiles.length ? 'warning' : 'info'"
              effect="plain"
              class="source-tag"
            >
              {{ essayFiles.length ? '图片提交' : '文字提交' }}
            </el-tag>
          </div>
          <el-tag :type="statusType(essayDetail.status)">
            {{ statusLabel(essayDetail.status) }}
          </el-tag>

          <el-tabs
            v-if="essayFiles.length"
            v-model="detailTab"
            class="detail-tabs"
          >
            <el-tab-pane
              label="原始图片"
              name="image"
            >
              <el-alert
                type="info"
                :closable="false"
                show-icon
                title="以下为学生提交的原始作文图片"
                description="可缩放、旋转、翻页；识别文本仅供参照，疑处请以原图为准。"
                class="detail-notice"
              />
              <EssayImageViewer
                :files="essayFiles"
                :annotations="essayAnnotations"
              />
            </el-tab-pane>
            <el-tab-pane
              label="识别/确认文本"
              name="text"
            >
              <div class="essay-detail-content">
                {{ essayDetail.content || '（该作文暂无已确认文本）' }}
              </div>
            </el-tab-pane>
          </el-tabs>
          <template v-else>
            <div class="essay-detail-content">
              {{ essayDetail.content }}
            </div>
          </template>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import PageHeader from '@/components/PageHeader.vue'
import EssayImageViewer from '@/components/EssayImageViewer.vue'
import { fetchEssay, fetchEssays } from '@/api/essay'
import { fetchEssayAnnotations, fetchEssayFiles } from '@/api/submission'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const essays = ref([])
const total = ref(0)
const statusFilter = ref('')
const loading = ref(false)
const detailVisible = ref(false)
const detailLoading = ref(false)
const essayDetail = ref(null)
const essayFiles = ref([])
const essayAnnotations = ref([])
const detailTab = ref('image')

function statusType(status) { return { completed: 'success', failed: 'danger', evaluating: 'warning', submitted: 'primary', draft: 'info' }[status] || 'info' }
function statusLabel(status) { return { completed: '评价完成', failed: '评价失败', evaluating: '评价中', submitted: '已提交', draft: '草稿' }[status] || status }

async function loadEssays() {
  loading.value = true
  try {
    const response = await fetchEssays({ page: 1, page_size: 50, status: statusFilter.value || undefined })
    essays.value = response.data.items
    total.value = response.data.total
  } finally {
    loading.value = false
  }
}

async function openDetail(essayId) {
  detailVisible.value = true
  detailLoading.value = true
  essayFiles.value = []
  essayAnnotations.value = []
  detailTab.value = 'image'
  try {
    const [detailResponse, filesResponse, annotationResponse] = await Promise.all([
      fetchEssay(essayId),
      fetchEssayFiles(essayId).catch(() => ({ data: [] })),
      fetchEssayAnnotations(essayId).catch(() => ({ data: [] })),
    ])
    essayDetail.value = detailResponse.data
    essayFiles.value = filesResponse.data || []
    essayAnnotations.value = annotationResponse.data || []
    if (!essayFiles.value.length) detailTab.value = 'text'
  } finally {
    detailLoading.value = false
  }
}

function editDraft(essayId) {
  router.push({ path: '/student/essays/new', query: { draft: essayId } })
}

onMounted(loadEssays)
</script>

<style scoped>
.list-card { padding: 20px; }
.list-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 16px; overflow-x: auto; }
.demo-tag { margin-left: 8px; }
.list-footer { margin-top: 14px; color: var(--wm-text-secondary); font-size: 12px; text-align: right; }
.detail-meta { margin: 8px 0 12px; color: var(--wm-text-secondary); font-size: 12px; }
.detail-meta .source-tag { margin-left: 8px; }
.detail-tabs { margin-top: 14px; }
.detail-notice { margin-bottom: 12px; }
.essay-detail-content { margin-top: 18px; padding: 18px; border-radius: 12px; background: #fffdf8; line-height: 2; white-space: pre-wrap; }
</style>