<template>
  <div class="wm-page">
    <div class="wm-page-header">
      <h1 class="wm-page-title">
        后端连接测试
      </h1>
      <p class="wm-page-subtitle">
        本页面用于验证前端开发服务器、Vite 代理与 FastAPI 服务之间的真实网络连通性，数据全部来自后端接口返回。
      </p>
    </div>

    <HealthPanel
      :health="appStore.health"
      :loading="appStore.healthLoading"
      :error="appStore.healthError"
      :checked-at="appStore.lastCheckedAt"
      :api-base-url="apiBaseUrl"
      @refresh="handleCheck"
    />

    <section class="wm-card guide">
      <h2 class="guide__title">
        本地启动步骤
      </h2>
      <ol class="guide__list">
        <li>后端：进入 <span class="wm-mono">backend</span> 目录，安装依赖后执行 <span class="wm-mono">uvicorn app.main:app --reload</span>。</li>
        <li>前端：进入 <span class="wm-mono">frontend</span> 目录，执行 <span class="wm-mono">npm install</span> 与 <span class="wm-mono">npm run dev</span>。</li>
        <li>访问本页面点击“重新检测”，出现“服务正常”即表示前后端已连通。</li>
      </ol>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="请求路径说明"
        description="前端请求 /api/v1/health，由 Vite 代理转发至 VITE_PROXY_TARGET（默认 http://127.0.0.1:8000），因此不会产生跨域问题；生产环境直接访问后端时已配置 CORS 白名单。"
      />
    </section>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'

import HealthPanel from '@/components/HealthPanel.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'

async function handleCheck() {
  try {
    await appStore.checkHealth()
  } catch {
    // 错误信息已由 store 记录并展示在页面中
  }
}

onMounted(handleCheck)
</script>

<style scoped>
.guide {
  margin-top: 18px;
  padding: 22px;
}

.guide__title {
  margin: 0 0 12px;
  font-size: 16px;
}

.guide__list {
  margin: 0 0 16px;
  padding-left: 20px;
  color: var(--wm-text-secondary);
  font-size: 13px;
  line-height: 2;
}
</style>