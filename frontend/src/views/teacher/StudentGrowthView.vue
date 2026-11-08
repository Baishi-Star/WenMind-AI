<template>
  <div>
    <PageHeader
      :title="`${profile?.student_name || '学生'} · 成长详情`"
      subtitle="教师查看授权学生的真实成长记录；教师复核结果优先，AI 未复核评价会明确标记。"
    >
      <template #actions>
        <el-button @click="router.push('/teacher/analytics')">
          返回班级分析
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
        description="该学生暂无成长数据"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import GrowthOverview from '@/components/GrowthOverview.vue'
import PageHeader from '@/components/PageHeader.vue'
import { fetchGrowthHistory, fetchGrowthProfile } from '@/api/growth'

const route = useRoute()
const router = useRouter()
const profile = ref(null)
const points = ref([])
const loading = ref(false)
const error = ref('')

async function loadGrowth() {
  loading.value = true
  error.value = ''
  try {
    const studentId = Number(route.params.studentId)
    const [profileResponse, historyResponse] = await Promise.all([
      fetchGrowthProfile(studentId),
      fetchGrowthHistory(studentId),
    ])
    profile.value = profileResponse.data
    points.value = historyResponse.data.points
  } catch (requestError) {
    error.value = requestError.message || '学生成长数据加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadGrowth)
</script>

<style scoped>
.page-error { margin-bottom: 16px; }
</style>