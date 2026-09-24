<script setup lang="ts">
withDefaults(defineProps<{ title: string; subtitle?: string }>(), { subtitle: '' });
</script>

<template>
  <header class="detail-page-header">
    <RouterLink to="/" class="back">‹ 首页</RouterLink>
    <div>
      <h1>{{ title }}</h1>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
  </header>
</template>

<style scoped>
.detail-page-header { display: flex; flex-direction: column; gap: 8px; margin: 4px 0 14px; }
.back { width: fit-content; color: #1a6bd6; font-size: 13px; line-height: 20px; text-decoration: none; }
.back:hover { text-decoration: underline; }
h1 { margin: 0; color: #1a1b1c; font-size: 20px; line-height: 1.35; }
p { margin: 4px 0 0; color: #6b7280; font-size: 12px; line-height: 1.65; }
</style>
