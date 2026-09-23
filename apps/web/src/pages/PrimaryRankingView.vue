<script setup lang="ts">
import { computed, ref } from 'vue';
import { DISTRICTS } from '@gz/shared';
import { primarySchools, civilizedCampusSchoolIds } from '../data';
import DetailFilterBar from '../components/DetailFilterBar.vue';
import DetailPageHeader from '../components/DetailPageHeader.vue';
import DetailRankingList from '../components/DetailRankingList.vue';

type Group = 'none' | 'district';
const CIVILIZED_FILTERS = [['national', '全国文明校园'], ['provincial', '广东省文明校园'], ['municipal', '广州市文明校园'], ['advanced', '创建先进学校（储备）'], ['other', '其他']] as const;
type CivilizedKey = typeof CIVILIZED_FILTERS[number][0];
const groupBy = ref<Group>('none');
const open = ref<'group' | 'filter' | null>(null);
const selectedDistricts = ref(new Set(DISTRICTS.map((d) => d.adcode)));
const honor = ref<Set<CivilizedKey> | null>(null);
const allDistricts = computed(() => selectedDistricts.value.size === DISTRICTS.length);
const allHonors = computed(() => honor.value === null);
function toggleDistrict(id: string) { const n = new Set(selectedDistricts.value); n.has(id) ? n.delete(id) : n.add(id); selectedDistricts.value = n; }
function schoolHonors(schoolId?: string) { return schoolId ? CIVILIZED_FILTERS.filter(([key]) => key !== 'other' && (civilizedCampusSchoolIds[key] || []).includes(schoolId)).map(([, label]) => label) : []; }
function toggleHonor(v: CivilizedKey) { const n = new Set<CivilizedKey>(honor.value || CIVILIZED_FILTERS.map(([key]) => key)); n.has(v) ? n.delete(v) : n.add(v); honor.value = n; }
function toggleAllDistricts() { selectedDistricts.value = allDistricts.value ? new Set() : new Set(DISTRICTS.map((d) => d.adcode)); }
function toggleAllHonors() { honor.value = allHonors.value ? new Set() : null; }
function isVisible(s: { school_id?: string; adcode: string }) {
  const district = allDistricts.value || selectedDistricts.value.has(s.adcode);
  if (!district || allHonors.value) return district;
  const honors = schoolHonors(s.school_id);
  return [...honor.value!].some((key) => key === 'other' ? honors.length === 0 : honors.includes(CIVILIZED_FILTERS.find(([filterKey]) => filterKey === key)![1]));
}
const districtName = (adcode: string) => DISTRICTS.find((d) => d.adcode === adcode)?.name || '其他';
const groups = computed(() => {
  const rows = primarySchools.schools.filter(isVisible).slice().sort((a, b) => a.name.localeCompare(b.name, 'zh'));
  if (groupBy.value === 'none') return [{ title: '', rows }];
  return DISTRICTS.map((d) => ({ title: d.name, rows: rows.filter((s) => s.adcode === d.adcode) })).filter((g) => g.rows.length);
});
const filterCount = computed(() => (allDistricts.value ? 0 : selectedDistricts.value.size) + (allHonors.value ? 0 : honor.value!.size));
</script>

