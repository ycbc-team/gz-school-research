<script setup lang="ts">
import { computed } from 'vue';
import {
  summarizeSchools,
  ADCODE_TO_DISTRICT,
} from '@gz/shared';
import {
  primarySchools,
  middleSchools,
  highSchools,
  tier1Schools,
  middleTier1Schools,
} from '../data';

const primarySum = summarizeSchools(primarySchools.schools);
const middleSum = summarizeSchools(middleSchools.schools);
const highSum = summarizeSchools(highSchools.schools);

const stats = computed(() => [
  { label: '小学点位', value: primarySum.total, sub: topDistricts(primarySum.byDistrict) },
  { label: '初中点位', value: middleSum.total, sub: topDistricts(middleSum.byDistrict) },
  { label: '高中点位', value: highSum.total, sub: topDistricts(highSum.byDistrict) },
  { label: '口碑核验', value: tier1Schools.length + middleTier1Schools.length, sub: `小学 ${tier1Schools.length} · 初中 ${middleTier1Schools.length}` },
]);

function topDistricts(by: Array<{ name: string; count: number }>): string {
  return by.slice(0, 3).map((d) => `${d.name} ${d.count}`).join(' · ');
}
const districtTotal = (schools: typeof primarySchools.schools) => {
  const set = new Set(schools.map((s) => s.adcode).filter((a) => a in ADCODE_TO_DISTRICT));
  return set.size;
};
</script>

<template>
  <section>
    <h1 class="page-title">为孩子寻找合适升学路线的调研工具集</h1>
    <p class="page-sub">数据共享自项目 <code>data/</code> 目录（JSON 唯一真源），覆盖广州 7 区 · {{ districtTotal(primarySchools.schools) }} 区小学 + {{ districtTotal(middleSchools.schools) }} 区初中 + {{ districtTotal(highSchools.schools) }} 区高中</p>

    <div class="stats">
      <div class="stat" v-for="s in stats" :key="s.label">
        <div class="stat-value">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-sub">{{ s.sub }}</div>
      </div>
    </div>

    <div class="features">
      <RouterLink to="/map" class="feature">
        <div class="feature-name">七区中小学·高中分布地图</div>
        <div class="feature-desc">点位分布 · 区筛选 · 口碑梯队标注（Vue3 + Leaflet）</div>
        <span class="tag tag-new">新版</span>
      </RouterLink>
      <RouterLink to="/support" class="feature">
        <div class="feature-name">口碑学校 · 支撑度核验</div>
        <div class="feature-desc">小学 {{ tier1Schools.length }} 所 + 初中 {{ middleTier1Schools.length }} 所网传名校核验</div>
        <span class="tag tag-new">新版</span>
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.page-title { font-size: 20px; font-weight: 700; }
.page-sub { font-size: 13px; color: #6b7280; margin-top: 8px; line-height: 1.6; }
.page-sub code { background: #e8e7e1; border-radius: 4px; padding: 1px 6px; }

.stats { display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0; }
.stat {
  flex: 1 1 160px; min-width: 0;
  background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 14px 16px;
}
.stat-value { font-size: 26px; font-weight: 700; color: #3a5396; }
.stat-label { font-size: 13px; color: #1a1b1c; margin-top: 2px; font-weight: 600; }
.stat-sub { font-size: 12px; color: #6b7280; margin-top: 4px; }

.features { display: flex; flex-direction: column; gap: 12px; }
.feature {
  display: block; text-decoration: none; color: #1a1b1c;
  background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 16px 18px;
}
.feature:hover { border-color: #9bbbf4; }
.feature-name { font-size: 15px; font-weight: 600; }
.feature-desc { font-size: 12px; color: #6b7280; margin-top: 6px; line-height: 1.6; }
.tag {
  display: inline-block; margin-top: 10px; font-size: 11px;
  border-radius: 999px; padding: 2px 10px;
}
.tag-new { color: #2f7d1f; background: #e6f4e6; }
.tag-old { color: #8a5a00; background: #fdf3e3; }
</style>
