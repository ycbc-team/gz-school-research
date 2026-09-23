<script setup lang="ts">
import { computed, ref } from 'vue';
import { DISTRICTS } from '@gz/shared';
import { primarySchools, civilizedCampusSchoolIds } from '../data';

type Group = 'none' | 'district';
const groupBy = ref<Group>('none');
const open = ref<'group' | 'filter' | null>(null);
const selectedDistricts = ref(new Set(DISTRICTS.map((d) => d.adcode)));
const honor = ref<Set<'national' | 'other'> | null>(null);
const allDistricts = computed(() => selectedDistricts.value.size === DISTRICTS.length);
const allHonors = computed(() => honor.value === null);
function toggleDistrict(id: string) { const n = new Set(selectedDistricts.value); n.has(id) ? n.delete(id) : n.add(id); selectedDistricts.value = n; }
function toggleHonor(v: 'national' | 'other') { const n = new Set<'national' | 'other'>(honor.value || ['national', 'other']); n.has(v) ? n.delete(v) : n.add(v); honor.value = n; }
function toggleAllDistricts() { selectedDistricts.value = allDistricts.value ? new Set() : new Set(DISTRICTS.map((d) => d.adcode)); }
function toggleAllHonors() { honor.value = allHonors.value ? new Set() : null; }
function isVisible(s: { school_id?: string; adcode: string }) {
  const district = allDistricts.value || selectedDistricts.value.has(s.adcode);
  if (!district || allHonors.value) return district;
  const national = !!s.school_id && civilizedCampusSchoolIds.national?.includes(s.school_id);
  return (honor.value!.has('national') && national) || (honor.value!.has('other') && !national);
}
const districtName = (adcode: string) => DISTRICTS.find((d) => d.adcode === adcode)?.name || '其他';
const groups = computed(() => {
  const rows = primarySchools.schools.filter(isVisible).slice().sort((a, b) => a.name.localeCompare(b.name, 'zh'));
  if (groupBy.value === 'none') return [{ title: '', rows }];
  return DISTRICTS.map((d) => ({ title: d.name, rows: rows.filter((s) => s.adcode === d.adcode) })).filter((g) => g.rows.length);
});
const filterCount = computed(() => (allDistricts.value ? 0 : selectedDistricts.value.size) + (allHonors.value ? 0 : honor.value!.size));
</script>

<template><div class="page"><header><RouterLink to="/" class="back">‹ 首页</RouterLink><h1>广州七区小学明细</h1><p>按小学点位展示；全国文明校园为官方正式称号。</p></header>
  <div class="filter-bar"><button class="fb-btn" @click="open=open==='group'?null:'group'">分组：{{ groupBy==='none'?'不分组':'按区' }} ▾</button><button class="fb-btn" @click="open=open==='filter'?null:'filter'">筛选<em v-if="filterCount">{{ filterCount }}</em> ▾</button>
    <div v-if="open==='group'" class="pop"><button :class="{on:groupBy==='none'}" @click="groupBy='none'">不分组</button><button :class="{on:groupBy==='district'}" @click="groupBy='district'">按区</button></div>
    <div v-if="open==='filter'" class="pop"><h3>位置</h3><button v-for="d in DISTRICTS" :key="d.adcode" :class="{on:selectedDistricts.has(d.adcode)}" @click="toggleDistrict(d.adcode)">{{ d.name }}</button><footer><a @click="toggleAllDistricts">{{ allDistricts?'全不选':'全选' }}</a></footer><h3>校园荣誉</h3><button :class="{on:allHonors||honor?.has('national')}" @click="toggleHonor('national')">全国文明校园</button><button :class="{on:allHonors||honor?.has('other')}" @click="toggleHonor('other')">其他</button><footer><a @click="toggleAllHonors">{{ allHonors?'全不选':'全选' }}</a><a @click="open=null">完成</a></footer></div>
  </div><div v-for="g in groups" :key="g.title" class="card"><h2 v-if="groupBy==='district'">{{ g.title }} <small>{{ g.rows.length }} 所</small></h2><RouterLink v-for="s in g.rows" :key="s.school_id || s.name" :to="{path:'/school/'+encodeURIComponent(s.name),query:{stage:'primary',...(s.school_id?{id:s.school_id}:{})}}" class="row"><b>{{ s.name }}</b><span>{{ districtName(s.adcode) }}<i v-if="s.school_id && civilizedCampusSchoolIds.national?.includes(s.school_id)">全国文明校园</i></span></RouterLink></div></div></template>

<style scoped>
.page{max-width:1180px;margin:auto}.back,.row{color:#1a6bd6;text-decoration:none}h1{font-size:20px}p,small{color:#6b7280;font-size:12px}.filter-bar{position:sticky;top:65px;z-index:2;display:flex;gap:8px;margin:15px 0;padding:8px;background:#fff;border:1px solid #e4e3dd;border-radius:14px}.fb-btn,.pop button{border:1px solid #d6d4cc;background:#fff;border-radius:16px;padding:6px 11px;cursor:pointer}.fb-btn{flex:1;border:0}.fb-btn em{background:#1a6bd6;color:#fff;border-radius:9px;padding:0 5px;font-size:10px}.pop{position:absolute;top:calc(100% + 6px);left:8px;right:8px;padding:12px;background:#fff;border:1px solid #e4e3dd;border-radius:12px;box-shadow:0 8px 28px #0002}.pop h3{font-size:12px;margin:10px 0 6px}.pop h3:first-child{margin-top:0}.pop button{margin:0 6px 6px 0}.pop button.on{background:#1a6bd6;border-color:#1a6bd6;color:#fff}.pop footer{display:flex;justify-content:space-between;border-top:1px dashed #ddd;padding-top:7px;margin:4px 0 10px}.pop a{color:#1a6bd6;cursor:pointer;font-size:12px}.card{background:#fff;border:1px solid #e4e3dd;border-radius:14px;margin-bottom:14px;overflow:hidden}h2{font-size:15px;padding:10px 14px;margin:0}.row{display:flex;justify-content:space-between;gap:12px;padding:10px 14px;border-top:1px solid #f0efeb;color:#1a1b1c}.row span{color:#8a93a3;font-size:12px}.row i{margin-left:7px;color:#1a6bd6;font-style:normal;font-size:11px}@media(max-width:600px){.filter-bar{top:58px}.row{align-items:start}.row span{white-space:nowrap}}
</style>