<template>
  <div class="page">
    <DetailPageHeader title="广州七区小学明细" subtitle="按小学点位展示；全国文明校园为官方正式称号。" />

    <DetailFilterBar :open="!!open" @close="open = null">
      <template #buttons>
        <div class="fb-col"><button class="fb-btn" :class="{ on: open === 'group' }" @click="open = open === 'group' ? null : 'group'">分组<em class="fb-badge">{{ groupBy === 'none' ? '不分组' : '按区' }}</em><span class="arr">▾</span></button></div>
        <div class="fb-col"><button class="fb-btn" :class="{ on: open === 'filter' }" @click="open = open === 'filter' ? null : 'filter'">筛选<em v-if="filterCount" class="fb-badge">{{ filterCount }}</em><span class="arr">▾</span></button></div>
      </template>
      <div v-if="open === 'group'">
        <div class="pop-chips"><button class="pop-chip" :class="{ on: groupBy === 'none' }" @click="groupBy = 'none'">不分组</button><button class="pop-chip" :class="{ on: groupBy === 'district' }" @click="groupBy = 'district'">按区</button></div>
        <div class="pop-foot"><button class="pop-link" @click="open = null">完成</button></div>
      </div>
      <div v-if="open === 'filter'">
        <div class="pop-group-title">位置</div><div class="pop-chips"><button v-for="d in DISTRICTS" :key="d.adcode" class="pop-chip" :class="{ on: selectedDistricts.has(d.adcode) }" @click="toggleDistrict(d.adcode)">{{ d.name }}</button></div><div class="pop-foot"><button class="pop-link" @click="toggleAllDistricts">{{ allDistricts ? '全不选' : '全选' }}</button></div>
        <div class="pop-group-title">校园荣誉</div><div class="pop-chips"><button v-for="option in CIVILIZED_FILTERS" :key="option[0]" class="pop-chip" :class="{ on: allHonors || honor?.has(option[0]) }" @click="toggleHonor(option[0])">{{ option[1] }}</button></div><div class="pop-foot"><button class="pop-link" @click="toggleAllHonors">{{ allHonors ? '全不选' : '全选' }}</button><button class="pop-link" @click="open = null">完成</button></div>
      </div>
    </DetailFilterBar>

    <DetailRankingList :groups="groups" :group-key="(g) => g.title || 'all'">
      <template #heading="{ group: g }"><h2 v-if="groupBy === 'district'">{{ g.title }}<em>{{ g.rows.length }} 所</em></h2></template>
      <template #default="{ group: g }">
        <table class="rank-table"><colgroup><col class="col-school"><col class="col-district"><col class="col-honor"></colgroup><thead><tr><th>学校 / 校区</th><th>位置</th><th>校园荣誉</th></tr></thead><tbody><tr v-for="s in g.rows" :key="s.school_id || s.name"><td class="school"><RouterLink :to="{ path: '/school/' + encodeURIComponent(s.name), query: { stage: 'primary', ...(s.school_id ? { id: s.school_id } : {}) } }">{{ s.name }}</RouterLink></td><td>{{ districtName(s.adcode) }}</td><td><span v-if="schoolHonors(s.school_id).length" class="honor">{{ schoolHonors(s.school_id).join(' · ') }}</span><span v-else class="empty">—</span></td></tr></tbody></table>
      </template>
    </DetailRankingList>
  </div>
</template>

<style scoped>
.page { max-width: 1180px; margin: 0 auto; } h2 { margin: 0; padding: 12px 18px 8px; font-size: 15px; } h2 em { margin-left: 8px; color: #8a93a3; font-size: 11.5px; font-style: normal; font-weight: 400; } .rank-table { width: 100%; min-width: 620px; border-collapse: collapse; table-layout: fixed; font-size: 12.5px; }.col-school { width: 55%; }.col-district { width: 20%; }.col-honor { width: 25%; } th { padding: 7px 10px; border-bottom: 1px solid #ecebe6; color: #6b7280; font-size: 11.5px; text-align: left; } td { padding: 9px 10px; border-bottom: 1px solid #f2f1ec; color: #6b7280; line-height: 1.5; } tbody tr:last-child td { border-bottom: 0; } tbody tr:hover { background: #fafbfc; }.school { color: #1a1b1c; }.honor { color: #1a6bd6; font-size: 11.5px; }.empty { color: #9ca3af; } @media(max-width:600px){ h2 { padding-left: 16px; }.rank-table { min-width: 0; font-size: 12px; }.col-school { width: 55%; }.col-district { width: 19%; }.col-honor { width: 26%; } th, td { padding: 8px 6px; } th { font-size: 10.5px; } }
</style>
