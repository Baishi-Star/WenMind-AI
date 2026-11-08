<template>
  <div class="login-page">
    <div class="login-page__grid" />
    <div class="login-page__glow login-page__glow--indigo" />
    <div class="login-page__glow login-page__glow--teal" />

    <header class="login-topbar">
      <router-link
        to="/"
        class="login-brand"
        aria-label="WenMind AI 返回产品首页"
      >
        <img
          src="@/assets/logo.svg"
          alt="WenMind AI"
        >
        <span><strong>WenMind AI</strong><small>文思智评</small></span>
      </router-link>
      <router-link
        to="/system/status"
        class="status-link"
      >
        <el-icon><Connection /></el-icon>
        <span>后端连接测试</span>
        <el-icon class="status-link__arrow"><Right /></el-icon>
      </router-link>
    </header>

    <div class="login-shell">
      <section class="login-intro">
        <p class="intro-kicker">
          <span /> WRITING GROWTH SYSTEM
        </p>
        <h1>让每一次作文评价，<br><span>都成为下一次写作成长的起点。</span></h1>
        <p class="intro-lead">
          不止于给出一个结论。WenMind AI 将多 Agent 协同评价、原文证据、学生质疑与教师复核连接起来，让写作改进有据可依。
        </p>

        <div class="feature-list">
          <article class="feature-item">
            <span class="feature-item__number">01</span>
            <div><h2>评价有依据</h2><p>每条问题与建议关联真实原文、评价量规和知识库资料。</p></div>
          </article>
          <article class="feature-item">
            <span class="feature-item__number">02</span>
            <div><h2>质疑有通道</h2><p>尊重个性表达，学生可以追问证据并提出正式申诉。</p></div>
          </article>
          <article class="feature-item">
            <span class="feature-item__number">03</span>
            <div><h2>成长有轨迹</h2><p>AI 原始诊断与教师复核分别保存，形成可持续改进闭环。</p></div>
          </article>
        </div>

        <div
          class="growth-path"
          aria-label="写作成长业务流程"
        >
          <span>提交作文</span><i />
          <span>协同评价</span><i />
          <span>证据追溯</span><i />
          <span>申诉复核</span>
        </div>
      </section>

      <section
        class="login-panel"
        aria-labelledby="login-title"
      >
        <div class="login-panel__shimmer" />
        <header class="login-panel__head">
          <span class="panel-eyebrow">WELCOME BACK</span>
          <h2 id="login-title">
            继续你的写作成长
          </h2>
          <p>使用账号登录，进入对应角色工作台。</p>
        </header>

        <div class="demo-note">
          <el-icon><Lock /></el-icon>
          <div>
            <strong>本地演示账号</strong>
            <span>统一初始密码 Demo@2026 · 登录由后端真实校验并返回 JWT</span>
          </div>
        </div>

        <div
          class="role-list"
          role="radiogroup"
          aria-label="选择演示角色"
        >
          <button
            v-for="item in roleOptions"
            :key="item.key"
            type="button"
            class="role-card"
            :class="{ 'is-selected': selectedRole === item.key }"
            :aria-pressed="selectedRole === item.key"
            @click="selectRole(item.key)"
          >
            <span class="role-card__icon"><el-icon><component :is="roleIcons[item.key]" /></el-icon></span>
            <span class="role-card__text"><strong>{{ item.name }}</strong><small>{{ item.username }}</small></span>
            <span class="role-card__indicator" />
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
              :prefix-icon="User"
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
              :prefix-icon="Lock"
              @keyup.enter="enterPortal"
            />
          </el-form-item>
          <div
            v-if="loginError"
            class="login-error"
            role="alert"
          >
            {{ loginError }}
          </div>
          <el-button
            type="primary"
            size="large"
            native-type="submit"
            class="login-panel__submit"
            :loading="entering"
            :disabled="!username || !password"
          >
            <span>登录并进入{{ selectedRoleInfo.name }}工作台</span>
            <el-icon v-if="!entering">
              <Right />
            </el-icon>
          </el-button>
        </el-form>

        <div class="login-panel__footer">
          <router-link to="/">返回产品首页</router-link>
          <span />
          <router-link to="/system/status">检查服务连接</router-link>
        </div>
      </section>
    </div>

    <footer class="login-footer">
      <span><el-icon><Lock /></el-icon> 密钥不进入前端，账号权限由后端校验</span>
      <span>AI 评价仅作教学诊断参考，不等同于正式考试评分</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Connection, Lock, Reading, Right, Setting, User, UserFilled } from '@element-plus/icons-vue'

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
const roleIcons = {
  student: Reading,
  teacher: UserFilled,
  admin: Setting,
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
  min-height: 100svh;
  padding: 28px clamp(24px, 5vw, 76px) 22px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #ededf2;
  background:
    radial-gradient(circle at 75% 20%, rgba(99, 102, 241, 0.09), transparent 35%),
    radial-gradient(circle at 10% 85%, rgba(20, 184, 166, 0.07), transparent 30%),
    linear-gradient(145deg, #07090f 0%, #090b13 45%, #070a10 100%);
}

.login-page__grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.32;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.022) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.022) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(to bottom, black, transparent 90%);
}

