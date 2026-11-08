<template>
  <el-tooltip
    content="当前使用预置演示账号，但登录、JWT 和接口权限均由后端真实校验；业务操作会写入 SQLite。"
    placement="bottom"
  >
    <span class="demo-tag">
      <span class="demo-tag__dot" />
      演示账号 · 真实 JWT 已接入
    </span>
  </el-tooltip>
</template>

<script setup>
</script>

<style scoped>
.demo-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.28);
  color: #a16207;
  font-size: 12px;
  cursor: help;
  white-space: nowrap;
}

.demo-tag__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d97706;
}
</style>