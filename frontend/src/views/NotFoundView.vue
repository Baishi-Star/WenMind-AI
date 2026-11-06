<template>
  <div class="not-found">
    <el-result
      icon="warning"
      title="页面不存在"
      sub-title="你访问的地址没有对应页面，请返回首页或进入演示工作台。"
    >
      <template #extra>
        <el-button
          type="primary"
          @click="goHome"
        >
          返回产品首页
        </el-button>
        <el-button @click="goPortal">
          进入我的工作台
        </el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function goHome() {
  router.push('/')
}

function goPortal() {
  router.push(authStore.isAuthenticated ? authStore.homePath : '/login')
}
</script>

<style scoped>
.not-found {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--wm-bg);
}
</style>