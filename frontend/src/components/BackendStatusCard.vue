<template>
  <section class="wm-card backend-card">
    <div class="backend-card__head">
      <div>
        <h2 class="backend-card__title">
          后端服务连接
        </h2>
        <p class="backend-card__desc">
          真实请求 <span class="wm-mono">GET /api/v1/health</span>
        </p>
      </div>
      <el-button
        size="small"
        :loading="appStore.healthLoading"
        @click="handleCheck"
      >
        刷新
      </el-button>
    </div>

    <div
      v-loading="appStore.healthLoading"
      class="backend-card__body"
    >
      <el-alert
        v-if="appStore.healthError"
        type="error"
        :closable="false"
        show-icon
        title="后端未连接"
        :description="appStore.healthError"
      />
      <template v-else-if="appStore.health">
        <div class="backend-card__status">
          <span class="status-dot is-online" />
          <strong>{{ appStore.health.app }} 运行正常</strong>
        </div>
        <dl class="backend-card__meta">
          <div><dt>版本</dt><dd>{{ appStore.health.version }}</dd></div>
          <div><dt>环境</dt><dd>{{ appStore.health.environment }}</dd></div>
          <div><dt>运行时长</dt><dd>{{ formatUptime(appStore.health.uptime_seconds) }}</dd></div>
          <div>
            <dt>模型模式</dt>
            <dd>{{ appStore.health.llm.mode === 'mock' ? 'Mock（未调用真实模型）' : '真实模型' }}</dd>
          </div>
        </dl>
        <el-descriptions
          v-if="detailed"
          :column="2"
          border
          size="small"
          class="backend-card__extra"
        >
          <el-descriptions-item label="API 前缀">
            {{ appStore.health.api_prefix }}
          </el-descriptions-item>
          <el-descriptions-item label="服务器时间">
            {{ formatDateTime(appStore.health.server_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="接口检查">
            {{ appStore.health.checks.api }}
          </el-descriptions-item>
          <el-descriptions-item label="模型配置">
            {{ appStore.health.llm.configured ? '已配置' : '未配置' }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty
        v-else-if="!appStore.healthLoading"
        description="尚未检测后端状态"
        :image-size="70"
      />
    </div>
  </section>
</template>

<script setup>
import { onMounted } from 'vue'

import { useAppStore } from '@/stores/app'
import { formatDateTime, formatUptime } from '@/utils/format'

defineProps({
  detailed: { type: Boolean, default: false },
})

const appStore = useAppStore()

async function handleCheck() {
  try {
    await appStore.checkHealth()
  } catch {
    // 连接失败状态已展示在卡片内
  }
}

onMounted(() => {
  if (!appStore.health && !appStore.healthLoading) {
    handleCheck()
  }
})
</script>

<style scoped>
.backend-card {
  padding: 20px;
}

.backend-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.backend-card__title {
  margin: 0 0 4px;
  font-size: 16px;
}

.backend-card__desc {
  margin: 0;
  font-size: 12px;
  color: var(--wm-text-secondary);
}

.backend-card__body {
  min-height: 96px;
}

.backend-card__status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.is-online {
  background: #16a34a;
  box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.14);
}

.backend-card__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.backend-card__meta div {
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--wm-bg-soft);
}

.backend-card__meta dt {
  font-size: 12px;
  color: var(--wm-text-secondary);
}

.backend-card__meta dd {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 600;
}

.backend-card__extra {
  margin-top: 14px;
}
</style>