.login-page__glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(4px);
  animation: breathe 9s ease-in-out infinite;
}

.login-page__glow--indigo {
  width: 560px;
  height: 560px;
  top: -250px;
  right: -100px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.16), transparent 68%);
}

.login-page__glow--teal {
  width: 460px;
  height: 460px;
  bottom: -240px;
  left: -160px;
  background: radial-gradient(circle, rgba(20, 184, 166, 0.11), transparent 68%);
  animation-delay: -4s;
}

.login-topbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.login-brand {
  display: inline-flex;
  align-items: center;
  gap: 11px;
}

.login-brand img {
  width: 40px;
  height: 40px;
  filter: drop-shadow(0 6px 16px rgba(99, 102, 241, 0.24));
}

.login-brand span {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.login-brand strong {
  font-size: 16px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.login-brand small {
  color: #8a91a3;
  font-size: 11px;
  letter-spacing: 0.12em;
}

.status-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  color: #a8afbf;
  background: rgba(255, 255, 255, 0.025);
  font-size: 12px;
  transition: color 180ms ease, border-color 180ms ease, background 180ms ease;
}

.status-link:hover {
  color: #ededf2;
  border-color: rgba(129, 140, 248, 0.35);
  background: rgba(99, 102, 241, 0.07);
}

.status-link__arrow {
  font-size: 11px;
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(1240px, 100%);
  margin: auto;
  padding: 54px 0 42px;
  display: grid;
  grid-template-columns: minmax(0, 1.06fr) minmax(390px, 0.82fr);
  gap: clamp(48px, 7vw, 96px);
  align-items: center;
}

.login-intro {
  max-width: 650px;
}

.intro-kicker {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0 0 22px;
  color: #9ca3af;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.2em;
}

.intro-kicker span {
  width: 24px;
  height: 1px;
  background: linear-gradient(90deg, #818cf8, #2dd4bf);
  box-shadow: 0 0 12px rgba(129, 140, 248, 0.5);
}

.login-intro h1 {
  margin: 0;
  color: #f1f1f5;
  font-size: clamp(32px, 3.35vw, 48px);
  font-weight: 620;
  line-height: 1.42;
  letter-spacing: -0.035em;
}

.login-intro h1 span {
  color: #c7c9ff;
  background: linear-gradient(105deg, #e2e3ff 10%, #a5b4fc 55%, #99f6e4 110%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.intro-lead {
  max-width: 590px;
  margin: 24px 0 0;
  color: #969eac;
  font-size: 14px;
  line-height: 1.95;
}

.feature-list {
  margin-top: 36px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.feature-item {
  padding: 16px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.022), transparent);
}

.feature-item__number {
  display: block;
  margin-bottom: 14px;
  color: #818cf8;
  font-family: Consolas, monospace;
  font-size: 11px;
  letter-spacing: 0.08em;
}

.feature-item h2 {
  margin: 0 0 7px;
  color: #dcdfe8;
  font-size: 14px;
  font-weight: 600;
}

.feature-item p {
  margin: 0;
  color: #838c9c;
  font-size: 11px;
  line-height: 1.8;
}

.growth-path {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 32px;
  color: #8e97a8;
  font-size: 11px;
}

.growth-path i {
  width: 20px;
  height: 1px;
  background: rgba(129, 140, 248, 0.3);
}

.login-panel {
  position: relative;
  padding: 30px;
  border: 1px solid rgba(255, 255, 255, 0.095);
  border-radius: 20px;
  background: linear-gradient(145deg, rgba(18, 22, 34, 0.88), rgba(11, 14, 23, 0.78));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.36), 0 0 0 1px rgba(99, 102, 241, 0.025) inset;
  backdrop-filter: blur(22px);
  overflow: hidden;
}

.login-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  background: linear-gradient(120deg, rgba(255, 255, 255, 0.035), transparent 28%);
}

