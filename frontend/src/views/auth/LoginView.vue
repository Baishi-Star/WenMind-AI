<template>
  <div class="login-page">
    <div class="login-page__glow login-page__glow--one" />
    <div class="login-page__glow login-page__glow--two" />

    <div class="login-shell">
      <section class="login-intro">
        <router-link
          to="/"
          class="login-brand"
        >
          <img
            src="@/assets/logo.svg"
            alt="WenMind AI"
          >
          <span><strong>WenMind AI</strong><small>文思智评</small></span>
        </router-link>
        <h1>让每一次作文评价，<br>都成为下一次写作成长的起点。</h1>
        <p>
          多 Agent 协同评价、原文证据追溯、学生申诉与教师复核、争议驱动的规则优化，
          共同构成可解释、可质疑、可复核的写作成长闭环。
        </p>
        <ul class="login-intro__points">
          <li>评价关联原文证据与量规版本</li>
          <li>AI 原始结果与教师复核结果双轨保存</li>
          <li>正式评分规则只能由人工审核发布</li>
        </ul>
      </section>

      <section class="login-panel wm-card">
        <div class="login-panel__head">
          <h2>选择演示角色</h2>
          <p>进入对应工作台，体验完整页面导航与布局。</p>
        </div>

        <el-alert
          type="warning"
          :closable="false"
          show-icon
          title="当前为前端演示角色入口"
          description="后端账号密码认证尚未接入，本页不会生成真实访问令牌，也不会展示虚构业务数据。"
          class="login-panel__notice"
        />

        <div
          class="role-list"
          role="radiogroup"
          aria-label="演示角色"
        >
          <button
            v-for="item in roleOptions"
            :key="item.key"
            type="button"
            class="role-card"
            :class="{ 'is-selected': selectedRole === item.key }"
            :aria-pressed="selectedRole === item.key"
            @click="selectedRole = item.key"
          >
            <span class="role-card__badge">{{ item.name }}</span>
            <span class="role-card__name">{{ item.englishName }}</span>
            <span class="role-card__desc">{{ item.description }}</span>
            <span class="role-card__points">
              <span
                v-for="point in item.highlights"
                :key="point"
              >{{ point }}</span>
            </span>
            <el-icon
              v-if="selectedRole === item.key"
              class="role-card__check"
            >
              <CircleCheckFilled />
            </el-icon>
          </button>
        </div>

        <el-button
          type="primary"
          size="large"
          class="login-panel__submit"
          :loading="entering"
          @click="enterPortal"
        >
          进入{{ selectedRoleInfo.name }}工作台
        </el-button>
        <p
          v-if="authStore.isAuthenticated"
          class="login-panel__current"
        >
          当前会话为「{{ authStore.roleInfo?.name }}」，进入新角色将替换该演示会话。
        </p>
        <div class="login-panel__links">
          <router-link to="/">返回产品首页</router-link>
          <router-link to="/system/status">后端连接测试</router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled } from '@element-plus/icons-vue'

import { ROLES } from '@/config/portal'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const roleOptions = Object.values(ROLES)
const selectedRole = ref(authStore.role || 'student')
const entering = ref(false)

const selectedRoleInfo = computed(() => ROLES[selectedRole.value])

async function enterPortal() {
  entering.value = true
  try {
    const home = authStore.loginAsRole(selectedRole.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    const target = redirect.startsWith(`/${selectedRole.value}/`) ? redirect : home
    ElMessage.success(`已进入${selectedRoleInfo.value.name}演示工作台`)
    await router.push(target)
  } finally {
    entering.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  padding: 48px 32px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: linear-gradient(150deg, #f6f8ff 0%, #eef2ff 48%, #eefcfb 100%);
}

.login-page__glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(10px);
  opacity: 0.5;
  pointer-events: none;
}

.login-page__glow--one {
  width: 420px;
  height: 420px;
  top: -140px;
  right: -80px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.22), transparent 68%);
}

.login-page__glow--two {
  width: 380px;
  height: 380px;
  bottom: -120px;
  left: -100px;
  background: radial-gradient(circle, rgba(20, 184, 166, 0.18), transparent 68%);
}

.login-shell {
  position: relative;
  width: min(1180px, 100%);
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 48px;
  align-items: center;
}

.login-brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.login-brand img {
  width: 46px;
  height: 46px;
}

.login-brand span {
  display: flex;
  flex-direction: column;
}

.login-brand strong {
  font-size: 20px;
}

.login-brand small {
  color: var(--wm-text-secondary);
}

.login-intro h1 {
  margin: 0 0 20px;
  font-size: 34px;
  line-height: 1.55;
  letter-spacing: 0.5px;
}

.login-intro p {
  margin: 0;
  color: var(--wm-text-secondary);
  font-size: 14px;
  line-height: 2;
}

.login-intro__points {
  margin: 26px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 12px;
}

.login-intro__points li {
  position: relative;
  padding-left: 20px;
  font-size: 13px;
  color: var(--wm-text-main);
}

.login-intro__points li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 7px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--wm-primary), var(--wm-accent));
}

.login-panel {
  padding: 30px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(18px);
}

.login-panel__head h2 {
  margin: 0 0 8px;
  font-size: 24px;
}

.login-panel__head p {
  margin: 0;
  color: var(--wm-text-secondary);
  font-size: 13px;
}

.login-panel__notice {
  margin: 20px 0;
}

.role-list {
  display: grid;
  gap: 12px;
}

.role-card {
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  padding: 16px 18px;
  text-align: left;
  border: 1px solid var(--wm-border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.role-card:hover {
  border-color: var(--wm-primary-soft);
  transform: translateY(-1px);
}

.role-card.is-selected {
  border-color: var(--wm-primary);
  box-shadow: 0 10px 24px rgba(79, 70, 229, 0.12);
  background: #f5f7ff;
}

.role-card__badge {
  grid-row: span 2;
  align-self: start;
  padding: 5px 10px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--wm-primary), var(--wm-primary-soft));
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}

.role-card__name {
  font-size: 12px;
  color: var(--wm-text-secondary);
  letter-spacing: 0.6px;
}

.role-card__desc {
  grid-column: 1 / -1;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--wm-text-main);
}

.role-card__points {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.role-card__points span {
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--wm-bg-soft);
  color: var(--wm-text-secondary);
  font-size: 11px;
}

.role-card__check {
  position: absolute;
  top: 14px;
  right: 14px;
  color: var(--wm-primary);
  font-size: 20px;
}

.login-panel__submit {
  width: 100%;
  margin-top: 22px;
}

.login-panel__current {
  margin: 12px 0 0;
  text-align: center;
  font-size: 12px;
  color: var(--wm-text-secondary);
}

.login-panel__links {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 16px;
  font-size: 12px;
}

.login-panel__links a {
  color: var(--wm-primary);
}

@media (max-width: 1000px) {
  .login-shell {
    grid-template-columns: 1fr;
    gap: 28px;
  }

  .login-intro h1 {
    font-size: 27px;
  }
}
</style>