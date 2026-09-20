<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { entities, detailedRecords } from '../data';

const route = useRoute();

const entsById = computed(() => {
  const m: Record<string, string> = {};
  for (const e of entities.entities) m[e.school_id] = e.name;
  return m;
});

function recordsOf(competition: string, stage: string) {
  return (detailedRecords as any[]).filter((r) => r.competition === competition && r.stage === stage);
}

function bySchool(records: any[]) {
  const map: Record<string, { name: string; records: any[] }> = {};
  for (const r of records) {
    for (const sid of r.school_ids) {
      if (!map[sid]) map[sid] = { name: entsById.value[sid] || sid, records: [] };
      map[sid].records.push(r);
    }
  }
  return Object.values(map).sort((a, b) => b.records.length - a.records.length);
}

const innovationPrimary = computed(() => bySchool(recordsOf('innovation', 'primary')));
const innovationMiddle = computed(() => bySchool(recordsOf('innovation', 'middle')));
const innovationHigh = computed(() => bySchool(recordsOf('innovation', 'high')));
const chuangkePrimary = computed(() => bySchool(recordsOf('chuangke', 'primary')));
const chuangkeMiddle = computed(() => bySchool(recordsOf('chuangke', 'middle')));

onMounted(() => {
  const id = route.hash.slice(1);
  if (id) {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView();
    }, 100);
  }
});

const medalClass = (award: string) => award.includes('金') ? 'gold' : award.includes('银') ? 'silver' : 'bronze';
function goBack() { window.history.back(); }
</script>

<template>
  <div class="awards-page">
    <header class="d-head">
      <h1>白名单竞赛获奖</h1>
      <p class="sub-note">数据来源：广州市教育局官网公示（2024-2026）</p>
    </header>

    <section id="innovation" class="card">
      <div class="card-title">广州市中小学生创新大赛</div>
      <p class="sub-note">小学金点子组 / 初中金种子组 / 高中金苗子组（2024-2026）</p>

      <div class="stage-block" id="innovation-primary">
        <h3>小学组（金点子）· {{ innovationPrimary.length }} 校</h3>
        <div v-for="s in innovationPrimary" :key="s.name" class="school-block">
          <div class="school-name">{{ s.name }}</div>
          <div v-for="(r, i) in s.records" :key="i" class="record-row">
            <span class="year">{{ r.year }}</span>
            <span class="medal" :class="medalClass(r.award)">{{ r.award }}</span>
            <span class="project">{{ r.project }}</span>
            <span class="person">{{ r.members || r.leader }}</span>
          </div>
        </div>
      </div>

      <div class="stage-block" id="innovation-middle">
        <h3>初中组（金种子）· {{ innovationMiddle.length }} 校</h3>
        <div v-for="s in innovationMiddle" :key="s.name" class="school-block">
          <div class="school-name">{{ s.name }}</div>
          <div v-for="(r, i) in s.records" :key="i" class="record-row">
            <span class="year">{{ r.year }}</span>
            <span class="medal" :class="medalClass(r.award)">{{ r.award }}</span>
            <span class="project">{{ r.project }}</span>
            <span class="person">{{ r.members || r.leader }}</span>
          </div>
        </div>
      </div>

      <div class="stage-block" id="innovation-high">
        <h3>高中组（金苗子）· {{ innovationHigh.length }} 校</h3>
        <div v-for="s in innovationHigh" :key="s.name" class="school-block">
          <div class="school-name">{{ s.name }}</div>
          <div v-for="(r, i) in s.records" :key="i" class="record-row">
            <span class="year">{{ r.year }}</span>
            <span class="medal" :class="medalClass(r.award)">{{ r.award }}</span>
            <span class="project">{{ r.project }}</span>
            <span class="person">{{ r.members || r.leader }}</span>
          </div>
        </div>
      </div>
    </section>

    <section id="chuangke" class="card">
      <div class="card-title">广州市中小学生科技创客电视大赛</div>
      <p class="sub-note">个人项目 + 团体项目（2025）</p>

      <div class="stage-block" id="chuangke-primary">
        <h3>小学组 · {{ chuangkePrimary.length }} 校</h3>
        <div v-for="s in chuangkePrimary" :key="s.name" class="school-block">
          <div class="school-name">{{ s.name }}</div>
          <div v-for="(r, i) in s.records" :key="i" class="record-row">
            <span class="year">{{ r.year }}</span>
            <span class="medal" :class="medalClass(r.award)">{{ r.award }}</span>
            <span class="project">{{ r.project }}</span>
            <span class="person">{{ r.leader }}</span>
          </div>
        </div>
      </div>

      <div class="stage-block" id="chuangke-middle">
        <h3>中学组 · {{ chuangkeMiddle.length }} 校</h3>
        <div v-for="s in chuangkeMiddle" :key="s.name" class="school-block">
          <div class="school-name">{{ s.name }}</div>
          <div v-for="(r, i) in s.records" :key="i" class="record-row">
            <span class="year">{{ r.year }}</span>
            <span class="medal" :class="medalClass(r.award)">{{ r.award }}</span>
            <span class="project">{{ r.project }}</span>
            <span class="person">{{ r.leader }}</span>
          </div>
        </div>
      </div>
    </section>

    <footer class="d-foot">
      <button class="back" @click="goBack">← 返回</button>
    </footer>
  </div>
</template>

<style scoped>
.awards-page { max-width: 800px; margin: 0 auto; padding: 16px; }
.d-head { padding: 12px 0 20px; }
.d-head h1 { font-size: 22px; margin: 0 0 4px; }
.sub-note { font-size: 12px; color: #888; margin: 4px 0 0; }
.card { background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.card-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.stage-block { margin-top: 20px; }
.stage-block h3 { font-size: 14px; color: #555; margin: 0 0 10px; }
.school-block { margin-bottom: 12px; }
.school-name { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.record-row { display: flex; gap: 8px; align-items: baseline; font-size: 12px; padding: 3px 0; border-bottom: 1px solid #f5f5f5; }
.year { color: #999; min-width: 36px; }
.medal { min-width: 28px; font-weight: 600; }
.medal.gold { color: #d4a017; }
.medal.silver { color: #6b7280; }
.medal.bronze { color: #b45309; }
.project { flex: 1; color: #333; }
.person { color: #888; }
.d-foot { padding: 16px 0; }
.back { background: none; border: 1px solid #ddd; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
</style>
