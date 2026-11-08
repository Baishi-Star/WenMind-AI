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
        <p>多 Agent 协同评价、原文证据追溯、学生申诉与教师复核，共同构成可解释、可质疑、可复核的写作成长闭环。</p>
        <ul class="login-intro__points">
          <li>评价关联原文证据与量规版本</li>
          <li>AI 原始结果与教师复核结果双轨保存</li>
          <li>正式评分规则只能由人工审核发布</li>
        </ul>
      </section>

      <section class="login-panel wm-card">
        <div class="login-panel__head">
          <h2>账号登录</h2>
          <p>选择演示角色可自动填入账号，登录由 FastAPI 真实校验并返回 JWT。</p>
        </div>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="本地演示账号，统一初始密码 Demo@2026"
          description="账号密码仅用于初赛演示，生产部署必须修改；登录后的上传、删除和检索均为真实后端操作。"
          class="login-panel__notice"
        />

        <div
          class="role-list"
          role="radiogroup"
          aria-label="演示账号"
        >
          <button
            v-for="item in roleOptions"
            :key="item.key"
            type="button"
            class="role-card"
            :class="{ 'is-selected': selectedRole === item.key }"
            @click="selectRole(item.key)"
          >
            <span class="role-card__badge">{{ item.name }}</span>
            <span class="role-card__account">{{ item.username }}</span>
            <span class="role-card__desc">{{ item.description }}</span>
          </button>
        </div>

        <el-form
          label-position="top"
          class="login-form"
          @submit.prevent="enterPortal"
        >
          <el-form-item
            label="用户名"
            required
          >
            <el-input
              v-model.trim="username"
              autocomplete="username"
              placeholder="请输入用户名"
              size="large"
            />
          </el-form-item>
          <el-form-item
            label="密码"
            required
          >
            <el-input
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              size="large"
              show-password
              @keyup.enter="enterPortal"
            />
          </el-form-item>
          <el-alert
            v-if="loginError"
            type="error"
            :closable="false"
            show-icon
            :title="loginError"
            class="login-form__error"
          />
          <el-button
            type="primary"
            size="large"
            native-type="submit"
            class="login-panel__submit"
            :loading="entering"
            :disabled="!username || !password"
          >
            登录并进入{{ selectedRoleInfo.name }}工作台
          </el-button>
        </el-form>
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

import { ROLES } from '@/config/portal'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const demoAccounts = {
  student: 'demo_student',
  teacher: 'demo_teacher',
  admin: 'demo_admin',
}
const roleOptions = Object.values(ROLES).map((role) => ({ ...role, username: demoAccounts[role.key] }))
const selectedRole = ref(authStore.role || 'student')
const username = ref(demoAccounts[selectedRole.value])
const password = ref('Demo@2026')
const entering = ref(false)
const loginError = ref('')

const selectedRoleInfo = computed(() => ROLES[selectedRole.value])

function selectRole(role) {
  selectedRole.value = role
  username.value = demoAccounts[role]
  password.value = 'Demo@2026'
  loginError.value = ''
}

async function enterPortal() {
  if (!username.value || !password.value || entering.value) return
  entering.value = true
  loginError.value = ''
  try {
    const home = await authStore.login(username.value, password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    const target = redirect.startsWith(`/${authStore.role}/`) ? redirect : home
    ElMessage.success(`登录成功，欢迎${authStore.displayName}`)
    await router.push(target)
  } catch (error) {
    loginError.value = error.message || '登录失败，请检查账号和密码'
  } finally {
    entering.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  padding: 42px 30px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: linear-gradient(150deg, #f6f8ff 0%, #eef2ff 48%, #eefcfb 100%);
}

.login-page__glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.login-page__glow--one {
  width: 420px;
  height: 420px;
  top: -140px;
  right: -80px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.2), transparent 68%);
}

.login-page__glow--two {
  width: 380px;
  height: 380px;
  bottom: -120px;
  left: -100px;
  background: radial-gradient(circle, rgba(20, 184, 166, 0.17), transparent 68%);
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
  margin-bottom: 30px;
}

.login-brand img {
  width: 46px;
  height: 46px;
}

.login-brand span {
  display: flex;
  flex-direction: column;
}

.login-brand strong { font-size: 20px; }
.login-brand small { color: var(--wm-text-secondary); }
.login-intro h1 { margin: 0 0 20px; font-size: 34px; line-height: 1.55; }
.login-intro p { margin: 0; color: var(--wm-text-secondary); font-size: 14px; line-height: 2; }

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
  padding: 28px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(18px);
}

.login-panel__head h2 { margin: 0 0 8px; font-size: 24px; }
.login-panel__head p { margin: 0; color: var(--wm-text-secondary); font-size: 13px; }
.login-panel__notice { margin: 18px 0; }

.role-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.role-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 13px;
  text-align: left;
  border: 1px solid var(--wm-border);
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
}

.role-card.is-selected {
  border-color: var(--wm-primary);
  background: #f4f5ff;
  box-shadow: 0 8px 18px rgba(79, 70, 229, 0.1);
}

.role-card__badge { color: var(--wm-primary); font-weight: 650; font-size: 14px; }
.role-card__account { font-size: 11px; color: var(--wm-text-secondary); }
.role-card__desc { display: none; }
.login-form { margin-top: 20px; }
.login-form__error { margin-bottom: 16px; }
.login-panel__submit { width: 100%; }

.login-panel__links {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 16px;
  font-size: 12px;
}

.login-panel__links a { color: var(--wm-primary); }

@media (min-width: 1100px) {
  .role-card__desc { display: block; font-size: 11px; line-height: 1.7; color: var(--wm-text-secondary); }
}

@media (max-width: 1000px) {
  .login-shell { grid-template-columns: 1fr; gap: 26px; }
  .login-intro h1 { font-size: 27px; }
}

@media (max-width: 560px) {
  .role-list { grid-template-columns: 1fr; }
}
</style>