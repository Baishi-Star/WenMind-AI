import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getRoleHome, ROLES } from '@/config/portal'

const SESSION_KEY = 'wenmind_demo_session'

function readSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const session = JSON.parse(raw)
    return ROLES[session.role] ? session : null
  } catch {
    localStorage.removeItem(SESSION_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const session = ref(readSession())

  // 当前阶段为前端演示角色会话，后端 JWT 认证接入后此标识会移除
  const isDemoSession = computed(() => Boolean(session.value))
  const isAuthenticated = computed(() => Boolean(session.value?.role))
  const role = computed(() => session.value?.role || '')
  const roleInfo = computed(() => ROLES[role.value] || null)
  const displayName = computed(() => roleInfo.value?.demoName || '访客')
  const homePath = computed(() => getRoleHome(role.value))

  function loginAsRole(nextRole) {
    if (!ROLES[nextRole]) {
      throw new Error('不支持的演示角色')
    }
    session.value = {
      role: nextRole,
      mode: 'demo',
      loginAt: new Date().toISOString(),
    }
    localStorage.setItem(SESSION_KEY, JSON.stringify(session.value))
    return getRoleHome(nextRole)
  }

  function logout() {
    session.value = null
    localStorage.removeItem(SESSION_KEY)
    // 后端认证接入前不遗留任何演示令牌
    localStorage.removeItem('wenmind_token')
  }

  return {
    session,
    isDemoSession,
    isAuthenticated,
    role,
    roleInfo,
    displayName,
    homePath,
    loginAsRole,
    logout,
  }
})