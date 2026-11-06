<template>
  <section class="wm-card health-panel">
    <div class="health-panel__head">
      <div>
        <h2 class="health-panel__title">
          后端服务健康检查
        </h2>
        <p class="wm-muted health-panel__desc">
          通过 Axios 请求 <span class="wm-mono">GET {{ apiBaseUrl }}/health</span>，验证前后端真实连通。
        </p>
      </div>
      <el-button
        type="primary"
        :loading="loading"
        @click="emit('refresh')"
      >
        {{ loading ? '检测中' : '重新检测' }}
      </el-button>
    </div>

    <el-alert
      v-if="error"
      type="error"
      :closable="false"
      show-icon
      title="后端连接失败"
      :description="error"
      class="health-panel__alert"
    />

    <div
      v-loading="loading"
      element-loading-text="正在请求后端健康检查接口"
      class="health-panel__body"
    >
      <el-empty
        v-if="!health && !error && !loading"
        description="尚未检测，点击右上角按钮开始"
      />

      <template v-if="health">
        <div class="health-panel__status">
          <el-tag
            type="success"
            effect="dark"
          >
            服务正常
          </el-tag>
          <span class="wm-muted">最近检测时间：{{ formatDateTime(checkedAt) }}</span>
        </div>
        <el-descriptions
          :column="2"
          border
        >
          <el-descriptions-item label="服务名称">
            {{ health.app }}
          </el-descriptions-item>
          <el-descriptions-item label="版本">
            {{ health.version }}
          </el-descriptions-item>
          <el-descriptions-item label="运行环境">
            {{ health.environment }}
          </el-descriptions-item>
          <el-descriptions-item label="API 前缀">
            {{ health.api_prefix }}
          </el-descriptions-item>
          <el-descriptions-item label="服务器时间">
            {{ formatDateTime(health.server_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="已运行时长">
            {{ formatUptime(health.uptime_seconds) }}
          </el-descriptions-item>
          <el-descriptions-item label="模型调用模式">
            <el-tag
              size="small"
              :type="health.llm.mode === 'mock' ? 'warning' : 'success'"
              effect="plain"
            >
              {{ health.llm.mode === 'mock' ? 'Mock 模式（未调用真实模型）' : '真实模型调用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="模型配置完整度">
            {{ health.llm.configured ? '已配置' : '未配置（阶段 1 无需配置）' }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </div>
  </section>
</template>

<script setup>
import { formatDateTime, formatUptime } from '@/utils/format'

defineProps({
  health: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  checkedAt: { type: Date, default: null },
  apiBaseUrl: { type: String, default: '/api/v1' },
})

const emit = defineEmits(['refresh'])
</script>

<style scoped>
.health-panel {
  padding: 22px;
}

.health-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}

.health-panel__title {
  margin: 0 0 6px;
  font-size: 18px;
}

.health-panel__desc {
  margin: 0;
  font-size: 13px;
}

.health-panel__alert {
  margin-bottom: 16px;
}

.health-panel__body {
  min-height: 160px;
}

.health-panel__status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  font-size: 13px;
}
</style>