<template>
  <div
    class="portal"
    :class="{ 'is-collapsed': collapsed }"
  >
    <aside class="portal-aside">
      <router-link
        class="portal-brand"
        :to="authStore.homePath"
      >
        <img
          src="@/assets/logo.svg"
          alt="WenMind AI"
          class="portal-brand__logo"
        >
        <transition name="fade">
          <span
            v-if="!collapsed"
            class="portal-brand__text"
          >
            <strong>WenMind AI</strong>
            <small>文思智评 · {{ authStore.roleInfo?.name }}端</small>
          </span>
        </transition>
      </router-link>

      <el-scrollbar class="portal-aside__scroll">
        <el-menu
          :default-active="route.path"
          :collapse="collapsed"
          :collapse-transition="false"
          router
          class="portal-menu"
        >
          <template
            v-for="group in groupedNavigation"
            :key="group.name"
          >
            <div
              v-if="!collapsed"
              class="portal-menu__group"
            >
              {{ group.name }}
            </div>
            <el-menu-item
              v-for="item in group.items"
              :key="item.path"
              :index="item.path"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <template #title>
                {{ item.title }}
              </template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div class="portal-aside__footer">
        <el-button
          text
          class="collapse-button"
          @click="collapsed = !collapsed"
        >
          <el-icon><Expand v-if="collapsed" /><Fold v-else /></el-icon>
          <span v-if="!collapsed">收起导航</span>
        </el-button>
      </div>
    </aside>

    <div class="portal-body">
      <header class="portal-header">
        <div class="portal-header__left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="authStore.homePath">
              {{ authStore.roleInfo?.name }}端
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">
              {{ route.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="portal-header__right">
          <DemoSessionTag />
          <el-tooltip
            content="后端连接测试"
            placement="bottom"
          >
            <el-button
              text
              circle
              @click="goSystemStatus"
            >
              <el-icon :size="18">
                <Link />
              </el-icon>
            </el-button>
          </el-tooltip>
          <el-dropdown
            trigger="click"
            @command="handleUserCommand"
          >
            <button
              class="user-entry"
              type="button"
            >
              <span class="user-entry__avatar">{{ avatarText }}</span>
              <span class="user-entry__info">
                <strong>{{ authStore.displayName }}</strong>
                <small>{{ authStore.roleInfo?.englishName }}</small>
              </span>
              <el-icon><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  演示角色：{{ authStore.roleInfo?.name }}
                </el-dropdown-item>
                <el-dropdown-item
                  command="switch"
                  :icon="Switch"
                >
                  切换演示角色
                </el-dropdown-item>
                <el-dropdown-item
                  command="logout"
                  :icon="SwitchButton"
                  divided
                >
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="portal-main">
        <router-view v-slot="{ Component }">
          <transition
            name="page-fade"
            mode="out-in"
          >
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ArrowDown, Expand, Fold, Link, Switch, SwitchButton } from '@element-plus/icons-vue'

import DemoSessionTag from '@/components/DemoSessionTag.vue'
import { NAVIGATIONS } from '@/config/portal'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

const groupedNavigation = computed(() => {
  const items = NAVIGATIONS[authStore.role] || []
  const groups = []
  items.forEach((item) => {
    let group = groups.find((entry) => entry.name === item.group)
    if (!group) {
      group = { name: item.group, items: [] }
      groups.push(group)
    }
    group.items.push(item)
  })
  return groups
})

const avatarText = computed(() => authStore.roleInfo?.name?.slice(0, 1) || '访')

function goSystemStatus() {
  router.push('/system/status')
}

async function handleUserCommand(command) {
  if (command === 'switch') {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('退出后将清除当前演示角色会话，需要重新选择角色进入。', '确认退出登录', {
        confirmButtonText: '退出登录',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
    authStore.logout()
    router.push({ name: 'login' })
  }
}
</script>

<style scoped>
.portal {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  background: var(--wm-bg);
  transition: grid-template-columns 0.2s ease;
}

.portal.is-collapsed {
  grid-template-columns: 68px minmax(0, 1fr);
}

.portal-aside {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(24, 33, 75, 0.98), rgba(35, 42, 92, 0.96));
  color: #e5e9ff;
  overflow: hidden;
}

.portal-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 68px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.portal-brand__logo {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}

.portal-brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
  white-space: nowrap;
}

.portal-brand__text strong {
  font-size: 15px;
}

.portal-brand__text small {
  font-size: 11px;
  color: #b7c0e8;
}

.portal-aside__scroll {
  flex: 1;
}

.portal-menu {
  border-right: none;
  background: transparent;
  padding: 10px 8px;
  --el-menu-text-color: #c3cbea;
  --el-menu-hover-text-color: #ffffff;
  --el-menu-active-color: #ffffff;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.08);
  --el-menu-item-height: 44px;
}

.portal-menu:not(.el-menu--collapse) {
  width: 100%;
}

.portal-menu__group {
  padding: 16px 12px 6px;
  font-size: 11px;
  color: #8f9bc9;
  letter-spacing: 1px;
}

.portal-menu :deep(.el-menu-item) {
  border-radius: 10px;
  margin-bottom: 4px;
}

.portal-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.9), rgba(59, 130, 246, 0.65));
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.22);
}

.portal-aside__footer {
  padding: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.collapse-button {
  width: 100%;
  color: #c3cbea;
}

.portal-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.portal-header {
  position: sticky;
  top: 0;
  z-index: 20;
  min-height: 68px;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--wm-border);
}

.portal-header__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-entry {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 8px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  cursor: pointer;
  color: var(--wm-text-main);
}

.user-entry:hover {
  background: var(--wm-bg-soft);
  border-color: var(--wm-border);
}

.user-entry__avatar {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  font-weight: 600;
  background: linear-gradient(135deg, var(--wm-primary), var(--wm-primary-soft));
}

.user-entry__info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.3;
}

.user-entry__info strong {
  font-size: 13px;
}

.user-entry__info small {
  font-size: 11px;
  color: var(--wm-text-secondary);
}

.portal-main {
  flex: 1;
  width: 100%;
  max-width: 1500px;
  margin: 0 auto;
  padding: 24px;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 1100px) {
  .portal {
    grid-template-columns: 68px minmax(0, 1fr);
  }

  .portal-aside {
    width: 68px;
  }

  .portal-brand__text,
  .portal-menu__group,
  .collapse-button span {
    display: none;
  }

  .portal-main {
    padding: 18px;
  }

  .user-entry__info {
    display: none;
  }
}
</style>