.login-panel__shimmer {
  position: absolute;
  z-index: 1;
  top: 0;
  left: -35%;
  width: 35%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(165, 180, 252, 0.8), rgba(153, 246, 228, 0.55), transparent);
  animation: shimmer 7s ease-in-out infinite;
}

.login-panel__head,
.demo-note,
.role-list,
.login-form,
.login-panel__footer {
  position: relative;
  z-index: 2;
}

.panel-eyebrow {
  display: block;
  margin-bottom: 9px;
  color: #818cf8;
  font-size: 10px;
  font-weight: 650;
  letter-spacing: 0.19em;
}

.login-panel__head h2 {
  margin: 0;
  color: #f0f0f4;
  font-size: 24px;
  font-weight: 620;
  letter-spacing: -0.025em;
}

.login-panel__head p {
  margin: 9px 0 0;
  color: #8d96a7;
  font-size: 12px;
}

.demo-note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 22px 0 18px;
  padding: 11px 12px;
  border: 1px solid rgba(129, 140, 248, 0.12);
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.055);
  color: #9ca7c6;
}

.demo-note > .el-icon {
  margin-top: 2px;
  color: #a5b4fc;
}

.demo-note div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.demo-note strong {
  color: #c7cce0;
  font-size: 11px;
  font-weight: 600;
}

.demo-note span {
  font-size: 10px;
  line-height: 1.65;
}

.role-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.role-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  padding: 12px;
  text-align: left;
  border: 1px solid rgba(255, 255, 255, 0.075);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.022);
  color: #a7afbf;
  cursor: pointer;
  transition: border-color 180ms ease, background 180ms ease, transform 180ms ease;
}

.role-card:hover {
  transform: translateY(-2px);
  border-color: rgba(129, 140, 248, 0.3);
  background: rgba(99, 102, 241, 0.055);
}

.role-card.is-selected {
  border-color: rgba(129, 140, 248, 0.58);
  background: linear-gradient(145deg, rgba(99, 102, 241, 0.14), rgba(99, 102, 241, 0.055));
  color: #e1e4f5;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.1);
}

.role-card__icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  font-size: 15px;
}

.role-card.is-selected .role-card__icon {
  color: #b6bcff;
  background: rgba(129, 140, 248, 0.14);
}

.role-card__text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.role-card__text strong {
  font-size: 12px;
  font-weight: 600;
}

