<template>
  <div>
    <PageHeader
      :title="`${roleInfo.name}工作台`"
      :subtitle="roleInfo.description"
    >
      <template #tag>
        <DemoSessionTag />
      </template>
      <template #actions>
        <el-button
          type="primary"
          plain
          @click="goSystemStatus"
        >
          后端连接测试
        </el-button>
      </template>
    </PageHeader>

    <section class="welcome-card wm-card">
      <div>
        <p class="welcome-card__eyebrow">
          WenMind AI · {{ roleInfo.englishName }}
        </p>
        <h2>{{ greeting }}，{{ authStore.displayName }}</h2>
        <p>{{ workspaceIntro }}</p>
      </div>
      <div class="welcome-card__meta">
        <span>当前角色</span>
        <strong>{{ roleInfo.name }}</strong>
        <small>界面框架阶段 · 业务数据待后端接入</small>
      </div>
    </section>

    <div class="workspace-grid">
      <div class="workspace-main">
        <section class="wm-card workspace-section">
          <div class="workspace-section__head">
            <h2>功能导航</h2>
            <span>所有入口均可点击进入对应页面</span>
          </div>
          <div class="quick-grid">
            <button
              v-for="item in quickLinks"
              :key="item.path"
              type="button"
              class="quick-card"
              @click="go(item.path)"
            >
              <el-icon :size="20">
                <component :is="item.icon" />
              </el-icon>
              <span class="quick-card__text">
                <strong>{{ item.title }}</strong>
                <small>{{ item.path === roleInfo.homePath ? '当前工作台' : '界面框架 · 待接入业务数据' }}</small>
              </span>
              <el-icon class="quick-card__arrow">
                <ArrowRight />
              </el-icon>
            </button>
          </div>
        </section>

        <section class="wm-card workspace-section">
          <div class="workspace-section__head">
            <h2>核心业务闭环</h2>
            <span>评价不是终点，复核与改进同样重要</span>
          </div>
          <el-steps
            :active="-1"
            align-center
            class="workflow-steps"
          >
            <el-step
              v-for="step in workflow"
              :key="step"
              :title="step"
              status="wait"
            />
          </el-steps>
          <p class="workflow-note">
            当前为页面框架展示，流程状态将在对应业务阶段由后端真实任务数据驱动。
          </p>
        </section>
      </div>

      <aside class="workspace-aside">
        <BackendStatusCard :detailed="role === 'admin'" />
        <section class="wm-card workspace-section">
          <div class="workspace-section__head">
            <h2>数据接入状态</h2>
          </div>
          <ul class="integration-list">
            <li
              v-for="item in integrationItems"
              :key="item.label"
            >
              <span>{{ item.label }}</span>
              <el-tag
                size="small"
                :type="item.done ? 'success' : 'info'"
                effect="plain"
              >
                {{ item.done ? '已连通' : '待接入' }}
              </el-tag>
            </li>
          </ul>
        </section>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="评价定位说明"
          description="AI 评价属于教学诊断性参考，不等同于高考正式阅卷分数，最终结果以教师复核为准。"
        />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

import BackendStatusCard from '@/components/BackendStatusCard.vue'
import DemoSessionTag from '@/components/DemoSessionTag.vue'
import PageHeader from '@/components/PageHeader.vue'
import { NAVIGATIONS, ROLES } from '@/config/portal'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  role: { type: String, required: true },
})

const router = useRouter()
const authStore = useAuthStore()

const roleInfo = computed(() => ROLES[props.role])
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 11) return '早上好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const intros = {
  student: '在这里进入作文提交、AI 评价、申诉与成长档案等页面。业务数据将在后端接口接入后展示。',
  teacher: '在这里进入班级管理、评价复核、申诉处理与规则版本管理页面，所有复核动作后续均由后端留痕。',
  admin: '在这里查看真实的后端健康状态，并进入知识库、Agent 监控、模型配置与日志等管理页面。',
}
const workspaceIntro = computed(() => intros[props.role])

const workflows = {
  student: ['提交作文', '多 Agent 评价', '证据追溯', '申诉复核', '成长训练'],
  teacher: ['布置任务', '查看评价', '处理申诉', '争议归类', '规则优化'],
  admin: ['知识入库', 'Agent 监控', '争议统计', '版本测试', '人工发布'],
}
const workflow = computed(() => workflows[props.role])

const quickLinks = computed(() => (NAVIGATIONS[props.role] || []).filter((item) => item.path !== roleInfo.value.homePath))

const integrationItems = computed(() => [
  { label: '后端健康检查接口', done: true },
  { label: '账号密码认证与 JWT', done: false },
  { label: `${roleInfo.value.name}端业务数据接口`, done: false },
  { label: '数据库持久化记录', done: false },
])

function go(path) {
  router.push(path)
}

function goSystemStatus() {
  router.push('/system/status')
}
</script>

<style scoped>
.welcome-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 26px 28px;
  margin-bottom: 20px;
  background: linear-gradient(120deg, rgba(255, 255, 255, 0.96), rgba(239, 242, 255, 0.92));
}

.welcome-card__eyebrow {
  margin: 0 0 8px;
  color: var(--wm-primary);
  font-size: 12px;
  letter-spacing: 1px;
}

.welcome-card h2 {
  margin: 0 0 10px;
  font-size: 25px;
}

.welcome-card p:not(.welcome-card__eyebrow) {
  margin: 0;
  max-width: 760px;
  color: var(--wm-text-secondary);
  font-size: 13px;
  line-height: 1.9;
}

.welcome-card__meta {
  min-width: 150px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid var(--wm-border);
}

.welcome-card__meta span,
.welcome-card__meta small {
  color: var(--wm-text-secondary);
  font-size: 11px;
}

.welcome-card__meta strong {
  font-size: 20px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 20px;
  align-items: start;
}

.workspace-main,
.workspace-aside {
  display: grid;
  gap: 20px;
}

.workspace-section {
  padding: 20px;
}

.workspace-section__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.workspace-section__head h2 {
  margin: 0;
  font-size: 16px;
}

.workspace-section__head span {
  color: var(--wm-text-secondary);
  font-size: 12px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.quick-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--wm-border);
  border-radius: 12px;
  background: #fff;
  color: var(--wm-primary);
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-card:hover {
  border-color: var(--wm-primary-soft);
  box-shadow: 0 8px 20px rgba(79, 70, 229, 0.1);
  transform: translateY(-2px);
}

.quick-card__text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quick-card__text strong {
  color: var(--wm-text-main);
  font-size: 14px;
}

.quick-card__text small {
  color: var(--wm-text-secondary);
  font-size: 11px;
}

.quick-card__arrow {
  color: var(--wm-text-secondary);
}

.workflow-steps {
  margin-top: 8px;
}

.workflow-steps :deep(.el-step__title) {
  font-size: 12px;
}

.workflow-note {
  margin: 14px 0 0;
  color: var(--wm-text-secondary);
  font-size: 12px;
  text-align: center;
}

.integration-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.integration-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: var(--wm-text-secondary);
}

@media (max-width: 1250px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .welcome-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>