<script setup lang="ts">
import { computed, ref } from 'vue';
import { VERDICT_LABEL } from '@gz/shared';
import { tier1Schools, middleTier1Schools } from '../data';

const stage = ref<'primary' | 'middle'>('primary');
const list = computed(() =>
  stage.value === 'primary' ? tier1Schools : middleTier1Schools,
);

const verdictBadge: Record<string, string> = {
  有支撑: '#2f7d1f',
  部分支撑: '#b07d1f',
  不支撑: '#c9534f',
};

const summary = computed(() => {
  const by: Record<string, number> = { 有支撑: 0, 部分支撑: 0, 不支撑: 0 };
  for (const s of list.value) by[s.conclusion] = (by[s.conclusion] ?? 0) + 1;
  return by;
});
</script>

<template>
  <section>
    <div class="toolbar">
      <button class="chip" :class="{ active: stage === 'primary' }" @click="stage = 'primary'">
        小学 {{ tier1Schools.length }} 所
      </button>
      <button class="chip" :class="{ active: stage === 'middle' }" @click="stage = 'middle'">
        初中 {{ middleTier1Schools.length }} 所
      </button>
      <span class="summary">
        有支撑 {{ summary['有支撑'] }} · 部分支撑 {{ summary['部分支撑'] }} · 不支撑 {{ summary['不支撑'] }}
      </span>
    </div>

    <div class="cards">
      <article v-for="s in list" :key="s.name" class="card">
        <header class="card-head">
          <h2>{{ s.name }}</h2>
          <span class="badge" :style="{ background: verdictBadge[s.conclusion] }">
            {{ VERDICT_LABEL[s.conclusion] }}
          </span>
        </header>
        <p class="tier">民间标签：{{ s.rumor_tier }}<template v-if="s.rumor_notes"> · {{ s.rumor_notes.slice(0, 40) }}</template></p>
        <p v-if="s.conclusion_basis" class="basis">{{ s.conclusion_basis }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 14px; }
.chip {
  border: 1px solid #d6d4cc; background: #fff; color: #1a1b1c;
  border-radius: 999px; padding: 6px 14px; font-size: 13px; cursor: pointer;
}
.chip.active { background: #3a5396; border-color: #3a5396; color: #fff; }
.summary { font-size: 12px; color: #6b7280; margin-left: 8px; }

.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.card { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 14px 16px; }
.card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.card-head h2 { font-size: 14px; font-weight: 600; line-height: 1.45; }
.badge {
  flex: 0 0 auto; color: #fff; font-size: 11px; font-weight: 600;
  border-radius: 999px; padding: 2px 10px;
}
.tier { font-size: 12px; color: #6b7280; margin-top: 8px; line-height: 1.6; }
.basis { font-size: 12px; color: #444; margin-top: 6px; line-height: 1.6; }
</style>
