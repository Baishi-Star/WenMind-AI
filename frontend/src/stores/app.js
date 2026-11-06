import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { fetchHealth } from '@/api/system'

export const useAppStore = defineStore('app', () => {
  const health = ref(null)
  const healthLoading = ref(false)
  const healthError = ref('')
  const lastCheckedAt = ref(null)

  const isBackendOnline = computed(() => health.value?.status === 'ok' && !healthError.value)

  async function checkHealth() {
    healthLoading.value = true
    healthError.value = ''
    try {
      const response = await fetchHealth()
      health.value = response.data
      lastCheckedAt.value = new Date()
      return response.data
    } catch (error) {
      health.value = null
      healthError.value = error.message || '健康检查失败'
      lastCheckedAt.value = new Date()
      throw error
    } finally {
      healthLoading.value = false
    }
  }

  return {
    health,
    healthLoading,
    healthError,
    lastCheckedAt,
    isBackendOnline,
    checkHealth,
  }
})