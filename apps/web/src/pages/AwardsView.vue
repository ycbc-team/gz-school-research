<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { DISTRICTS } from '@gz/shared';
import { entities, detailedRecords } from '../data';

type Competition = 'innovation' | 'chuangke';
type GroupBy = 'none' | 'district';
interface AwardRecord { competition: Competition; stage: string; year: number; project: string; leader?: string; members?: string; award: string; school_ids: string[]; }
interface AwardSchool { id: string; name: string; district: string; records: AwardRecord[]; }

const route = useRoute();
const records = detailedRecords as unknown as AwardRecord[];
const COMPETITIONS: Array<{ value: Competition; label: string }> = [
  { value: 'innovation', label: '创新大赛' },
  { value: 'chuangke', label: '科技创客电视大赛' },
];
const COMPETITION_LABEL = Object.fromEntries(COMPETITIONS.map((item) => [item.value, item.label])) as Record<Competition, string>;
const DISTRICT_BY_ADCODE = new Map(DISTRICTS.map((district) => [district.adcode, district.name]));
const entitiesById = new Map(entities.entities.map((entity) => [entity.school_id, entity.name]));

const openMenu = ref<null | 'group' | 'district' | 'competition' | 'year'>(null);
const groupBy = ref<GroupBy>('none');
const competition = ref<'all' | Competition>('all');
const year = ref<'all' | number>('all');
const selectedDistricts = ref(new Set(DISTRICTS.map((district) => district.adcode)));
const targetSchoolId = computed(() => typeof route.query.school === 'string' ? route.query.school : '');
const groupLabel = computed(() => groupBy.value === 'district' ? '按区' : '不分组');
const competitionLabel = computed(() => competition.value === 'all' ? '全部比赛' : COMPETITION_LABEL[competition.value]);
const years = computed(() => [...new Set(records.filter((record) => competition.value === 'all' || record.competition === competition.value).map((record) => record.year))].sort((a, b) => b - a));
const districtAllOn = computed(() => selectedDistricts.value.size === DISTRICTS.length);

function districtOf(id: string) { return DISTRICT_BY_ADCODE.get(id.slice(3, 9)) || '其他'; }
function toggleDistrict(adcode: string) {
  const next = new Set(selectedDistricts.value);
  next.has(adcode) ? next.delete(adcode) : next.add(adcode);
  selectedDistricts.value = next;
}
function flipDistricts() { selectedDistricts.value = districtAllOn.value ? new Set() : new Set(DISTRICTS.map((district) => district.adcode)); }
function selectCompetition(value: 'all' | Competition) {
  competition.value = value;
  if (year.value !== 'all' && !years.value.includes(year.value)) year.value = 'all';
}
function schoolDomId(id: string) { return `award-school-${id}`; }
function scrollToTargetSchool() {
  if (!targetSchoolId.value) return;
  nextTick(() => requestAnimationFrame(() => {
    document.getElementById(schoolDomId(targetSchoolId.value))?.scrollIntoView({ block: 'start' });
  }));
}

const filteredSchools = computed<AwardSchool[]>(() => {
  const map = new Map<string, AwardSchool>();
  for (const record of records) {
    if (competition.value !== 'all' && record.competition !== competition.value) continue;
    if (year.value !== 'all' && record.year !== year.value) continue;
    for (const id of record.school_ids) {
      if (!selectedDistricts.value.has(id.slice(3, 9))) continue;
      const school = map.get(id) || { id, name: entitiesById.get(id) || id, district: districtOf(id), records: [] };
      school.records.push(record);
      map.set(id, school);
    }
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name, 'zh'));
});
const groups = computed(() => {
  if (groupBy.value === 'none') return [{ key: 'all', title: '', schools: filteredSchools.value }];
  const byDistrict = new Map<string, AwardSchool[]>();
  for (const school of filteredSchools.value) {
    const schools = byDistrict.get(school.district) || [];
    schools.push(school);
    byDistrict.set(school.district, schools);
  }
  const order = new Map(DISTRICTS.map((district, index) => [district.name, index]));
  return [...byDistrict.entries()].sort(([a], [b]) => (order.get(a) ?? 99) - (order.get(b) ?? 99)).map(([title, schools]) => ({ key: title, title, schools }));
});

