<script setup lang="ts" generic="T">
defineProps<{
  groups: readonly T[];
  groupKey: (group: T, index: number) => string;
}>();
</script>

<template>
  <main class="detail-ranking-list">
    <section v-for="(group, index) in groups" :key="groupKey(group, index)" class="ranking-group">
      <slot name="heading" :group="group" />
      <div class="table-wrap"><slot :group="group" /></div>
    </section>
  </main>
</template>

<style scoped>
.detail-ranking-list { display: flex; flex-direction: column; gap: 16px; }
.ranking-group { overflow: hidden; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; }
.table-wrap { overflow-x: auto; }
/* 三个明细页共同的学校链接字形；各页只保留列宽和业务标签的差异。 */
.detail-ranking-list :deep(.school-link), .detail-ranking-list :deep(.school a) { color: #1a6bd6; font-weight: 600; text-decoration: none; }
.detail-ranking-list :deep(.school-link:hover), .detail-ranking-list :deep(.school a:hover) { text-decoration: underline; }
@media (max-width: 600px) { .table-wrap { overflow-x: visible; } }
</style>
