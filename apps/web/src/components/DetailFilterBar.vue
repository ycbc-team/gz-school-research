<script setup lang="ts">
defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();
</script>

<template>
  <div class="detail-filter-bar">
    <slot name="buttons" />
    <div v-if="open" class="filter-pop"><slot /></div>
  </div>
  <div v-if="open" class="filter-mask" @click="emit('close')" />
</template>

<style scoped>
.detail-filter-bar { position: sticky; top: 65px; z-index: 1200; display: flex; gap: 8px; margin: 0 0 16px; padding: 8px; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; }
.detail-filter-bar :deep(.fb-col) { flex: 1 1 0; min-width: 0; }.detail-filter-bar :deep(.fb-btn) { width: 100%; border: 0; background: transparent; color: #1a1b1c; padding: 8px 4px; border-radius: 9px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px; font-size: 13px; white-space: nowrap; }.detail-filter-bar :deep(.fb-btn:hover),.detail-filter-bar :deep(.fb-btn.on) { background: #eaf1fe; color: #1a6bd6; font-weight: 600; }.detail-filter-bar :deep(.arr){color:#8a93a3;font-size:10px}.detail-filter-bar :deep(.fb-badge){background:#1a6bd6;color:#fff;border-radius:9px;padding:0 6px;font-size:10.5px;font-style:normal;line-height:15px}
.filter-pop { position:absolute; top:calc(100% + 6px); left:8px; right:8px; z-index:1300; padding:12px; border:1px solid #e4e3dd; border-radius:12px; background:#fff; box-shadow:0 8px 28px rgba(20,30,50,.16); }
.detail-filter-bar :deep(.pop-group) { margin-bottom: 10px; }.detail-filter-bar :deep(.pop-group:last-of-type) { margin-bottom: 0; }
.detail-filter-bar :deep(.pop-group-title) { margin: 12px 0 6px; color: #6b7280; font-size: 11.5px; font-weight: 600; }.detail-filter-bar :deep(.pop-group-title:first-child) { margin-top: 0; }
.detail-filter-bar :deep(.pop-chips) { display:flex; flex-wrap:wrap; gap:6px; }.detail-filter-bar :deep(.pop-chip) { border:1px solid #d6d4cc; border-radius:16px; background:#fff; padding:5px 12px; color:#1a1b1c; font-size:12.5px; cursor:pointer; }.detail-filter-bar :deep(.pop-chip.on) { border-color:#1a6bd6; background:#1a6bd6; color:#fff; }
.detail-filter-bar :deep(.pop-foot) { display:flex; justify-content:space-between; margin-top:10px; padding-top:8px; border-top:1px dashed #e4e3dd; }.detail-filter-bar :deep(.pop-link) { border:0; background:none; color:#1a6bd6; padding:4px 8px; font-size:12.5px; cursor:pointer; }
.filter-mask { position:fixed; inset:0; z-index:1100; background:rgba(0,0,0,.02); }
@media(max-width:600px){.detail-filter-bar{top:58px;gap:3px;padding:6px}.detail-filter-bar :deep(.fb-btn){padding:7px 1px;font-size:11.5px}}
</style>
