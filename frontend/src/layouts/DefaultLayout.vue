<template>
  <div class="layout">
    <header class="layout-header">
      <div class="layout-header__inner">
        <router-link
          class="brand"
          to="/"
        >
          <img
            class="brand__logo"
            src="@/assets/logo.svg"
            alt="WenMind AI"
          >
          <span class="brand__text">
            <strong>WenMind AI</strong>
            <small>文思智评</small>
          </span>
        </router-link>

        <nav class="layout-nav">
          <router-link
            class="layout-nav__item"
            to="/"
            exact-active-class="is-active"
          >首页</router-link>
          <router-link
            class="layout-nav__item"
            to="/system/status"
            active-class="is-active"
          >
            后端连接测试
          </router-link>
        </nav>

        <el-tag
          size="small"
          effect="plain"
          type="info"
        >
          V1.0 · 阶段 1 工程骨架
        </el-tag>
      </div>
    </header>

    <main class="layout-main">
      <router-view />
    </main>

    <footer class="layout-footer">
      <span>让每一次作文评价，都成为下一次写作成长的起点。</span>
      <span class="wm-muted">AI 评价为教学诊断性参考，不等同于高考正式阅卷分数。</span>
    </footer>
  </div>
</template>

<script setup>
</script>

<style scoped>
.layout {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.layout-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--wm-border);
}

.layout-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 28px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand__logo {
  width: 38px;
  height: 38px;
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.brand__text strong {
  font-size: 16px;
  letter-spacing: 0.2px;
}

.brand__text small {
  color: var(--wm-text-secondary);
  font-size: 12px;
}

.layout-nav {
  display: flex;
  gap: 6px;
  flex: 1;
}

.layout-nav__item {
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 14px;
  color: var(--wm-text-secondary);
  transition: all 0.2s ease;
}

.layout-nav__item:hover {
  color: var(--wm-primary);
  background: #eef3ff;
}

.layout-nav__item.is-active {
  color: var(--wm-primary);
  background: #e6eeff;
  font-weight: 600;
}

.layout-main {
  flex: 1;
}

.layout-footer {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 20px 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--wm-text-secondary);
}
</style>