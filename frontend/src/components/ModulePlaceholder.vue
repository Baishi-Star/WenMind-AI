<template>
  <div v-if="module">
    <PageHeader
      :title="module.title"
      :subtitle="module.subtitle"
    >
      <template #tag>
        <el-tag
          type="warning"
          effect="plain"
        >
          界面框架 · 待接入后端
        </el-tag>
      </template>
      <template #actions>
        <el-button @click="goDashboard">
          返回工作台
        </el-button>
      </template>
    </PageHeader>

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      class="module-notice"
      title="本页面当前仅提供信息架构与交互入口"
      description="后端业务接口尚未接入，因此不展示虚构的作文、分数或统计结果。下方列出本页计划具备的真实能力与 API 契约。"
    />

    <div class="module-grid">
      <section class="wm-card module-card">
        <h2 class="module-card__title">
          计划能力
        </h2>
        <ul class="capability-list">
          <li
            v-for="item in module.capabilities"
            :key="item"
          >
            <el-icon><CircleCheck /></el-icon>
            <span>{{ item }}</span>
          </li>
        </ul>
        <div class="module-card__footer">
          <el-tag
            size="small"
            effect="plain"
            type="info"
          >
            计划实现：{{ module.stage }}
          </el-tag>
        </div>
      </section>

      <section class="wm-card module-card">
        <div class="module-card__head">
          <h2 class="module-card__title">
            后端 API 契约
          </h2>
          <el-button
            text
            type="primary"
            size="small"
            @click="showApis = !showApis"
          >
            {{ showApis ? '收起' : '展开' }}
          </el-button>
        </div>
        <el-collapse-transition>
          <div
            v-show="showApis"
            class="api-list"
          >
            <div
              v-for="api in module.apis"
              :key="api"
              class="api-item"
            >
              <el-tag
                size="small"
                :type="api.startsWith('POST') ? 'success' : 'primary'"
                effect="plain"
              >
                {{ api.split(' ')[0] }}
              </el-tag>
              <span class="wm-mono">{{ api.split(' ').slice(1).join(' ') }}</span>
            </div>
          </div>
        </el-collapse-transition>
        <p class="module-card__hint">
          接口将在对应阶段以后端真实实现为准，当前点击导航不会产生模拟业务数据。
        </p>
      </section>
    </div>

    <section class="wm-card module-card module-card--empty">
      <h2 class="module-card__title">
        业务数据区
      </h2>
      <el-empty description="暂无数据：后端业务接口待接入">
        <el-button
          type="primary"
          plain
          @click="goSystemStatus"
        >
          检查后端连接
        </el-button>
      </el-empty>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CircleCheck } from '@element-plus/icons-vue'

import PageHeader from '@/components/PageHeader.vue'
import { MODULES } from '@/config/modules'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  moduleKey: { type: String, required: true },
})

const router = useRouter()
const authStore = useAuthStore()
const showApis = ref(true)

const module = computed(() => MODULES[props.moduleKey])

function goDashboard() {
  router.push(authStore.homePath)
}

function goSystemStatus() {
  router.push('/system/status')
}
</script>

<style scoped>
.module-notice {
  margin-bottom: 18px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.module-card {
  padding: 20px;
}

.module-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.module-card__title {
  margin: 0 0 14px;
  font-size: 16px;
}

.module-card__footer {
  margin-top: 16px;
}

.module-card__hint {
  margin: 14px 0 0;
  font-size: 12px;
  line-height: 1.8;
  color: var(--wm-text-secondary);
}

.module-card--empty {
  margin-top: 18px;
}

.capability-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.capability-list li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--wm-text-secondary);
}

.capability-list .el-icon {
  margin-top: 3px;
  color: var(--wm-accent);
}

.api-list {
  display: grid;
  gap: 10px;
}

.api-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: 1px solid var(--wm-border);
  border-radius: 8px;
  font-size: 12px;
  overflow-wrap: anywhere;
}

@media (max-width: 1100px) {
  .module-grid {
    grid-template-columns: 1fr;
  }
}
</style>