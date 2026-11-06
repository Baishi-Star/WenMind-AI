<template>
  <div class="page-header">
    <div class="page-header__main">
      <div class="page-header__title-row">
        <h1 class="page-header__title">
          {{ title }}
        </h1>
        <slot name="tag" />
      </div>
      <p
        v-if="subtitle"
        class="page-header__subtitle"
      >
        {{ subtitle }}
      </p>
    </div>
    <div
      v-if="$slots.actions"
      class="page-header__actions"
    >
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}

.page-header__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.page-header__title {
  margin: 0;
  font-size: 23px;
  font-weight: 650;
  letter-spacing: 0.2px;
}

.page-header__subtitle {
  margin: 8px 0 0;
  max-width: 860px;
  color: var(--wm-text-secondary);
  font-size: 13px;
  line-height: 1.8;
}

.page-header__actions {
  flex-shrink: 0;
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
  }
}
</style>