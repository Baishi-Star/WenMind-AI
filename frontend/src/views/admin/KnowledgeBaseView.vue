<template>
  <div>
    <PageHeader
      title="知识库管理"
      subtitle="上传真实评价资料，完成解析、切片、向量化与 FAISS 检索；所有状态均来自后端和 SQLite。"
    >
      <template #tag>
        <el-tag
          type="success"
          effect="plain"
        >
          真实接口 · RAG 已接入
        </el-tag>
      </template>
      <template #actions>
        <el-button
          :loading="documentsLoading"
          @click="loadAll"
        >
          刷新状态
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="status && status.semantic === false"
      type="warning"
      :closable="false"
      show-icon
      class="mode-alert"
      title="当前为 TF-IDF 词汇相似度检索，不是语义 Embedding"
      description="系统未配置外部 Embedding 服务，因此使用真实 TF-IDF 向量与 FAISS 完成可测试的降级检索，不使用随机向量冒充语义能力。"
    />
    <el-alert
      v-else-if="status && status.semantic === true"
      type="success"
      :closable="false"
      show-icon
      class="mode-alert"
      :title="`当前使用远程语义 Embedding：${status.embedding_model}`"
    />

    <div class="stats-grid">
      <section class="wm-card stat-card">
        <span>文档数量</span><strong>{{ documents.length }}</strong>
      </section>
      <section class="wm-card stat-card">
        <span>已索引切片</span><strong>{{ status?.indexed_chunks ?? '—' }}</strong>
      </section>
      <section class="wm-card stat-card">
        <span>检索模式</span><strong class="stat-card__mode">{{ modeLabel }}</strong>
      </section>
      <section class="wm-card stat-card">
        <span>索引持久化</span><strong>{{ status?.index_persisted ? '已落盘' : '未生成' }}</strong>
      </section>
    </div>

    <div class="workspace-grid">
      <section class="wm-card panel">
        <div class="panel__head">
          <h2>上传文档</h2><span>PDF / DOCX / TXT，单文件不超过 10 MB</span>
        </div>
        <el-form label-position="top">
          <el-form-item label="文档标题">
            <el-input
              v-model.trim="uploadForm.title"
              placeholder="留空则使用文件名"
              maxlength="200"
            />
          </el-form-item>
          <el-form-item
            label="资料来源"
            required
          >
            <el-input
              v-model.trim="uploadForm.source"
              placeholder="例如：学校语文教研组授权资料"
              maxlength="255"
            />
          </el-form-item>
          <el-form-item
            label="选择文件"
            required
          >
            <el-upload
              v-model:file-list="uploadFiles"
              class="document-uploader"
              drag
              :auto-upload="false"
              :limit="1"
              accept=".pdf,.docx,.txt"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :on-exceed="handleFileExceed"
            >
              <el-icon class="el-icon--upload">
                <UploadFilled />
              </el-icon>
              <div class="el-upload__text">
                将文件拖到此处，或<em>点击选择</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  相同内容文件不能重复上传；失败文档可修正后重试。
                </div>
              </template>
            </el-upload>
          </el-form-item>
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!selectedFile"
            @click="submitUpload"
          >
            {{ uploading ? '正在解析并建立索引' : '上传并建立索引' }}
          </el-button>
        </el-form>
      </section>

      <section class="wm-card panel">
        <div class="panel__head">
          <h2>检索测试</h2><span>Top-K 结果包含来源、章节与相似度分数</span>
        </div>
        <el-form
          label-position="top"
          @submit.prevent="submitSearch"
        >
          <el-form-item
            label="作文评价相关问题"
            required
          >
            <el-input
              v-model.trim="searchForm.query"
              type="textarea"
              :rows="3"
              maxlength="500"
              show-word-limit
              placeholder="例如：语言维度有哪些常见问题与修改建议？"
            />
          </el-form-item>
          <div class="search-options">
            <el-form-item label="Top-K">
              <el-input-number
                v-model="searchForm.top_k"
                :min="1"
                :max="10"
              />
            </el-form-item>
            <el-form-item label="关联评价任务 ID（可选）">
              <el-input-number
                v-model="searchForm.evaluation_id"
                :min="1"
                :precision="0"
                placeholder="不关联"
              />
            </el-form-item>
          </div>
          <el-button
            type="primary"
            native-type="submit"
            :loading="searching"
            :disabled="searchForm.query.length < 2"
          >
            执行检索
          </el-button>
        </el-form>
        <el-alert
          v-if="searchError"
          type="error"
          :closable="false"
          show-icon
          :title="searchError"
          class="search-error"
        />
      </section>
    </div>

    <section
      v-if="searchResponse"
      class="wm-card panel results-panel"
    >
      <div class="panel__head">
        <h2>命中结果（{{ searchResponse.results.length }}）</h2>
        <span>耗时 {{ searchResponse.took_ms }} ms · {{ searchResponse.search_mode }}</span>
      </div>
      <el-alert
        v-if="searchResponse.evaluation_id"
        type="info"
        :closable="false"
        show-icon
        class="result-alert"
        :title="`本次检索已关联评价任务 #${searchResponse.evaluation_id}，作文 #${searchResponse.essay_id}`"
      />
      <el-empty
        v-if="searchResponse.results.length === 0"
        description="未检索到足够相关的知识片段，不会编造来源"
      />
      <article
        v-for="(item, index) in searchResponse.results"
        :key="item.chunk_id"
        class="result-item"
      >
        <div class="result-item__head">
          <span class="result-item__rank">#{{ index + 1 }}</span>
          <strong>{{ item.document_name }}</strong>
          <el-tag
            size="small"
            effect="plain"
          >
            score {{ item.score }}
          </el-tag>
        </div>
        <div class="result-item__meta">
          document_id={{ item.document_id }} · chunk_id={{ item.chunk_id }} · {{ item.metadata.page_or_section || '章节未标注' }} · {{ item.metadata.source }}
        </div>
        <p class="result-item__content">
          {{ item.content }}
        </p>
      </article>
    </section>

    <section class="wm-card panel documents-panel">
      <div class="panel__head">
        <h2>文档列表</h2><span>解析状态、切片数量与失败原因均可追踪</span>
      </div>
      <el-table
        v-loading="documentsLoading"
        :data="documents"
        empty-text="尚未上传知识库文档"
      >
        <el-table-column
          prop="title"
          label="文档"
          min-width="220"
        >
          <template #default="{ row }">
            <div class="document-title">
              <strong>{{ row.title }}</strong><small>{{ row.original_filename }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="source"
          label="来源"
          min-width="170"
          show-overflow-tooltip
        />
        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="statusType(row.status)"
              size="small"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="chunk_count"
          label="切片"
          width="75"
        />
        <el-table-column
          label="向量模式"
          width="150"
        >
          <template #default="{ row }">
            {{ row.embedding_mode || '—' }}
          </template>
        </el-table-column>
        <el-table-column
          label="大小"
          width="90"
        >
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column
          label="上传时间"
          width="165"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="90"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              type="danger"
              text
              size="small"
              :loading="deletingId === row.id"
              @click="confirmDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="尚未上传知识库文档" />
        </template>
      </el-table>
      <div
        v-for="document in failedDocuments"
        :key="document.id"
        class="document-error"
      >
        <strong>{{ document.title }}：</strong>{{ document.error_message }}
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

import PageHeader from '@/components/PageHeader.vue'
import {
  deleteKnowledgeDocument,
  fetchKnowledgeDocuments,
  fetchKnowledgeStatus,
  searchKnowledge,
  uploadKnowledgeDocument,
} from '@/api/knowledge'
import { formatDateTime } from '@/utils/format'

const documents = ref([])
const status = ref(null)
const documentsLoading = ref(false)
const uploading = ref(false)
const searching = ref(false)
const deletingId = ref(null)
const selectedFile = ref(null)
const uploadFiles = ref([])
const searchResponse = ref(null)
const searchError = ref('')

const uploadForm = reactive({ title: '', source: '项目提供或教研组授权资料' })
const searchForm = reactive({ query: '语言维度有哪些常见问题与修改建议？', top_k: 3, evaluation_id: null })

const failedDocuments = computed(() => documents.value.filter((item) => item.status === 'failed' && item.error_message))
const modeLabel = computed(() => {
  if (!status.value?.embedding_mode) return '未建立'
  return status.value.semantic ? '远程语义' : '本地词汇'
})

function statusType(value) {
  return { ready: 'success', failed: 'danger', processing: 'warning', uploaded: 'info' }[value] || 'info'
}

function statusLabel(value) {
  return { ready: '已就绪', failed: '失败', processing: '解析中', uploaded: '已上传' }[value] || value
}

function formatFileSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function handleFileChange(file) {
  selectedFile.value = file.raw || null
}

function handleFileRemove() {
  selectedFile.value = null
}

function handleFileExceed() {
  ElMessage.warning('一次只能上传一个文件，请先移除已选文件')
}

async function loadDocuments() {
  documentsLoading.value = true
  try {
    const response = await fetchKnowledgeDocuments()
    documents.value = response.data
  } finally {
    documentsLoading.value = false
  }
}

async function loadStatus() {
  try {
    const response = await fetchKnowledgeStatus()
    status.value = response.data
  } catch {
    status.value = null
  }
}

async function loadAll() {
  await Promise.all([loadDocuments(), loadStatus()])
}

async function submitUpload() {
  if (!selectedFile.value || uploading.value) return
  uploading.value = true
  try {
    const response = await uploadKnowledgeDocument({
      file: selectedFile.value,
      title: uploadForm.title,
      source: uploadForm.source,
    })
    ElMessage.success(`索引完成，共 ${response.data.chunk_count} 个切片`)
    uploadForm.title = ''
    uploadFiles.value = []
    selectedFile.value = null
    await loadAll()
  } catch {
    await loadDocuments()
  } finally {
    uploading.value = false
  }
}

async function confirmDelete(document) {
  try {
    await ElMessageBox.confirm(
      `将删除「${document.title}」及其全部切片和向量索引，此操作不可撤销。`,
      '确认删除文档',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  deletingId.value = document.id
  try {
    await deleteKnowledgeDocument(document.id)
    ElMessage.success('文档及索引已删除')
    searchResponse.value = null
    await loadAll()
  } finally {
    deletingId.value = null
  }
}

async function submitSearch() {
  if (searchForm.query.trim().length < 2 || searching.value) return
  searching.value = true
  searchError.value = ''
  try {
    const response = await searchKnowledge({
      query: searchForm.query,
      top_k: searchForm.top_k,
      evaluation_id: searchForm.evaluation_id || null,
    })
    searchResponse.value = response.data
  } catch (error) {
    searchResponse.value = null
    searchError.value = error.message || '检索失败'
  } finally {
    searching.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.mode-alert { margin-bottom: 18px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.stat-card { padding: 16px 18px; display: flex; flex-direction: column; gap: 7px; }
.stat-card span { color: var(--wm-text-secondary); font-size: 12px; }
.stat-card strong { font-size: 23px; }
.stat-card__mode { font-size: 18px !important; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr); gap: 18px; }
.panel { padding: 20px; }
.panel__head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 16px; }
.panel__head h2 { margin: 0; font-size: 16px; }
.panel__head span { color: var(--wm-text-secondary); font-size: 12px; }
.document-uploader { width: 100%; }
.document-uploader :deep(.el-upload), .document-uploader :deep(.el-upload-dragger) { width: 100%; }
.search-options { display: grid; grid-template-columns: 0.7fr 1.3fr; gap: 12px; }
.search-error { margin-top: 14px; }
.results-panel, .documents-panel { margin-top: 18px; }
.result-alert { margin-bottom: 14px; }
.result-item { padding: 15px 0; border-top: 1px solid var(--wm-border); }
.result-item__head { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
.result-item__rank { color: var(--wm-primary); font-weight: 700; }
.result-item__meta { margin-top: 7px; color: var(--wm-text-secondary); font-size: 11px; overflow-wrap: anywhere; }
.result-item__content { margin: 10px 0 0; color: var(--wm-text-main); font-size: 13px; line-height: 1.9; white-space: pre-wrap; }
.document-title { display: flex; flex-direction: column; gap: 4px; }
.document-title small { color: var(--wm-text-secondary); }
.document-error { margin-top: 12px; padding: 10px 12px; border-radius: 8px; background: #fef2f2; color: #b91c1c; font-size: 12px; line-height: 1.7; }

@media (max-width: 1100px) {
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .workspace-grid { grid-template-columns: 1fr; }
}
</style>