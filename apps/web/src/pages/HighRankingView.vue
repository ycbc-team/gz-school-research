<script setup lang="ts">
/** UI only: 高中明细的行、分组、录取线口径与排序均由 @gz/shared ViewModel 提供。 */
import { computed, ref } from 'vue';
import { buildHighRankingGroups, type HighRankingGroupBy } from '@gz/shared';
import { highLevels, highSchools, highScores2025, highScores2026 } from '../data';

const groupBy = ref<HighRankingGroupBy>('affiliation');
const groups = computed(() => buildHighRankingGroups({ highSchools, highLevels, highScores2025, highScores2026 }, groupBy.value));

function shortName(name: string): string {
  const n = name.trim();
  if (n.startsWith('广州市')) return n.slice(3);
  if (n.startsWith('广东')) return n.slice(2);
  if (n.startsWith('广州')) {
    const rest = n.slice(2);
    if (rest.length >= 3 && !rest.startsWith('大学')) return rest;
  }
  return n;
}
</script>

<template>
  <div class="page">
    <header class="top">
      <RouterLink to="/" class="back">‹ 首页</RouterLink>
      <h1 class="page-title">广州七区高中明细</h1>
      <p class="intro">收录高中校区点位；每组内按 2026 年中考录取线降序。公办以户籍生分数排序，民办/中外合作以最低分排序；同校区多招生条目取最高主分数。</p>
    </header>

    <div class="filter-bar" aria-label="分组方式">
      <button class="filter" :class="{ on: groupBy === 'affiliation' }" @click="groupBy = 'affiliation'">按省属/市属/区属</button>
      <button class="filter" :class="{ on: groupBy === 'district' }" @click="groupBy = 'district'">按位置所在行政区</button>
    </div>

    <main class="rank-body">
      <section v-for="group in groups" :key="group.key" class="rank-group">
        <h2>{{ group.title }}<em>{{ group.items.length }} 个校区</em></h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>学校 / 校区</th><th>分类</th><th>2025 中考录取线</th><th>2026 中考录取线 ↓</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in group.items" :key="row.schoolId || row.name">
                <td class="school">
                  <RouterLink :to="{ path: '/school/' + encodeURIComponent(row.name), query: { stage: 'high', ...(row.schoolId ? { id: row.schoolId } : {}) } }">{{ shortName(row.name) }}</RouterLink>
                  <span class="district">{{ row.district }}</span>
                </td>
                <td class="category">{{ row.category }}</td>
                <td class="score"><span v-if="!row.score2025.length" class="empty">—</span><span v-for="(score, index) in row.score2025" :key="index" class="score-line">{{ score.text }}</span></td>
                <td class="score current"><span v-if="!row.score2026.length" class="empty">—</span><span v-for="(score, index) in row.score2026" :key="index" class="score-line">{{ score.text }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <footer>数据来源：广州市招考办 2025、2026 年普通高中招生录取分数表。录取线按官方批次与招生口径原样列示。</footer>
  </div>
</template>

<style scoped>
.page { max-width: 1180px; margin: 0 auto; }
.top { display: flex; flex-direction: column; gap: 7px; }
.back, .school a { color: #1a6bd6; text-decoration: none; }
.back { font-size: 13px; }.back:hover, .school a:hover { text-decoration: underline; }
.page-title { font-size: 20px; }.intro, footer { font-size: 12px; color: #6b7280; line-height: 1.65; }
.filter-bar { position: sticky; top: 65px; z-index: 10; display: flex; gap: 8px; margin: 15px 0; padding: 8px; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; }
.filter { border: 1px solid #d6d4cc; border-radius: 18px; background: #fff; color: #1a1b1c; padding: 6px 13px; font-size: 13px; cursor: pointer; }
.filter.on { background: #1a6bd6; border-color: #1a6bd6; color: #fff; }
.rank-body { display: flex; flex-direction: column; gap: 16px; }
.rank-group { overflow: hidden; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; }
h2 { padding: 12px 14px 8px; font-size: 15px; } h2 em { margin-left: 8px; color: #8a93a3; font-size: 11.5px; font-style: normal; font-weight: 400; }
.table-wrap { overflow-x: auto; } table { width: 100%; min-width: 760px; border-collapse: collapse; font-size: 12.5px; }
th { padding: 7px 10px; color: #6b7280; font-size: 11.5px; text-align: left; border-bottom: 1px solid #ecebe6; } td { padding: 8px 10px; vertical-align: top; border-bottom: 1px solid #f2f1ec; } tbody tr:last-child td { border: 0; } tbody tr:hover { background: #fafbfc; }
.school { min-width: 180px; font-weight: 600; }.district { display: block; margin-top: 3px; color: #8a93a3; font-size: 11px; font-weight: 400; }.category { color: #6b7280; white-space: nowrap; }.score { min-width: 220px; color: #4b5563; font-variant-numeric: tabular-nums; }.current { color: #1a1b1c; font-weight: 600; }.score-line { display: block; line-height: 1.65; }.empty { color: #9ca3af; } footer { margin: 18px 2px 30px; }
@media (max-width: 600px) { .filter-bar { top: 58px; }.filter { flex: 1; padding: 7px 5px; font-size: 12px; } }
</style>
