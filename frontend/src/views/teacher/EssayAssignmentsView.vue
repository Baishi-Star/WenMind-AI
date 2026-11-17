<template>
  <div>
    <PageHeader
      title="作文任务"
      subtitle="创建并下发作文任务：填写题目/材料与要求，设置字数、截止与下发范围，并绑定已发布量规。"
    >
      <template #tag>
        <el-tag
          type="success"
          effect="plain"
        >
          真实任务闭环
        </el-tag>
      </template>
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadAll"
        >
          刷新
        </el-button>
        <el-button
          type="primary"
          @click="openCreate"
        >
          新建任务
        </el-button>
      </template>
    </PageHeader>

    <section class="wm-card filter-card">
      <el-radio-group
        v-model="statusFilter"
        @change="loadTasks"
      >
        <el-radio-button value="">
          全部
        </el-radio-button>
        <el-radio-button value="draft">
          草稿
        </el-radio-button>
        <el-radio-button value="published">
          已发布
        </el-radio-button>
        <el-radio-button value="closed">
          已关闭
        </el-radio-button>
      </el-radio-group>
    </section>

    <section class="wm-card list-card">
      <el-table
        v-loading="loading"
        :data="tasks"
        empty-text="暂无写作任务，点击右上角新建"
      >
        <el-table-column
          prop="id"
          label="ID"
          width="70"
        />
        <el-table-column
          label="任务标题"
          min-width="220"
        >
          <template #default="{ row }">
            <strong>{{ row.title }}</strong>
            <div class="muted">
              {{ row.prompt_text.slice(0, 40) }}{{ row.prompt_text.length > 40 ? '…' : '' }}
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="下发范围"
          min-width="150"
        >
          <template #default="{ row }">
            <template v-if="row.targets.length">
              <el-tag
                v-for="target in row.targets"
                :key="target.id"
                size="small"
                effect="plain"
                class="target-tag"
              >
                {{ target.target_type === 'class' ? '班级' : '学生' }}：{{ target.target_name }}
              </el-tag>
            </template>
            <span
              v-else
              class="muted"
            >未指定</span>
          </template>
        </el-table-column>
        <el-table-column

          label="字数"
          width="120"
        >
          <template #default="{ row }">
            {{ wordLabel(row) }}
          </template>
        </el-table-column>
        <el-table-column
          label="截止时间"
          width="165"
        >
          <template #default="{ row }">
            {{ formatDateTime(row.due_at) }}
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="100"
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
              查看
            </el-button>
            <el-button
              v-if="row.status === 'draft'"
              text
              type="primary"
              size="small"
              @click="openEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              v-if="row.status === 'draft'"
              text
              type="success"
              size="small"
              :loading="actingId === row.id"
              @click="publish(row)"
            >
              发布
            </el-button>
            <el-button
              v-if="row.status === 'published'"
              text
              type="warning"
              size="small"
              :loading="actingId === row.id"
              @click="close(row)"
            >
              关闭
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="formVisible"
      :title="editingId ? `编辑任务 #${editingId}` : '新建写作任务'"
      width="820px"
      :close-on-click-modal="false"
    >
      <el-form
        label-position="top"
        class="task-form"
      >
        <el-form-item label="任务标题">
          <el-input
            v-model.trim="form.title"
            maxlength="200"
            placeholder="可留空，默认取作文题目摘要"
          />
        </el-form-item>
        <el-form-item
          label="作文题目 / 材料"
          required
        >
          <el-input
            v-model="form.prompt_text"
            type="textarea"
            :rows="4"
            maxlength="4000"
            show-word-limit
            placeholder="粘贴作文题目或材料原文"
          />
        </el-form-item>
        <el-form-item label="写作要求">
          <el-input
            v-model="form.requirements"
            type="textarea"
            :rows="3"
            maxlength="4000"
            show-word-limit
            placeholder="文体、角度、字数等要求"
          />
        </el-form-item>

        <div class="form-row">
          <el-form-item
            label="评分量规版本"
            required
          >
            <el-select
              v-model="form.rubric_version_id"
              placeholder="选择已发布量规"
              style="width: 100%"
            >
              <el-option
                v-for="item in rubrics"
                :key="item.id"
                :value="item.id"
                :label="`${item.version} · ${item.name}`"
              />
            </el-select>
          </el-form-item>
          <el-form-item
            label="下发范围"
            required
          >
            <el-select
              v-model="selectedTargetKeys"
              multiple
              placeholder="选择班级或学生"
              style="width: 100%"
            >
              <el-option
                v-for="item in targetOptions"
                :key="item.key"
                :value="item.key"
                :label="item.label"
              />
            </el-select>
          </el-form-item>
        </div>

        <div class="form-row">
          <el-form-item label="字数下限">
            <el-input-number
              v-model="form.word_min"
              :min="0"
              :max="20000"
            />
          </el-form-item>
          <el-form-item label="字数上限（0 表示不限）">
            <el-input-number
              v-model="form.word_max"
              :min="0"
              :max="20000"
            />
          </el-form-item>
          <el-form-item label="截止时间">
            <el-date-picker
              v-model="form.due_at"
              type="datetime"
              placeholder="选择截止时间"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="允许多次提交">
            <el-switch v-model="form.allow_resubmit" />
          </el-form-item>
        </div>
      </el-form>
      <el-alert
        v-if="formError"
        type="error"
        :closable="false"
        show-icon
        :title="formError"
        class="form-error"
      />
      <template #footer>
        <el-button @click="formVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="submitForm"
        >
          {{ editingId ? '保存修改' : '创建草稿' }}
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="detailVisible"
      size="620px"
      :title="detail ? `任务 #${detail.id}` : '任务详情'"
    >
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-descriptions
            :column="1"
            border
          >
            <el-descriptions-item label="标题">
              {{ detail.title }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              {{ statusLabel(detail.status) }}
            </el-descriptions-item>
            <el-descriptions-item label="作文题目">
              {{ detail.prompt_text }}
            </el-descriptions-item>
            <el-descriptions-item label="写作要求">
              {{ detail.requirements || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="评分量规">
              #{{ detail.rubric_version_id ?? '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="字数">
              {{ wordLabel(detail) }}
            </el-descriptions-item>
            <el-descriptions-item label="截止时间">
              {{ formatDateTime(detail.due_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="下发范围">
              {{ detail.targets.map((item) => item.target_name).join('、') || '未指定' }}
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import PageHeader from '@/components/PageHeader.vue'
import { fetchTeacherClasses } from '@/api/teacher'
import { fetchRubricVersions } from '@/api/teacher'
import {
  closeTeacherTask,
  createTeacherTask,
  fetchTeacherTask,
  fetchTeacherTasks,
  publishTeacherTask,
  updateTeacherTask,
} from '@/api/task'
import { formatDateTime } from '@/utils/format'

const tasks = ref([])
const classes = ref([])
const rubrics = ref([])
const statusFilter = ref('')
const loading = ref(false)
const actingId = ref(null)
const formVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formError = ref('')
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const selectedTargetKeys = ref([])

const emptyForm = () => ({
  title: '',
  prompt_text: '',
  requirements: '',
  rubric_version_id: null,
  word_min: 0,
  word_max: 0,
  allow_resubmit: false,
  due_at: null,

})
const form = reactive(emptyForm())

const targetOptions = computed(() => [
  ...classes.value.map((item) => ({ key: `class:${item.id}`, label: `班级 · ${item.name}`, target_type: 'class', target_id: item.id })),
])

function statusType(status) { return { draft: 'info', published: 'success', closed: 'warning', archived: 'info' }[status] || 'info' }
function statusLabel(status) { return { draft: '草稿', published: '已发布', closed: '已关闭', archived: '已归档' }[status] || status }
function wordLabel(row) {
  if (!row.word_min && !row.word_max) return '不限'
  return `${row.word_min || 0} ~ ${row.word_max || '不限'}`
}

async function loadTasks() {
  loading.value = true
  try {
    const response = await fetchTeacherTasks(statusFilter.value ? { status: statusFilter.value } : {})
    tasks.value = response.data
  } finally {
    loading.value = false
  }
}

async function loadAll() {
  const [classResponse, rubricResponse] = await Promise.all([fetchTeacherClasses(), fetchRubricVersions()])
  classes.value = classResponse.data
  rubrics.value = rubricResponse.data.filter((item) => item.status === 'published')
  await loadTasks()
}

function resetForm() {
  Object.assign(form, emptyForm())
  selectedTargetKeys.value = []
  formError.value = ''
}

function openCreate() {
  editingId.value = null
  resetForm()
  if (rubrics.value.length) form.rubric_version_id = rubrics.value[0].id
  formVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  resetForm()
  Object.assign(form, {
    title: row.title,
    prompt_text: row.prompt_text,
    requirements: row.requirements,
    rubric_version_id: row.rubric_version_id,
    word_min: row.word_min,
    word_max: row.word_max,
    allow_resubmit: row.allow_resubmit,
    due_at: row.due_at ? new Date(row.due_at) : null,

  })
  selectedTargetKeys.value = row.targets.map((item) => `${item.target_type}:${item.target_id}`)
  formVisible.value = true
}


async function submitForm() {
  formError.value = ''
  if (form.prompt_text.trim().length < 2) {
    formError.value = '请填写作文题目 / 材料'
    return
  }
  if (!form.rubric_version_id) {
    formError.value = '必须绑定已发布的评分量规版本'
    return
  }
  const targets = selectedTargetKeys.value
    .map((key) => targetOptions.value.find((item) => item.key === key))
    .filter(Boolean)
    .map((item) => ({ target_type: item.target_type, target_id: item.target_id }))
  if (targets.length === 0) {
    formError.value = '请至少选择一个班级或学生作为下发范围'
    return
  }

  const payload = {
    title: form.title.trim(),
    prompt_text: form.prompt_text.trim(),
    requirements: form.requirements.trim(),
    rubric_version_id: form.rubric_version_id,
    word_min: form.word_min || 0,
    word_max: form.word_max || 0,
    allow_resubmit: form.allow_resubmit,
    due_at: form.due_at ? form.due_at.toISOString() : null,
    targets,

  }
  submitting.value = true
  try {
    if (editingId.value) await updateTeacherTask(editingId.value, payload)
    else await createTeacherTask(payload)
    ElMessage.success(editingId.value ? '任务已更新' : '任务草稿已创建')
    formVisible.value = false
    await loadTasks()
  } catch (error) {
    formError.value = error.message || '保存失败'
  } finally {
    submitting.value = false
  }
}

async function publish(row) {
  try {
    await ElMessageBox.confirm(`发布后学生即可看到任务「${row.title}」，是否继续？`, '发布任务', { type: 'warning' })
  } catch {
    return
  }
  actingId.value = row.id
  try {
    await publishTeacherTask(row.id)
    ElMessage.success('任务已发布')
    await loadTasks()
  } finally {
    actingId.value = null
  }
}

async function close(row) {
  try {
    await ElMessageBox.confirm('关闭后学生不能再提交该任务，是否继续？', '关闭任务', { type: 'warning' })
  } catch {
    return
  }
  actingId.value = row.id
  try {
    await closeTeacherTask(row.id)
    ElMessage.success('任务已关闭')
    await loadTasks()
  } finally {
    actingId.value = null
  }
}

async function openDetail(taskId) {
  detailVisible.value = true
  detailLoading.value = true
  try {
    const response = await fetchTeacherTask(taskId)
    detail.value = response.data
  } finally {
    detailLoading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.filter-card { padding: 14px 18px; margin-bottom: 16px; }
.list-card { padding: 18px; }
.muted { color: var(--wm-text-secondary); font-size: 11px; margin-top: 4px; }
.target-tag { margin: 2px 4px 2px 0; }
.form-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.section-title { margin: 8px 0 12px; font-weight: 650; font-size: 14px; }
.question-row { display: grid; grid-template-columns: 130px minmax(0, 1fr) auto; gap: 10px; align-items: start; margin-bottom: 10px; }
.form-error { margin-top: 12px; }
.question-view { padding: 12px; margin-bottom: 10px; border: 1px solid var(--wm-border); border-radius: 9px; }
.question-view p { margin: 6px 0 0; color: var(--wm-text-secondary); font-size: 12px; line-height: 1.7; }

@media (max-width: 900px) {
  .form-row { grid-template-columns: 1fr; }
  .question-row { grid-template-columns: 1fr; }
}
</style>