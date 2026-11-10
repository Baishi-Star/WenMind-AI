<template>
  <div v-if="module">
    <PageHeader
      :title="module.title"
      :subtitle="module.subtitle"
    >
      <template #actions>
        <el-button @click="goDashboard">
          返回工作台
        </el-button>
      </template>
    </PageHeader>

    <div class="module-grid">
      <section class="wm-card module-card">
        <h2 class="module-card__title">
          功能说明
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
      </section>

      <section class="wm-card module-card">
        <h2 class="module-card__title">
          业务数据
        </h2>
        <el-empty description="暂无数据" />
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
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

const module = computed(() => MODULES[props.moduleKey])

function goDashboard() {
  router.push(authStore.homePath)
}
</script>

<style scoped>
.module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.module-card {
  padding: 20px;
}

.module-card__title {
  margin: 0 0 14px;
  font-size: 16px;
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

@media (max-width: 1100px) {
  .module-grid {
    grid-template-columns: 1fr;
  }
}
</style>