.role-card__text small {
  max-width: 100%;
  color: #788398;
  font-size: 9px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.role-card__indicator {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: transparent;
}

.role-card.is-selected .role-card__indicator {
  background: #a5b4fc;
  box-shadow: 0 0 9px rgba(165, 180, 252, 0.75);
}

.login-form {
  margin-top: 20px;
}

.login-form :deep(.el-form-item__label) {
  color: #aab2c2;
  font-size: 11px;
  font-weight: 500;
}

.login-form :deep(.el-input__wrapper) {
  border: 1px solid rgba(255, 255, 255, 0.085);
  border-radius: 10px;
  background: rgba(3, 6, 12, 0.36);
  box-shadow: none;
  transition: border-color 180ms ease, box-shadow 180ms ease, background 180ms ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: rgba(129, 140, 248, 0.32);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: rgba(129, 140, 248, 0.72);
  background: rgba(3, 6, 12, 0.52);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

.login-form :deep(.el-input__inner),
.login-form :deep(.el-input__inner::placeholder) {
  color: #e4e7ef;
  font-size: 12px;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #626d80;
}

.login-form :deep(.el-input__prefix),
.login-form :deep(.el-input__suffix) {
  color: #737f96;
}

.login-error {
  margin: -2px 0 14px;
  padding: 10px 12px;
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: 9px;
  background: rgba(248, 113, 113, 0.07);
  color: #fca5a5;
  font-size: 11px;
  line-height: 1.65;
}

.login-panel__submit {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid rgba(165, 180, 252, 0.3);
  border-radius: 10px;
  background: linear-gradient(105deg, #5457c9, #6366f1 58%, #4f46e5);
  box-shadow: 0 10px 26px rgba(79, 70, 229, 0.23), 0 0 18px rgba(99, 102, 241, 0.1);
  font-size: 12px;
  font-weight: 600;
  transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
}

.login-panel__submit:hover {
  transform: translateY(-1px);
  filter: brightness(1.08);
  box-shadow: 0 14px 32px rgba(79, 70, 229, 0.3), 0 0 22px rgba(99, 102, 241, 0.16);
}

.login-panel__submit:active {
  transform: translateY(0);
}

.login-panel__footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 13px;
  margin-top: 19px;
  color: #7f899c;
  font-size: 11px;
}

.login-panel__footer a:hover {
  color: #c4c9ff;
}

.login-panel__footer > span {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #485165;
}

.login-footer {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  color: #626d7f;
  font-size: 10px;
}

.login-footer span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.login-brand:focus-visible,
.status-link:focus-visible,
.role-card:focus-visible,
.login-panel__footer a:focus-visible,
.login-footer a:focus-visible {
  outline: 2px solid #818cf8;
  outline-offset: 4px;
}

@keyframes shimmer {
  0%, 15% { transform: translateX(0); opacity: 0; }
  35% { opacity: 1; }
  65% { opacity: 1; }
  85%, 100% { transform: translateX(390%); opacity: 0; }
}

@keyframes breathe {
  0%, 100% { opacity: 0.65; transform: scale(0.97); }
  50% { opacity: 1; transform: scale(1.04); }
}

@media (max-width: 1080px) {
  .login-shell {
    width: min(620px, 100%);
    grid-template-columns: 1fr;
    gap: 30px;
    padding-top: 44px;
  }

  .login-intro {
    max-width: none;
    text-align: center;
  }

  .intro-kicker,
  .growth-path {
    justify-content: center;
  }

  .intro-lead {
    margin-left: auto;
    margin-right: auto;
  }

  .feature-list {
    display: none;
  }

  .growth-path {
    margin-top: 22px;
  }
}

@media (max-width: 620px) {
  .login-page {
    padding: 20px 16px 18px;
    overflow: auto;
  }

  .status-link span:not(.status-link__arrow) {
    display: none;
  }

  .login-shell {
    padding: 34px 0 28px;
  }

  .login-intro h1 {
    font-size: 29px;
  }

  .intro-lead {
    font-size: 12px;
  }

  .growth-path {
    gap: 7px;
    font-size: 9px;
  }

  .growth-path i {
    width: 10px;
  }

  .login-panel {
    padding: 22px 18px;
    border-radius: 16px;
  }

  .login-panel__head h2 {
    font-size: 21px;
  }

  .role-list {
    gap: 6px;
  }

  .role-card {
    padding: 10px 8px;
  }

  .role-card__text small {
    display: none;
  }

  .login-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 7px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-page__glow,
  .login-panel__shimmer {
    animation: none;
  }

  .role-card,
  .login-panel__submit,
  .status-link {
    transition: none;
  }

  .role-card:hover,
  .login-panel__submit:hover {
    transform: none;
  }
}
</style>