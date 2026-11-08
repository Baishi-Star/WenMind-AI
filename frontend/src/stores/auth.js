import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { login as loginRequest } from '@/api/auth'
import { getRoleHome, ROLES } from '@/config/portal'

const TOKEN_KEY = 'wenmind_token'
const SESSION_KEY = 'wenmind_auth_session'
const LEGACY_SESSION_KEY = 'wenmind_demo_session'

function readSession() {
  try {
    if (!localStorage.getItem(TOKEN_KEY)) return null
    const session = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null')
    return ROLES[session?.user?.role] ? session : null
  } catch {
    localStorage.removeItem(SESSION_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const session = ref(readSession())

  const isDemoSession = computed(() => Boolean(session.value?.user?.is_demo))
  const isAuthenticated = computed(() => Boolean(session.value?.user?.role && localStorage.getItem(TOKEN_KEY)))
  const role = computed(() => session.value?.user?.role || '')
  const roleInfo = computed(() => ROLES[role.value] || null)
  const displayName = computed(() => session.value?.user?.display_name || '访客')
  const homePath = computed(() => getRoleHome(role.value))

  async function login(username, password) {
    const response = await loginRequest({ username, password })
    const { access_token: accessToken, user } = response.data
    localStorage.setItem(TOKEN_KEY, accessToken)
    session.value = { user, loginAt: new Date().toISOString() }
    localStorage.setItem(SESSION_KEY, JSON.stringify(session.value))
    localStorage.removeItem(LEGACY_SESSION_KEY)
    return getRoleHome(user.role)
  }

  function logout() {
    session.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(SESSION_KEY)
    localStorage.removeItem(LEGACY_SESSION_KEY)
  }

  return {
    session,
    isDemoSession,
    isAuthenticated,
    role,
    roleInfo,
    displayName,
    homePath,
    login,
    logout,
  }
})