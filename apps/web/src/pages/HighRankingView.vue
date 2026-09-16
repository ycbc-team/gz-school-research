<script setup lang="ts">
/** UI only: 高中明细的行、分组、录取线口径与排序均由 @gz/shared ViewModel 提供。 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { DISTRICTS, buildHighRankingGroups, type HighRankingGroupBy, type HighRankingSortBy } from '@gz/shared';
import { entities, highLevels, highSchools, highScores2025, highScores2026 } from '../data';

const openMenu = ref<'group' | 'affiliation' | 'district' | 'sort' | null>(null);
const groupBy = ref<HighRankingGroupBy>('none');
const selectedDistricts = ref(new Set(DISTRICTS.map((district) => district.adcode)));
const AFFILIATION_OPTIONS = [
  { label: '省市属', values: ['省属', '市属'] },
  ...DISTRICTS.map((district) => ({ label: `${district.name}属`, values: [`${district.name}属`] })),
  { label: '民办', values: ['民办'] },
];
const ALL_AFFILIATIONS = AFFILIATION_OPTIONS.flatMap((option) => option.values);
/** null 表示不限制，确保“全选”也包含未标注隶属的点位。 */
const selectedAffiliations = ref<Set<string> | null>(null);
const sortBy = ref<HighRankingSortBy>('score2026');
const groups = computed(() => buildHighRankingGroups(
  { highSchools, highLevels, highScores2025, highScores2026, entities },
  { groupBy: groupBy.value, districtAdcodes: [...selectedDistricts.value], affiliations: selectedAffiliations.value ? [...selectedAffiliations.value] : undefined, sortBy: sortBy.value },
));
const groupLabel = computed(() => ({ none: '不分组', category: '省市区属', district: '行政区位置' })[groupBy.value]);
const sortLabel = computed(() => ({ score2025: '2025 分', score2026: '2026 分', average: '历年平均分' })[sortBy.value]);
const districtAllOn = computed(() => selectedDistricts.value.size === DISTRICTS.length);
const affiliationAllOn = computed(() => selectedAffiliations.value === null);
function affiliationOn(values: string[]) {
  return affiliationAllOn.value || values.every((value) => selectedAffiliations.value!.has(value));
}
function toggleAffiliation(values: string[]) {
  const next = new Set(selectedAffiliations.value || ALL_AFFILIATIONS);
  const enabled = values.every((value) => next.has(value));
  values.forEach((value) => enabled ? next.delete(value) : next.add(value));
  selectedAffiliations.value = next;
}
function selectAllAffiliations() { selectedAffiliations.value = null; }
function selectNoAffiliations() { selectedAffiliations.value = new Set(); }
function toggleDistrict(adcode: string) {
  const next = new Set(selectedDistricts.value);
  next.has(adcode) ? next.delete(adcode) : next.add(adcode);
  selectedDistricts.value = next;
}
function flipDistricts() {
  selectedDistricts.value = districtAllOn.value ? new Set() : new Set(DISTRICTS.map((district) => district.adcode));
}
const showHint = ref(false);
const hintPos = ref({ top: 0, left: 0 });
let hintTimer: number | undefined;
const SCORE_NOTE = '第三批公办普通高中户籍生录取分数；不含第一、第四批次，以及非户籍生、外区生、民办和中外合作办学项目分数。';