watch(() => [route.query.competition, route.query.school], () => {
  const requested = route.query.competition;
  if (requested === 'innovation' || requested === 'chuangke') selectCompetition(requested);
  scrollToTargetSchool();
}, { immediate: true });
watch([competition, year, selectedDistricts, groupBy], scrollToTargetSchool);
onMounted(scrollToTargetSchool);

const medalClass = (award: string) => award.includes('金') || award.includes('一等') ? 'gold' : award.includes('银') || award.includes('二等') ? 'silver' : 'bronze';
function goBack() { window.history.back(); }
</script>

<template>
  <div class="awards-page">
    <header class="top">
      <RouterLink to="/" class="back">‹ 首页</RouterLink>
      <h1 class="page-title">白名单竞赛获奖</h1>
      <p class="sub-note">数据来源：广州市教育局官网公示（2024-2026）</p>
    </header>

    <div class="filter-bar">
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'group' }" @click="openMenu = openMenu === 'group' ? null : 'group'">分组<em class="fb-badge">{{ groupLabel }}</em><span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'district' }" @click="openMenu = openMenu === 'district' ? null : 'district'">位置<em v-if="!districtAllOn" class="fb-badge">{{ selectedDistricts.size }}</em><span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'competition' }" @click="openMenu = openMenu === 'competition' ? null : 'competition'">比赛：{{ competitionLabel }}<span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'year' }" @click="openMenu = openMenu === 'year' ? null : 'year'">年份：{{ year === 'all' ? '全部' : year }}<span class="arr">▾</span></button></div>
      <div v-if="openMenu === 'group'" class="fb-pop"><div class="pop-chips"><button class="pop-chip" :class="{ on: groupBy === 'none' }" @click="groupBy = 'none'">不分组</button><button class="pop-chip" :class="{ on: groupBy === 'district' }" @click="groupBy = 'district'">按区</button></div><div class="pop-foot"><button class="pop-link" @click="openMenu = null">完成</button></div></div>
      <div v-if="openMenu === 'district'" class="fb-pop"><div class="pop-chips"><button v-for="district in DISTRICTS" :key="district.adcode" class="pop-chip" :class="{ on: selectedDistricts.has(district.adcode) }" @click="toggleDistrict(district.adcode)">{{ district.name }}</button></div><div class="pop-foot"><button class="pop-link" @click="flipDistricts">{{ districtAllOn ? '取消全选' : '全选' }}</button><button class="pop-link" @click="openMenu = null">完成</button></div></div>
      <div v-if="openMenu === 'competition'" class="fb-pop"><div class="pop-chips"><button class="pop-chip" :class="{ on: competition === 'all' }" @click="selectCompetition('all')">全部比赛</button><button v-for="item in COMPETITIONS" :key="item.value" class="pop-chip" :class="{ on: competition === item.value }" @click="selectCompetition(item.value)">{{ item.label }}</button></div><div class="pop-foot"><button class="pop-link" @click="openMenu = null">完成</button></div></div>
      <div v-if="openMenu === 'year'" class="fb-pop"><div class="pop-chips"><button class="pop-chip" :class="{ on: year === 'all' }" @click="year = 'all'">全部年份</button><button v-for="item in years" :key="item" class="pop-chip" :class="{ on: year === item }" @click="year = item">{{ item }}</button></div><div class="pop-foot"><button class="pop-link" @click="openMenu = null">完成</button></div></div>
    </div>
    <div v-if="openMenu" class="pop-mask" @click="openMenu = null"></div>

    <main class="awards-body">
      <section v-for="group in groups" :key="group.key" class="award-group">
        <h2 v-if="groupBy === 'district'" class="group-title">{{ group.title }}<em>{{ group.schools.length }} 校</em></h2>
        <div v-for="school in group.schools" :id="schoolDomId(school.id)" :key="school.id" class="school-block" :class="{ target: school.id === targetSchoolId }">
          <div class="school-name">{{ school.name }}<span class="stage-tag">{{ school.records[0]?.stage === 'primary' ? '小学' : school.records[0]?.stage === 'middle' ? '初中' : '高中' }}</span></div>
          <div v-for="(record, index) in school.records" :key="index" class="record-row">
            <div class="record-meta"><span class="year">{{ record.year }}</span><span class="medal" :class="medalClass(record.award)">{{ record.award }}</span><span v-if="competition === 'all'" class="competition-tag">{{ COMPETITION_LABEL[record.competition] }}</span></div>
            <div class="project"><span class="record-label">项目</span>{{ record.project }}</div>
            <div class="person"><span class="record-label">参赛学生</span>{{ record.members || record.leader }}</div>
          </div>
        </div>
        <p v-if="!group.schools.length" class="empty">没有符合当前筛选条件的获奖记录。</p>
      </section>
    </main>
    <footer class="d-foot"><button class="back-button" @click="goBack">← 返回</button></footer>
  </div>
