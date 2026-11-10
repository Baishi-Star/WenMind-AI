<template>
  <div>
    <PageHeader
      title="成长档案"
      subtitle="从多篇真实作文的有效评价中分析内容、表达、发展表现；教师复核结果优先。"
    >
      <template #tag>
        <el-tag
          type="success"
          effect="plain"
        >
          真实评价统计
        </el-tag>
      </template>
      <template #actions>
        <el-button
          :loading="loading"
          @click="loadAll"
        >
          刷新画像
        </el-button>
      </template>
    </PageHeader>
    <el-alert
      v-if="error"
      type="error"
      :closable="false"
      show-icon
      :title="error"
      class="page-error"
    />
    <div v-loading="loading">
      <GrowthOverview
        v-if="profile"
        :profile="profile"
        :points="points"
      />
      <el-empty
        v-else-if="!loading"
        description="尚未获取成长数据"
      />
      <TrainingTaskList
        v-if="profile"
        :tasks="tasks"
        :loading="loading"
        :notice="trainingNotice"
        @completed="loadAll"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import GrowthOverview from '@/components/GrowthOverview.vue'
import PageHeader from '@/components/PageHeader.vue'
import TrainingTaskList from '@/components/TrainingTaskList.vue'
import { fetchGrowthHistory, fetchGrowthProfile, fetchTrainingTasks } from '@/api/growth'

const profile = ref(null)
const points = ref([])
const tasks = ref([])
const trainingNotice = ref('')
const loading = ref(false)
const error = ref('')

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [profileResponse, historyResponse, trainingResponse] = await Promise.all([
      fetchGrowthProfile(),
      fetchGrowthHistory(),
      fetchTrainingTasks(),
    ])
    profile.value = profileResponse.data
    points.value = historyResponse.data.points
    tasks.value = trainingResponse.data.tasks
    trainingNotice.value = trainingResponse.data.notice
  } catch (requestError) {
    error.value = requestError.message || '成长画像加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.page-error { margin-bottom: 16px; }
</style>