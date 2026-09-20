<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { DISTRICTS } from '@gz/shared';
import { entities, detailedRecords } from '../data';

type Competition = 'innovation' | 'chuangke';
type GroupBy = 'none' | 'district';
type AwardStage = 'primary' | 'middle' | 'high' | 'secondary';
type SelectionStage = Exclude<AwardStage, 'secondary'>;
interface AwardRecord { competition: Competition; stage: AwardStage; year: number; school: string; project: string; leader?: string; members?: string; award: string; school_ids: string[]; }
interface AwardSchool { key: string; name: string; district: string; stage: AwardStage; ids: string[]; records: AwardRecord[]; }

const route = useRoute();
const router = useRouter();
const records = detailedRecords as unknown as AwardRecord[];
const COMPETITIONS: Array<{ value: Competition; label: string }> = [
  { value: 'innovation', label: '创新大赛' },
  { value: 'chuangke', label: '科技创客电视大赛' },
];
const COMPETITION_LABEL = Object.fromEntries(COMPETITIONS.map((item) => [item.value, item.label])) as Record<Competition, string>;
const STAGES: Array<{ value: SelectionStage; label: string }> = [
  { value: 'primary', label: '小学' },
  { value: 'middle', label: '初中' },
  { value: 'high', label: '高中' },
];
const STAGE_LABEL: Record<AwardStage, string> = { primary: '小学', middle: '初中', high: '高中', secondary: '中学组（初中+高中）' };
const DISTRICT_BY_ADCODE = new Map(DISTRICTS.map((district) => [district.adcode, district.name]));
const entitiesById = new Map(entities.entities.map((entity) => [entity.school_id, entity]));

const openMenu = ref<null | 'group' | 'district' | 'event' | 'stage'>(null);
const groupBy = ref<GroupBy>('none');
const eventKey = (competition: Competition, year: number) => `${competition}:${year}`;
const allEventKeys = [...new Set(records.map((record) => eventKey(record.competition, record.year)))];
const selectedEvents = ref(new Set(allEventKeys));
const selectedStages = ref(new Set<SelectionStage>(STAGES.map((item) => item.value)));
const selectedDistricts = ref(new Set(DISTRICTS.map((district) => district.adcode)));
const targetSchoolId = computed(() => typeof route.query.school === 'string' ? route.query.school : '');
const groupLabel = computed(() => groupBy.value === 'district' ? '按区' : '不分组');
const eventAllOn = computed(() => selectedEvents.value.size === allEventKeys.length);
const stageAllOn = computed(() => selectedStages.value.size === STAGES.length);
const eventLabel = computed(() => eventAllOn.value ? '全部' : `已选 ${selectedEvents.value.size}`);
const stageLabel = computed(() => {
  if (stageAllOn.value) return '全部';
  const onlyStage = [...selectedStages.value][0];
  return selectedStages.value.size === 1 && onlyStage ? STAGE_LABEL[onlyStage] : `已选 ${selectedStages.value.size}`;
});
function yearsOf(value: Competition) {
  return [...new Set(records.filter((record) => record.competition === value).map((record) => record.year))]
    .sort((a, b) => b - a);
}
const districtAllOn = computed(() => selectedDistricts.value.size === DISTRICTS.length);

function districtOf(id: string) { return DISTRICT_BY_ADCODE.get(id.slice(3, 9)) || '其他'; }
function toggleDistrict(adcode: string) {
  const next = new Set(selectedDistricts.value);
  next.has(adcode) ? next.delete(adcode) : next.add(adcode);
  selectedDistricts.value = next;
}
function selectAllDistricts(selected: boolean) { selectedDistricts.value = selected ? new Set(DISTRICTS.map((district) => district.adcode)) : new Set(); }
function toggleEvent(key: string) {
  const next = new Set(selectedEvents.value);
  next.has(key) ? next.delete(key) : next.add(key);
  selectedEvents.value = next;
}
function toggleCompetitionEvents(value: Competition) {
  const keys = yearsOf(value).map((itemYear) => eventKey(value, itemYear));
  const next = new Set(selectedEvents.value);
  const allOn = keys.every((key) => next.has(key));
  keys.forEach((key) => allOn ? next.delete(key) : next.add(key));
  selectedEvents.value = next;
}
function selectAllEvents(selected: boolean) { selectedEvents.value = selected ? new Set(allEventKeys) : new Set(); }
function toggleStage(value: SelectionStage) {
  const next = new Set(selectedStages.value);
  next.has(value) ? next.delete(value) : next.add(value);
  selectedStages.value = next;
}
function selectAllStages(selected: boolean) { selectedStages.value = selected ? new Set(STAGES.map((item) => item.value)) : new Set(); }
function schoolDomId(key: string) { return `award-school-${encodeURIComponent(key)}`; }
const targetSchool = computed(() => filteredSchools.value.find((school) => school.ids.includes(targetSchoolId.value)));
function scrollToTargetSchool() {
  if (!targetSchoolId.value || !targetSchool.value) return;
  nextTick(() => requestAnimationFrame(() => {
    document.getElementById(schoolDomId(targetSchool.value!.key))?.scrollIntoView({ block: 'start' });
  }));
}