</template>

<style scoped>
.awards-page { max-width: 1180px; margin: 0 auto; }.top { display: flex; flex-direction: column; gap: 7px; }.back { font-size: 13px; color: #1a6bd6; text-decoration: none; }.page-title { font-size: 20px; font-weight: 700; margin: 0; }.sub-note { font-size: 12px; color: #888; margin: 0; }
.filter-bar { position: sticky; top: 65px; z-index: 1200; display: flex; gap: 8px; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 8px; margin: 15px 0; }.fb-col { flex: 1 1 0; min-width: 0; }.fb-btn { width: 100%; border: none; background: transparent; cursor: pointer; font-size: 13px; color: #1a1b1c; padding: 8px 6px; border-radius: 9px; display: flex; align-items: center; justify-content: center; gap: 4px; white-space: nowrap; }.fb-btn:hover { background: #f2f7ff; }.fb-btn.on { background: #eaf1fe; color: #1a6bd6; font-weight: 600; }.arr { font-size: 10px; color: #8a93a3; }.fb-badge { background: #1a6bd6; color: #fff; font-style: normal; font-size: 10.5px; border-radius: 9px; padding: 0 6px; line-height: 15px; }
.fb-pop { position: absolute; top: calc(100% + 6px); left: 8px; right: 8px; z-index: 1300; background: #fff; border: 1px solid #e4e3dd; border-radius: 12px; box-shadow: 0 8px 28px rgba(20, 30, 50, .16); padding: 12px; }.pop-chips { display: flex; flex-wrap: wrap; gap: 6px; }.pop-chip { border: 1px solid #d6d4cc; background: #fff; border-radius: 16px; padding: 5px 14px; font-size: 12.5px; cursor: pointer; color: #1a1b1c; }.pop-chip.on { background: #1a6bd6; border-color: #1a6bd6; color: #fff; }.pop-foot { display: flex; justify-content: flex-end; margin-top: 10px; }.pop-link { border: none; background: none; color: #1a6bd6; font-size: 13px; cursor: pointer; padding: 4px 8px; }.pop-mask { position: fixed; inset: 0; z-index: 1100; }
.awards-body { display: flex; flex-direction: column; gap: 16px; }.award-group { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 14px 18px; }.group-title { font-size: 15px; margin: 0 0 10px; }.group-title em { margin-left: 8px; color: #8a93a3; font-size: 11.5px; font-style: normal; font-weight: 500; }.school-block { padding: 10px 0; border-bottom: 1px solid #ecebe6; scroll-margin-top: 130px; }.school-block:last-child { border-bottom: none; }.school-block.target { background: #f2f7ff; box-shadow: 0 0 0 6px #f2f7ff; border-radius: 6px; }.school-name { font-size: 14px; font-weight: 700; margin-bottom: 4px; }.stage-tag, .competition-tag { margin-left: 6px; font-size: 10.5px; font-weight: 500; color: #6b7280; background: #f3f4f6; border-radius: 8px; padding: 1px 5px; }.record-row { font-size: 12px; padding: 7px 0; border-bottom: 1px solid #f5f5f5; }.record-row:last-child { border-bottom: none; }.record-meta { display: flex; gap: 8px; align-items: baseline; margin-bottom: 3px; }.year { color: #999; min-width: 36px; }.medal { min-width: 28px; font-weight: 600; }.medal.gold { color: #d4a017; }.medal.silver { color: #6b7280; }.medal.bronze { color: #b45309; }.project, .person { display: flex; align-items: flex-start; gap: 6px; line-height: 1.55; overflow-wrap: anywhere; }.project { color: #333; }.person { color: #888; margin-top: 1px; }.record-label { flex: none; color: #999; }.empty { color: #8a93a3; font-size: 13px; }.d-foot { padding: 16px 0; }.back-button { background: none; border: 1px solid #ddd; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
@media (max-width: 600px) { .filter-bar { gap: 4px; padding: 5px; }.fb-btn { font-size: 12px; padding: 7px 2px; }.fb-badge { display: none; }.award-group { padding: 12px; } }
</style>
