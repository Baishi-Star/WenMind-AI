<template>
  <div class="wm-page">
    <section class="hero wm-card">
      <div class="hero__content">
        <el-tag
          effect="plain"
          type="primary"
        >
          WenMind AI · 文思智评 V1.0
        </el-tag>
        <h1 class="hero__title">
          让每一次作文评价，<br>都成为下一次写作成长的起点。
        </h1>
        <p class="hero__desc">
          面向高中生与语文教师的个性化写作成长系统：多 Agent 协同评价、知识库检索、评分证据追溯、
          学生申诉与教师复核、争议驱动的规则优化，以及跨作文的能力成长画像。
        </p>
        <div class="hero__actions">
          <el-button
            type="primary"
            size="large"
            @click="goStatus"
          >
            测试后端连接
          </el-button>
          <el-button
            size="large"
            text
            type="primary"
            @click="showRoadmap = true"
          >
            查看建设计划
          </el-button>
        </div>
        <p class="hero__notice">
          AI 评价属于教学诊断性参考，不等同于高考正式阅卷分数，最终评价以教师复核为准。
        </p>
      </div>
      <div class="hero__status">
        <div class="status-card">
          <span class="status-card__label">后端服务状态</span>
          <div class="status-card__value">
            <span
              class="status-dot"
              :class="statusDotClass"
            />
            {{ statusText }}
          </div>
          <p class="status-card__hint">
            {{ appStore.lastCheckedAt ? `最近检测：${formatDateTime(appStore.lastCheckedAt)}` : '页面加载后自动检测一次' }}
          </p>
          <el-button
            size="small"
            :loading="appStore.healthLoading"
            @click="handleCheck"
          >
            立即检测
          </el-button>
        </div>
      </div>
    </section>

    <section class="wm-grid capability">
      <article
        v-for="item in capabilities"
        :key="item.title"
        class="wm-card capability__item"
      >
        <el-icon
          class="capability__icon"
          :size="22"
        >
          <component :is="item.icon" />
        </el-icon>
        <h3>{{ item.title }}</h3>
        <p>{{ item.description }}</p>
        <el-tag
          size="small"
          effect="plain"
          type="info"
        >
          {{ item.stage }}
        </el-tag>
      </article>
    </section>

    <el-drawer
      v-model="showRoadmap"
      title="阶段建设计划"
      size="420px"
    >
      <el-timeline>
        <el-timeline-item
          v-for="step in roadmap"
          :key="step.title"
          :type="step.done ? 'success' : 'info'"
          :hollow="!step.done"
        >
          <strong>{{ step.title }}</strong>
          <p class="wm-muted roadmap__desc">
            {{ step.description }}
          </p>
        </el-timeline-item>
      </el-timeline>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChatLineSquare, Connection, DataAnalysis, DocumentChecked, Search, UserFilled } from '@element-plus/icons-vue'

import { useAppStore } from '@/stores/app'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const appStore = useAppStore()
const showRoadmap = ref(false)

const statusText = computed(() => {
  if (appStore.healthLoading) return '检测中'
  if (appStore.isBackendOnline) return '后端连接正常'
  if (appStore.healthError) return '后端未连接'
  return '尚未检测'
})

const statusDotClass = computed(() => ({
  'is-online': appStore.isBackendOnline,
  'is-offline': Boolean(appStore.healthError),
}))

const capabilities = [
  { title: '多 Agent 协同评价', description: '审题、内容、结构、语言分工分析，综合反馈与质量审核，输出结构化诊断结果。', icon: Connection, stage: '阶段 4' },
  { title: '写作知识库 RAG', description: '评价量规与教学资料上传、切片、向量化检索，命中来源可查看、不编造引用。', icon: Search, stage: '阶段 5' },
  { title: '评分证据追溯', description: '反馈条目关联作文原文片段与评价标准，后端校验引用真实性，失败标记待核验。', icon: DocumentChecked, stage: '阶段 6' },
  { title: '学生申诉与教师复核', description: '学生可质疑评价，教师拥有最终复核权；AI 原始分与教师最终分双轨保存。', icon: UserFilled, stage: '阶段 6' },
  { title: '争议驱动规则优化', description: '教师确认的问题标签进入统计，生成待审核的规则优化建议，人工发布后生效。', icon: ChatLineSquare, stage: '阶段 7' },
  { title: '成长画像与训练推荐', description: '基于多篇有效评价形成维度趋势、优势与薄弱项，并给出可解释的专项训练任务。', icon: DataAnalysis, stage: '阶段 7' },
]

const roadmap = [
  { title: '阶段 1：工程初始化', description: '前后端骨架、统一响应与异常、健康检查与前后端连通验证。', done: true },
  { title: '阶段 2：登录与角色权限', description: '用户模型、JWT 登录、学生/教师/管理员三端布局与路由守卫。', done: false },
  { title: '阶段 3：作文提交与评价任务', description: '作文数据模型、提交校验、评价状态机与 LLM 适配层。', done: false },
  { title: '阶段 4—7：核心业务闭环', description: '多 Agent、RAG、证据追溯、申诉复核、规则版本与成长画像。', done: false },
  { title: '阶段 8：测试与交付', description: '自动化测试、README、演示数据、录屏与打包检查。', done: false },
]

function goStatus() {
  router.push('/system/status')
}

async function handleCheck() {
  try {
    await appStore.checkHealth()
  } catch {
    // 失败状态已在首页状态卡片中体现
  }
}

onMounted(handleCheck)
</script>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: 1.7fr 1fr;
  gap: 28px;
  padding: 36px;
  background: linear-gradient(135deg, #ffffff 0%, #f2f6ff 60%, #eaf8f8 100%);
}

.hero__title {
  margin: 18px 0 14px;
  font-size: 32px;
  line-height: 1.45;
  letter-spacing: 0.5px;
}

.hero__desc {
  margin: 0;
  max-width: 640px;
  color: var(--wm-text-secondary);
  line-height: 1.9;
  font-size: 14px;
}

.hero__actions {
  margin-top: 22px;
}

.hero__notice {
  margin: 18px 0 0;
  font-size: 12px;
  color: var(--wm-text-secondary);
}

.hero__status {
  display: flex;
  align-items: center;
}

.status-card {
  width: 100%;
  padding: 20px;
  border-radius: var(--wm-radius-md);
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid var(--wm-border);
}

.status-card__label {
  font-size: 12px;
  color: var(--wm-text-secondary);
}

.status-card__value {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 6px;
  font-size: 18px;
  font-weight: 600;
}

.status-card__hint {
  margin: 0 0 14px;
  font-size: 12px;
  color: var(--wm-text-secondary);
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #b6bfce;
}

.status-dot.is-online {
  background: #16a34a;
  box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.15);
}

.status-dot.is-offline {
  background: #dc2626;
  box-shadow: 0 0 0 4px rgba(220, 38, 38, 0.12);
}

.capability {
  margin-top: 20px;
  grid-template-columns: repeat(3, 1fr);
}

.capability__item {
  padding: 20px;
}

.capability__item h3 {
  margin: 12px 0 8px;
  font-size: 16px;
}

.capability__item p {
  margin: 0 0 12px;
  min-height: 66px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--wm-text-secondary);
}

.capability__icon {
  color: var(--wm-primary);
}

.roadmap__desc {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.8;
}

@media (max-width: 960px) {
  .hero {
    grid-template-columns: 1fr;
    padding: 24px;
  }

  .hero__title {
    font-size: 26px;
  }

  .capability {
    grid-template-columns: 1fr;
  }

  .capability__item p {
    min-height: auto;
  }
}
</style>