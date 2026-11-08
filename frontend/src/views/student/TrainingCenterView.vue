<template>
  <div>
    <PageHeader
      title="个性化训练"
      subtitle="根据近期真实评价中的薄弱维度生成训练任务；完成结果会保存并计入成长档案。"
    >
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadTasks"
        >
          刷新任务
        </el-button>
      </template>
    </PageHeader>
    <div
      v-if="profile"
      class="summary-row"
    >
      <div class="wm-card summary-chip">
        <span>有效评价</span><strong>{{ profile.sample_count }}</strong>
      </div>
      <div class="wm-card summary-chip">
        <span>待完成训练</span><strong>{{ taskData.pending_count }}</strong>
      </div>
      <div class="wm-card summary-chip">
        <span>已完成训练</span><strong>{{ taskData.completed_count }}</strong>
      </div>
      <div class="wm-card summary-chip">
        <span>重点关注</span><strong class="summary-chip__text">{{ profile.weaknesses.join('、') || '暂无明确弱项' }}</strong>
      </div>
    </div>
    <el-alert
      v-if="profile?.insufficient_data"
      type="warning"
      :closable="false"
      show-icon
      :title="profile.notice"
      class="notice"
    />
    <TrainingTaskList
      :tasks="taskData.tasks"
      :loading="loading"
      :notice="taskData.notice"
      @completed="loadTasks"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

import PageHeader from '@/components/PageHeader.vue'
import TrainingTaskList from '@/components/TrainingTaskList.vue'
import { fetchGrowthProfile, fetchTrainingTasks } from '@/api/growth'

const loading = ref(false)
const profile = ref(null)
const taskData = reactive({ tasks: [], pending_count: 0, completed_count: 0, notice: '' })

async function loadTasks() {
  loading.value = true
  try {
    const [profileResponse, taskResponse] = await Promise.all([fetchGrowthProfile(), fetchTrainingTasks()])
    profile.value = profileResponse.data
    Object.assign(taskData, taskResponse.data)
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)
</script>

<style scoped>
.summary-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }
.summary-chip { padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.summary-chip span { color: var(--wm-text-secondary); font-size: 11px; }
.summary-chip strong { font-size: 22px; }
.summary-chip__text { font-size: 15px !important; }
.notice { margin-bottom: 16px; }

@media (max-width: 900px) {
  .summary-row { grid-template-columns: 1fr 1fr; }
}
</style>