/** 与初中明细一致：PopupWindow 锚定问号；悬停可读、点击可固定，滚动时收起。 */
function openHint(e: MouseEvent) {
  clearTimeout(hintTimer);
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const width = 330;
  hintPos.value = {
    top: rect.bottom + 6,
    left: Math.min(Math.max(8, rect.left), window.innerWidth - width - 8),
  };
  showHint.value = true;
}
function closeHint() { clearTimeout(hintTimer); showHint.value = false; }
function scheduleClose() { clearTimeout(hintTimer); hintTimer = window.setTimeout(closeHint, 160); }
function keepHint() { clearTimeout(hintTimer); }
function toggleHint(e: MouseEvent) { showHint.value ? closeHint() : openHint(e); }
onMounted(() => { window.addEventListener('scroll', closeHint, true); window.addEventListener('resize', closeHint); });
onBeforeUnmount(() => { window.removeEventListener('scroll', closeHint, true); window.removeEventListener('resize', closeHint); });

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
      <p class="intro">收录高中校区点位；录取线为第三批户籍生口径，当前按{{ sortLabel }}降序。</p>
    </header>

    <div class="filter-bar" aria-label="高中明细筛选器">
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'group' }" @click="openMenu = openMenu === 'group' ? null : 'group'">分组<em class="fb-badge">{{ groupLabel }}</em><span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'affiliation' }" @click="openMenu = openMenu === 'affiliation' ? null : 'affiliation'">隶属<em v-if="!affiliationAllOn" class="fb-badge">{{ selectedAffiliations?.size }}</em><span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'district' }" @click="openMenu = openMenu === 'district' ? null : 'district'">位置<em v-if="!districtAllOn" class="fb-badge">{{ selectedDistricts.size }}</em><span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'sort' }" @click="openMenu = openMenu === 'sort' ? null : 'sort'">排序<em class="fb-badge">{{ sortLabel }}</em><span class="arr">▾</span></button></div>

      <div v-if="openMenu === 'group'" class="fb-pop"><div class="pop-chips">
        <button class="pop-chip" :class="{ on: groupBy === 'none' }" @click="groupBy = 'none'">不分组</button>
        <button class="pop-chip" :class="{ on: groupBy === 'category' }" @click="groupBy = 'category'">按省市区属</button>
        <button class="pop-chip" :class="{ on: groupBy === 'district' }" @click="groupBy = 'district'">按行政区位置</button>
      </div><div class="pop-foot"><button class="pop-link" @click="openMenu = null">完成</button></div></div>
      <div v-if="openMenu === 'affiliation'" class="fb-pop"><div class="pop-chips">
        <button v-for="option in AFFILIATION_OPTIONS" :key="option.label" class="pop-chip" :class="{ on: affiliationOn(option.values) }" @click="toggleAffiliation(option.values)">{{ option.label }}</button>
      </div><div class="pop-foot"><button class="pop-link" @click="selectAllAffiliations">全选</button><button class="pop-link" @click="selectNoAffiliations">全不选</button><button class="pop-link" @click="openMenu = null">完成</button></div></div>
      <div v-if="openMenu === 'district'" class="fb-pop"><div class="pop-chips">
        <button v-for="district in DISTRICTS" :key="district.adcode" class="pop-chip" :class="{ on: selectedDistricts.has(district.adcode) }" @click="toggleDistrict(district.adcode)">{{ district.name }}</button>
      </div><div class="pop-foot"><button class="pop-link" @click="flipDistricts">{{ districtAllOn ? '取消全选' : '全选' }}</button><button class="pop-link" @click="openMenu = null">完成</button></div></div>
      <div v-if="openMenu === 'sort'" class="fb-pop"><div class="pop-chips">
        <button class="pop-chip" :class="{ on: sortBy === 'score2025' }" @click="sortBy = 'score2025'">按 2025 分排</button>
        <button class="pop-chip" :class="{ on: sortBy === 'score2026' }" @click="sortBy = 'score2026'">按 2026 分排</button>
        <button class="pop-chip" :class="{ on: sortBy === 'average' }" @click="sortBy = 'average'">按全部年份平均分排</button>
      </div><div class="pop-foot"><button class="pop-link" @click="openMenu = null">完成</button></div></div>
    </div>
    <div v-if="openMenu" class="pop-mask" @click="openMenu = null"></div>

    <main class="rank-body">
      <section v-for="group in groups" :key="group.key" class="rank-group">
        <h2 v-if="groupBy !== 'none'">{{ group.title }}<em>{{ group.items.length }} 个校区</em></h2>
        <div class="table-wrap">
          <table class="rank-table">
            <colgroup><col class="col-school"><col class="col-score"><col class="col-score"></colgroup>
            <thead>
              <tr>
                <th>学校 / 校区</th>
                <th><span class="desktop-label">2025 中考录取线</span><span class="mobile-label">2025 录取线</span> <button class="q-mark" :aria-label="SCORE_NOTE" @mouseenter="openHint" @mouseleave="scheduleClose" @click.stop="toggleHint">?</button></th>
                <th><span class="desktop-label">2026 中考录取线</span><span class="mobile-label">2026 录取线</span> <button class="q-mark" :aria-label="SCORE_NOTE" @mouseenter="openHint" @mouseleave="scheduleClose" @click.stop="toggleHint">?</button></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in group.items" :key="row.schoolId || row.name">
                <td class="school">
                  <RouterLink :to="{ path: '/school/' + encodeURIComponent(row.name), query: { stage: 'high', ...(row.schoolId ? { id: row.schoolId } : {}) } }">{{ shortName(row.name) }}</RouterLink>
                  <em v-if="row.minban" class="mb-tag">民办</em>
                  <span class="school-meta"><span>{{ row.district }}</span><span v-if="row.affiliation">{{ row.affiliation }}</span></span>
                </td>
                <td class="score"><span v-if="!row.score2025.length" class="empty">—</span><span v-for="(score, index) in row.score2025" :key="index" class="score-line">{{ score.text }}</span></td>
                <td class="score current"><span v-if="!row.score2026.length" class="empty">—</span><span v-for="(score, index) in row.score2026" :key="index" class="score-line">{{ score.text }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <footer>数据来源：广州市招考办 2025、2026 年普通高中招生录取分数表。{{ SCORE_NOTE }}</footer>
    <Teleport to="body"><div v-if="showHint" class="hint-pop" :style="{ top: hintPos.top + 'px', left: hintPos.left + 'px' }" @mouseenter="keepHint" @mouseleave="scheduleClose">{{ SCORE_NOTE }}</div></Teleport>
  </div>
</template>

<style scoped>
.page { max-width: 1180px; margin: 0 auto; }
.top { display: flex; flex-direction: column; gap: 7px; }
.back, .school a { color: #1a6bd6; text-decoration: none; }
.back { font-size: 13px; }.back:hover, .school a:hover { text-decoration: underline; }
.page-title { font-size: 20px; }.intro, footer { font-size: 12px; color: #6b7280; line-height: 1.65; }
.filter-bar { position: sticky; top: 65px; z-index: 1200; display: flex; gap: 8px; margin: 15px 0; padding: 8px; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; }
.fb-col { flex: 1 1 0; min-width: 0; }.fb-btn { width: 100%; border: none; background: transparent; color: #1a1b1c; padding: 8px 4px; border-radius: 9px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px; font-size: 13px; white-space: nowrap; }.fb-btn:hover { background: #f2f7ff; }.fb-btn.on { background: #eaf1fe; color: #1a6bd6; font-weight: 600; }.arr { color: #8a93a3; font-size: 10px; }.fb-badge { background: #1a6bd6; color: #fff; border-radius: 9px; padding: 0 6px; font-size: 10.5px; font-style: normal; line-height: 15px; }
.fb-pop { position: absolute; top: calc(100% + 6px); left: 8px; right: 8px; z-index: 1300; padding: 12px; border: 1px solid #e4e3dd; border-radius: 12px; background: #fff; box-shadow: 0 8px 28px rgba(20,30,50,.16); }.pop-chips { display: flex; flex-wrap: wrap; gap: 6px; }.pop-chip { border: 1px solid #d6d4cc; border-radius: 16px; background: #fff; padding: 5px 12px; color: #1a1b1c; font-size: 12.5px; cursor: pointer; }.pop-chip.on { border-color: #1a6bd6; background: #1a6bd6; color: #fff; }.pop-foot { display: flex; justify-content: space-between; margin-top: 10px; padding-top: 8px; border-top: 1px dashed #e4e3dd; }.pop-link { border: 0; background: none; color: #1a6bd6; padding: 4px 8px; font-size: 12.5px; cursor: pointer; }.pop-mask { position: fixed; inset: 0; z-index: 1100; background: rgba(0,0,0,.02); }
.rank-body { display: flex; flex-direction: column; gap: 16px; }
.rank-group { overflow: hidden; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; }
h2 { padding: 12px 14px 8px; font-size: 15px; } h2 em { margin-left: 8px; color: #8a93a3; font-size: 11.5px; font-style: normal; font-weight: 400; }
.table-wrap { overflow-x: auto; } table { width: 100%; min-width: 620px; border-collapse: collapse; font-size: 12.5px; }.rank-table { table-layout: fixed; }.col-school { width: 42%; }.col-score { width: 29%; }.mobile-label { display: none; }
th { padding: 7px 10px; color: #6b7280; font-size: 11.5px; text-align: left; border-bottom: 1px solid #ecebe6; } td { padding: 8px 10px; vertical-align: top; border-bottom: 1px solid #f2f1ec; } tbody tr:last-child td { border: 0; } tbody tr:hover { background: #fafbfc; }
.school { font-weight: 600; }.school-meta { display: flex; gap: 7px; margin-top: 3px; color: #8a93a3; font-size: 11px; font-weight: 400; }.school-meta span + span::before { content: '·'; margin-right: 7px; color: #c3c9d4; }.score { color: #4b5563; font-variant-numeric: tabular-nums; }.current { color: #1a1b1c; font-weight: 400; }.score-line { display: block; line-height: 1.65; }.empty { color: #9ca3af; } footer { margin: 18px 2px 30px; }
.mb-tag { display: inline-block; margin-left: 6px; padding: 0 5px; border: 1px solid #fde68a; border-radius: 8px; background: #fef3c7; color: #b45309; font-size: 10.5px; font-style: normal; font-weight: 400; line-height: 15px; vertical-align: 1px; }
.q-mark { display: inline-flex; align-items: center; justify-content: center; width: 15px; height: 15px; margin-left: 3px; padding: 0; border: 1px solid #c3c9d4; border-radius: 50%; background: #fff; color: #6b7280; font-size: 10px; cursor: help; vertical-align: 1px; }.q-mark:hover { border-color: #1a6bd6; color: #1a6bd6; }.hint-pop { position: fixed; z-index: 1300; width: 330px; max-width: 86vw; padding: 10px 12px; border: 1px solid #e4e3dd; border-radius: 12px; background: #fff; box-shadow: 0 10px 30px rgba(20,30,50,.16); color: #4b5563; font-size: 12px; line-height: 1.65; }
@media (max-width: 600px) {
  .filter-bar { top: 58px; gap: 3px; padding: 6px; }.fb-btn { padding: 7px 1px; font-size: 11.5px; }.fb-badge { max-width: 72px; overflow: hidden; text-overflow: ellipsis; }.pop-chip { padding: 5px 10px; }
  .table-wrap { overflow-x: visible; }.rank-table { min-width: 0; font-size: 12px; }.col-school { width: 46%; }.col-score { width: 27%; }
  th, td { padding: 7px 6px; } th { font-size: 10.5px; white-space: nowrap; }.desktop-label { display: none; }.mobile-label { display: inline; }
  .school-meta { gap: 4px; font-size: 10.5px; }.school-meta span + span::before { margin-right: 4px; }.q-mark { width: 13px; height: 13px; margin-left: 1px; font-size: 9px; }
}
</style>
