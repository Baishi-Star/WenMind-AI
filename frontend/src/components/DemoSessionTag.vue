<template>
  <el-tooltip
    content="当前为前端演示角色会话，用于界面与路由演示；后端账号密码认证将在后续阶段接入。"
    placement="bottom"
  >
    <span class="demo-tag">
      <span class="demo-tag__dot" />
      演示会话 · 后端认证待接入
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