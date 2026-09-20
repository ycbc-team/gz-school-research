<script setup lang="ts">
import { computed } from 'vue';
import { innovationAwards, chuangkeAwards, entities } from '../data';

const entsById = computed(() => {
  const m: Record<string, string> = {};
  for (const e of entities.entities) m[e.school_id] = e.name;
  return m;
});

const stageLabel = (s: string) => s === 'primary' ? '小学组' : s === 'middle' ? '初中组' : '高中组';

function medalList(awards: Record<string, any>, stage: string) {
  const bySchool: Record<string, { gold: number; silver: number; bronze: number }> = {};
  for (const [sid, data] of Object.entries(awards)) {
    const stages = (data as any).innovation_awards?.stages || (data as any).chuangke_awards?.stages || {};
    const years = stages[stage] || {};
    for (const yr of Object.keys(years)) {
      const m = years[yr];
      bySchool[sid] = bySchool[sid] || { gold: 0, silver: 0, bronze: 0 };
      bySchool[sid].gold += m.gold || 0;
      bySchool[sid].silver += m.silver || 0;
      bySchool[sid].bronze += m.bronze || 0;
    }
  }
  return Object.entries(bySchool)
    .map(([sid, m]) => ({ sid, name: entsById.value[sid] || sid, ...m }))
    .sort((a, b) => b.gold - a.gold || b.silver - a.silver || b.bronze - a.bronze);
}

const innovationPrimary = computed(() => medalList(innovationAwards as any, 'primary'));
const innovationMiddle = computed(() => medalList(innovationAwards as any, 'middle'));
const innovationHigh = computed(() => medalList(innovationAwards as any, 'high'));
const chuangkePrimary = computed(() => medalList(chuangkeAwards as any, 'primary'));
const chuangkeMiddle = computed(() => medalList(chuangkeAwards as any, 'middle'));
</script>

<template>
  <div class="awards-page">
    <header class="d-head">
      <h1>白名单竞赛获奖</h1>
      <p class="sub-note">数据来源：广州市教育局官网公示（2024-2026）</p>
    </header>

    <!-- 创新大赛 -->
    <section id="innovation" class="card">
      <div class="card-title">广州市中小学生创新大赛</div>
      <p class="sub-note">小学金点子组 / 初中金种子组 / 高中金苗子组（2024-2026）</p>

      <div class="stage-block">
        <h3>小学组（金点子）</h3>
        <table class="rank-table">
          <thead><tr><th>#</th><th>学校</th><th>金</th><th>银</th><th>铜</th></tr></thead>
          <tbody><tr v-for="(r, i) in innovationPrimary" :key="r.sid">
            <td>{{ i + 1 }}</td>
            <td>{{ r.name }}</td>
            <td v-if="r.gold">{{ r.gold }}</td><td v-else>-</td>
            <td v-if="r.silver">{{ r.silver }}</td><td v-else>-</td>
            <td v-if="r.bronze">{{ r.bronze }}</td><td v-else>-</td>
          </tr>
        </tbody></table>
      </div>

      <div class="stage-block">
        <h3>初中组（金种子）</h3>
        <table class="rank-table">
          <thead><tr><th>#</th><th>学校</th><th>金</th><th>银</th><th>铜</th></tr></thead>
          <tbody><tr v-for="(r, i) in innovationMiddle" :key="r.sid">
            <td>{{ i + 1 }}</td>
            <td>{{ r.name }}</td>
            <td v-if="r.gold">{{ r.gold }}</td><td v-else>-</td>
            <td v-if="r.silver">{{ r.silver }}</td><td v-else>-</td>
            <td v-if="r.bronze">{{ r.bronze }}</td><td v-else>-</td>
          </tr>
        </tbody></table>
      </div>

      <div class="stage-block">
        <h3>高中组（金苗子）</h3>
        <table class="rank-table">
          <thead><tr><th>#</th><th>学校</th><th>金</th><th>银</th><th>铜</th></tr></thead>
          <tbody><tr v-for="(r, i) in innovationHigh" :key="r.sid">
            <td>{{ i + 1 }}</td>
            <td>{{ r.name }}</td>
            <td v-if="r.gold">{{ r.gold }}</td><td v-else>-</td>
            <td v-if="r.silver">{{ r.silver }}</td><td v-else>-</td>
            <td v-if="r.bronze">{{ r.bronze }}</td><td v-else>-</td>
          </tr>
        </tbody></table>
      </div>
    </section>

    <!-- 创客大赛 -->
    <section id="chuangke" class="card">
      <div class="card-title">广州市中小学生科技创客电视大赛</div>
      <p class="sub-note">个人项目 + 团体项目（2025）</p>

      <div class="stage-block">
        <h3>小学组</h3>
        <table class="rank-table">
          <thead><tr><th>#</th><th>学校</th><th>金</th><th>银</th><th>铜</th></tr></thead>
          <tbody><tr v-for="(r, i) in chuangkePrimary" :key="r.sid">
            <td>{{ i + 1 }}</td>
            <td>{{ r.name }}</td>
            <td v-if="r.gold">{{ r.gold }}</td><td v-else>-</td>
            <td v-if="r.silver">{{ r.silver }}</td><td v-else>-</td>
            <td v-if="r.bronze">{{ r.bronze }}</td><td v-else>-</td>
          </tr>
        </tbody></table>
      </div>

      <div class="stage-block">
        <h3>中学组</h3>
        <table class="rank-table">
          <thead><tr><th>#</th><th>学校</th><th>金</th><th>银</th><th>铜</th></tr></thead>
          <tbody><tr v-for="(r, i) in chuangkeMiddle" :key="r.sid">
            <td>{{ i + 1 }}</td>
            <td>{{ r.name }}</td>
            <td v-if="r.gold">{{ r.gold }}</td><td v-else>-</td>
            <td v-if="r.silver">{{ r.silver }}</td><td v-else>-</td>
            <td v-if="r.bronze">{{ r.bronze }}</td><td v-else>-</td>
          </tr>
        </tbody></table>
      </div>
    </section>

    <footer class="d-foot">
      <button class="back" @click="history.back()">← 返回</button>
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
.stage-block { margin-top: 16px; }
.stage-block h3 { font-size: 14px; color: #555; margin: 0 0 8px; }
.rank-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.rank-table th, .rank-table td { padding: 6px 8px; border-bottom: 1px solid #f0f0f0; text-align: left; }
.rank-table th { color: #888; font-weight: 500; }
.d-foot { padding: 16px 0; }
.back { background: none; border: 1px solid #ddd; padding: 8px 16px; border-radius: 8px; cursor: pointer; }
</style>