const filteredSchools = computed<AwardSchool[]>(() => {
  const map = new Map<string, AwardSchool>();
  for (const record of records) {
    if (!selectedEvents.value.has(eventKey(record.competition, record.year))) continue;
    if (record.stage === 'secondary'
      ? !selectedStages.value.has('middle') && !selectedStages.value.has('high')
      : !selectedStages.value.has(record.stage)) continue;
    const ids = record.school_ids.filter((id) => selectedDistricts.value.has(id.slice(3, 9)));
    if (!ids.length) continue;
    const key = `${record.stage}:${record.school}`;
    const school = map.get(key) || { key, name: record.school, district: districtOf(ids[0]!), stage: record.stage, ids: [], records: [] };
    school.ids = [...new Set([...school.ids, ...ids])];
    school.records.push(record);
    map.set(key, school);
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

watch(() => [route.query.competition, route.query.stage, route.query.school], () => {
  const requested = route.query.competition;
  if (requested === 'innovation' || requested === 'chuangke') {
    selectedEvents.value = new Set(yearsOf(requested).map((itemYear) => eventKey(requested, itemYear)));
  }
  const requestedStage = route.query.stage;
  if (requestedStage === 'primary' || requestedStage === 'middle' || requestedStage === 'high') selectedStages.value = new Set([requestedStage]);
  scrollToTargetSchool();
}, { immediate: true });
watch([selectedEvents, selectedStages, selectedDistricts, groupBy], scrollToTargetSchool);
onMounted(scrollToTargetSchool);

const campusPicker = ref<{ top: number; left: number; school: AwardSchool; items: Array<{ id: string; name: string; stage: string; district: string }> } | null>(null);
function openSchool(school: AwardSchool, event: MouseEvent) {
  const ids = school.ids.filter((id) => entitiesById.has(id));
  if (ids.length < 2) {
    const id = ids[0];
    const entity = id ? entitiesById.get(id) : null;
    if (id && entity) router.push({ path: `/school/${encodeURIComponent(entity.name)}`, query: { stage: entity.stage, id } });
    return;
  }
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
  const width = 300;
  campusPicker.value = {
    top: rect.bottom + 6,
    left: rect.left + width > window.innerWidth - 8 ? Math.max(8, window.innerWidth - width - 8) : rect.left,
    school,
    items: ids.map((id) => ({ id, name: entitiesById.get(id)!.name, stage: entitiesById.get(id)!.stage, district: districtOf(id) })),
  };
}
function goCampus(item: { id: string; name: string; stage: string }, school: AwardSchool) {
  campusPicker.value = null;
  router.push({ path: `/school/${encodeURIComponent(item.name)}`, query: { stage: item.stage, id: item.id } });
}

const medalClass = (award: string) => award.includes('金') || award.includes('一等') ? 'gold' : award.includes('银') || award.includes('二等') ? 'silver' : 'bronze';
function goBack() { window.history.back(); }
</script>

<template>
  <div class="awards-page">
    <header class="top">
      <RouterLink to="/" class="back">‹ 首页</RouterLink>
      <h1 class="page-title">竞赛获奖明细</h1>
      <p class="sub-note">数据来源：广州市教育局官网公示（2024-2026）</p>
    </header>

    <div class="filter-bar">
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'group' }" @click="openMenu = openMenu === 'group' ? null : 'group'">分组<em class="fb-badge">{{ groupLabel }}</em><span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'district' }" @click="openMenu = openMenu === 'district' ? null : 'district'">位置<em v-if="!districtAllOn" class="fb-badge">{{ selectedDistricts.size }}</em><span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'event' }" @click="openMenu = openMenu === 'event' ? null : 'event'">赛事：{{ eventLabel }}<span class="arr">▾</span></button></div>
      <div class="fb-col"><button class="fb-btn" :class="{ on: openMenu === 'stage' }" @click="openMenu = openMenu === 'stage' ? null : 'stage'">学段：{{ stageLabel }}<span class="arr">▾</span></button></div>
      <div v-if="openMenu === 'group'" class="fb-pop"><div class="pop-chips"><button class="pop-chip" :class="{ on: groupBy === 'none' }" @click="groupBy = 'none'">不分组</button><button class="pop-chip" :class="{ on: groupBy === 'district' }" @click="groupBy = 'district'">按区</button></div><div class="pop-foot pop-foot-right"><button class="pop-link" @click="openMenu = null">完成</button></div></div>
      <div v-if="openMenu === 'district'" class="fb-pop"><div class="pop-chips"><button v-for="district in DISTRICTS" :key="district.adcode" class="pop-chip" :class="{ on: selectedDistricts.has(district.adcode) }" @click="toggleDistrict(district.adcode)">{{ district.name }}</button></div><div class="pop-foot"><button class="pop-link" @click="selectAllDistricts(!districtAllOn)">{{ districtAllOn ? '全不选' : '全选' }}</button><button class="pop-link" @click="openMenu = null">完成</button></div></div>
      <div v-if="openMenu === 'event'" class="fb-pop">
        <div v-for="item in COMPETITIONS" :key="item.value" class="pop-group">
          <div class="pop-group-title">{{ item.label }}</div>
          <div class="pop-chips"><button class="pop-chip" :class="{ on: yearsOf(item.value).every((itemYear) => selectedEvents.has(eventKey(item.value, itemYear))) }" @click="toggleCompetitionEvents(item.value)">全部年份</button><button v-for="itemYear in yearsOf(item.value)" :key="itemYear" class="pop-chip" :class="{ on: selectedEvents.has(eventKey(item.value, itemYear)) }" @click="toggleEvent(eventKey(item.value, itemYear))">{{ itemYear }}</button></div>
        </div>
        <div class="pop-foot"><button class="pop-link" @click="selectAllEvents(!eventAllOn)">{{ eventAllOn ? '全不选' : '全选' }}</button><button class="pop-link" @click="openMenu = null">完成</button></div>
      </div>
      <div v-if="openMenu === 'stage'" class="fb-pop"><div class="pop-chips"><button v-for="item in STAGES" :key="item.value" class="pop-chip" :class="{ on: selectedStages.has(item.value) }" @click="toggleStage(item.value)">{{ item.label }}</button></div><div class="pop-foot"><button class="pop-link" @click="selectAllStages(!stageAllOn)">{{ stageAllOn ? '全不选' : '全选' }}</button><button class="pop-link" @click="openMenu = null">完成</button></div></div>
    </div>
    <div v-if="openMenu" class="pop-mask" @click="openMenu = null"></div>

    <main class="awards-body">
      <section v-for="group in groups" :key="group.key" class="award-group">
        <h2 v-if="groupBy === 'district'" class="group-title">{{ group.title }}<em>{{ group.schools.length }} 校</em></h2>
        <div v-for="school in group.schools" :id="schoolDomId(school.key)" :key="school.key" class="school-block" :class="{ target: school.ids.includes(targetSchoolId) }">
          <div class="school-name"><button class="school-link" @click="openSchool(school, $event)">{{ school.name }}</button><span class="stage-tag">{{ STAGE_LABEL[school.stage] }}</span></div>
          <div v-for="(record, index) in school.records" :key="index" class="record-row">
            <div class="record-meta"><span class="year">{{ record.year }}</span><span class="medal" :class="medalClass(record.award)">{{ record.award }}</span><span v-if="selectedEvents.size !== yearsOf(record.competition).length" class="competition-tag">{{ COMPETITION_LABEL[record.competition] }}</span></div>
            <div class="project"><span class="record-label">项目</span>{{ record.project }}</div>
            <div class="person"><span class="record-label">参赛学生</span>{{ record.members || record.leader }}</div>
          </div>
        </div>
        <p v-if="!group.schools.length" class="empty">没有符合当前筛选条件的获奖记录。</p>
      </section>
    </main>
    <footer class="d-foot"><button class="back-button" @click="goBack">← 返回</button></footer>
    <Teleport to="body">
      <div v-if="campusPicker" class="campus-mask" @click="campusPicker = null"></div>
      <div v-if="campusPicker" class="campus-pop" :style="{ top: campusPicker.top + 'px', left: campusPicker.left + 'px' }">
        <div class="campus-pop-title">选择校区</div>
        <button v-for="campus in campusPicker.items" :key="campus.id" class="campus-opt" @click="goCampus(campus, campusPicker!.school)"><span>{{ campus.name }}</span><span class="campus-dist">{{ campus.district }}</span></button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.awards-page { max-width: 1180px; margin: 0 auto; }.top { display: flex; flex-direction: column; gap: 7px; }.back { font-size: 13px; color: #1a6bd6; text-decoration: none; }.page-title { font-size: 20px; font-weight: 700; margin: 0; }.sub-note { font-size: 12px; color: #888; margin: 0; }
.filter-bar { position: sticky; top: 65px; z-index: 1200; display: flex; gap: 8px; background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 8px; margin: 15px 0; }.fb-col { flex: 1 1 0; min-width: 0; }.fb-btn { width: 100%; border: none; background: transparent; cursor: pointer; font-size: 13px; color: #1a1b1c; padding: 8px 6px; border-radius: 9px; display: flex; align-items: center; justify-content: center; gap: 4px; white-space: nowrap; }.fb-btn:hover { background: #f2f7ff; }.fb-btn.on { background: #eaf1fe; color: #1a6bd6; font-weight: 600; }.arr { font-size: 10px; color: #8a93a3; }.fb-badge { background: #1a6bd6; color: #fff; font-style: normal; font-size: 10.5px; border-radius: 9px; padding: 0 6px; line-height: 15px; }
.fb-pop { position: absolute; top: calc(100% + 6px); left: 8px; right: 8px; z-index: 1300; background: #fff; border: 1px solid #e4e3dd; border-radius: 12px; box-shadow: 0 8px 28px rgba(20, 30, 50, .16); padding: 12px; }.pop-group { margin-top: 10px; }.pop-group-title { font-size: 11.5px; color: #6b7280; font-weight: 600; margin-bottom: 6px; }.pop-chips { display: flex; flex-wrap: wrap; gap: 6px; }.pop-chip { border: 1px solid #d6d4cc; background: #fff; border-radius: 16px; padding: 5px 14px; font-size: 12.5px; cursor: pointer; color: #1a1b1c; }.pop-chip.on { background: #1a6bd6; border-color: #1a6bd6; color: #fff; }.pop-foot { display: flex; justify-content: space-between; margin-top: 10px; }.pop-foot-right { justify-content: flex-end; }.pop-link { border: none; background: none; color: #1a6bd6; font-size: 13px; cursor: pointer; padding: 4px 8px; }.pop-mask { position: fixed; inset: 0; z-index: 1100; }
.awards-body { display: flex; flex-direction: column; gap: 16px; }.award-group { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 14px 18px; }.group-title { font-size: 15px; margin: 0 0 10px; }.group-title em { margin-left: 8px; color: #8a93a3; font-size: 11.5px; font-style: normal; font-weight: 500; }.school-block { padding: 10px 0; border-bottom: 1px solid #ecebe6; scroll-margin-top: 130px; }.school-block:last-child { border-bottom: none; }.school-block.target { background: #f2f7ff; box-shadow: 0 0 0 6px #f2f7ff; border-radius: 6px; }.school-name { font-size: 14px; font-weight: 700; margin-bottom: 4px; }.stage-tag, .competition-tag { margin-left: 6px; font-size: 10.5px; font-weight: 500; color: #6b7280; background: #f3f4f6; border-radius: 8px; padding: 1px 5px; }.record-row { font-size: 12px; padding: 7px 0; border-bottom: 1px solid #f5f5f5; }.record-row:last-child { border-bottom: none; }.record-meta { display: flex; gap: 8px; align-items: baseline; margin-bottom: 3px; }.year { color: #999; min-width: 36px; }.medal { min-width: 28px; font-weight: 600; }.medal.gold { color: #d4a017; }.medal.silver { color: #6b7280; }.medal.bronze { color: #b45309; }.project, .person { display: flex; align-items: flex-start; gap: 6px; line-height: 1.55; overflow-wrap: anywhere; }.project { color: #333; }.person { color: #888; margin-top: 1px; }.record-label { flex: none; color: #999; }.empty { color: #8a93a3; font-size: 13px; }.d-foot { padding: 16px 0; }.back-button { background: none; border: 1px solid #ddd; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
.school-link { border: 0; background: none; padding: 0; color: #1a6bd6; font: inherit; font-weight: inherit; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; text-align: left; }.school-link:hover { color: #0e4fb0; text-decoration-thickness: 2px; }.campus-mask { position: fixed; inset: 0; z-index: 1350; background: rgba(0, 0, 0, .03); }.campus-pop { position: fixed; z-index: 1400; width: 300px; max-width: 86vw; background: #fff; border: 1px solid #e4e3dd; border-radius: 12px; box-shadow: 0 10px 30px rgba(20, 30, 50, .16); padding: 8px; }.campus-pop-title { font-size: 12.5px; font-weight: 700; color: #1a1b1c; padding: 4px 6px 8px; }.campus-opt { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; border: 0; background: transparent; border-radius: 8px; padding: 7px 8px; font-size: 12.5px; color: #1a6bd6; cursor: pointer; text-align: left; }.campus-opt:hover { background: #f2f7ff; }.campus-dist { flex: none; font-size: 11px; color: #8a93a3; }
@media (max-width: 600px) { .filter-bar { gap: 4px; padding: 5px; }.fb-btn { font-size: 12px; padding: 7px 2px; }.fb-badge { display: none; }.award-group { padding: 12px; } }
</style>
