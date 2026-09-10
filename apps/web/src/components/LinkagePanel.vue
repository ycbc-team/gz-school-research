<script setup lang="ts">
/**
 * 升学路径面板（公共组件）：
 * - stage='middle'：指定初中的四通道升学数据（名额分配 21 校区 / 自招·体育·艺术 / 第二批次录取分数）
 * - stage='high'：指定高中的名额分配覆盖初中 + 特殊通道覆盖（按学校聚合全部校区）
 * 用于：学校详情页（school 由路由指定）与升学路径查询页（school 由搜索/选择器指定）。
 * 数据真源：data/linkage/（2026 官方发布）。
 */
import { computed } from 'vue';
import {
  CAMPUS_SHORT,
  CAMPUS_SCHOOL,
  CAMPUS_TO_SPECIAL,
  CAMPUS_TO_BATCH2,
  linkageOf,
  specialOf,
  batch2Of,
  quotaCoverage,
  specialCoverage,
} from '../data';

const props = defineProps<{ stage: 'middle' | 'high'; school: string }>();
const schoolName = computed(() => decodeURIComponent(props.school || ''));

/* ========== 初中：四通道 ========== */
const quota = computed(() => (props.stage === 'middle' ? linkageOf(schoolName.value) : undefined));
const quotaRows = computed(() => {
  const q = quota.value;
  if (!q) return [];
  return CAMPUS_SHORT.filter((c) => (q.sz[c] ?? 0) > 0)
    .map((c) => ({ campus: c, n: q.sz[c] as number }))
    .sort((a, b) => b.n - a.n);
});
const specialKeyToShort = (spKey: string) => {
  for (const [short, full] of Object.entries(CAMPUS_TO_SPECIAL)) if (full === spKey) return short;
  return spKey;
};
const batchKeyToShort = (bk: string) => {
  for (const [short, full] of Object.entries(CAMPUS_TO_BATCH2)) if (full === bk) return short;
  return bk;
};
const specialRows = computed(() => {
  const m = specialOf(schoolName.value);
  if (!m) return [];
  return Object.entries(m).map(([k, v]) => ({
    campus: specialKeyToShort(k),
    autonomy: v.autonomy ?? 0,
    sports: v.sports ?? 0,
    arts: v.arts ?? 0,
  }));
});
const specialTotal = computed(() =>
  specialRows.value.reduce((s, r) => s + r.autonomy + r.sports + r.arts, 0),
);
const batchRows = computed(() => {
  const m = batch2Of(schoolName.value);
  return Object.entries(m).map(([k, v]) => ({
    campus: batchKeyToShort(k),
    min: v.min_score,
    last: v.last_score,
  }));
});
const hasMiddleData = computed(() => !!quota.value || specialTotal.value > 0 || batchRows.value.length > 0);
/** 校区简称 → 高中全名（路由用） */
function schoolOf(campus: string): string {
  return (CAMPUS_SCHOOL as Record<string, string>)[campus] ?? campus;
}

/** 第二批次合并表：名额（quota）+ 录取最低分（batch2）按校区对齐 */
const batchMerged = computed(() => {
  const qmap = new Map<string, number>(quotaRows.value.map((r) => [r.campus, r.n]));
  const bmap = new Map(batchRows.value.map((r) => [r.campus, r.min]));
  const all = [...new Set([...qmap.keys(), ...bmap.keys()])];
  return all
    .map((c) => ({ campus: c, school: schoolOf(c), n: qmap.get(c) ?? null, min: bmap.get(c) ?? null }))
    .sort((a, b) => (b.n ?? 0) - (a.n ?? 0));
});

/* ========== 高中：覆盖反查（按学校聚合校区） ========== */
const highShorts = computed(() =>
  props.stage === 'high' ? CAMPUS_SHORT.filter((c) => CAMPUS_SCHOOL[c] === schoolName.value) : [],
);
const highCoverage = computed(() => {
  const merged = new Map<string, { n: number; districts: Set<string> }>();
  for (const c of highShorts.value) {
    for (const { school, n, district } of quotaCoverage(c)) {
      const m = merged.get(school) || { n: 0, districts: new Set<string>() };
      m.n += n;
      if (district) m.districts.add(district);
      merged.set(school, m);
    }
  }
  return [...merged.entries()]
    .map(([school, v]) => ({ school, n: v.n, districts: [...v.districts] }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 30);
});
const highSpecialCoverage = computed(() => {
  const merged = new Map<string, { autonomy: number; sports: number; arts: number }>();
  for (const c of highShorts.value) {
    for (const s of specialCoverage(c)) {
      const m = merged.get(s.school) || { autonomy: 0, sports: 0, arts: 0 };
      m.autonomy += s.autonomy;
      m.sports += s.sports;
      m.arts += s.arts;
      merged.set(s.school, m);
    }
  }
  return [...merged.entries()]
    .map(([school, v]) => ({ school, ...v }))
    .sort((a, b) => b.autonomy + b.sports + b.arts - (a.autonomy + a.sports + a.arts))
    .slice(0, 30);
});
</script>

<template>
  <!-- ===== 初中视角：按录取批次组织 ===== -->
  <template v-if="stage === 'middle'">
    <div class="card" v-if="specialRows.length">
      <div class="card-title">第一批次 · 特殊通道（自招 / 体育 / 艺术）· 2026</div>
      <p class="sub-note">本校学生通过自招/体育/艺术被以下高中录取（资格名单人数，非最终预录取）。</p>
      <div class="tbl">
        <div class="tbl-row tbl-head"><span>升入高中</span><span>自招</span><span>体育</span><span>艺术</span><span>合计</span></div>
        <div v-for="r in specialRows" :key="r.campus" class="tbl-row">
          <span><RouterLink :to="`/school/high/${encodeURIComponent(schoolOf(r.campus))}`" class="sch-link">{{ r.campus }}</RouterLink></span><span>{{ r.autonomy }}</span><span>{{ r.sports }}</span><span>{{ r.arts }}</span><span class="strong">{{ r.autonomy + r.sports + r.arts }}</span>
        </div>
      </div>
    </div>

    <div class="card" v-if="quota">
      <div class="card-title">第二批次 · 名额分配（指标到校）· 2026（官方）</div>
      <p class="sub-note">本校名额考生按政策获得以下高中的名额；名额 = 该高中分给本校的名额数，录取最低分为本校考生被该校第二批次录取的最低分。省市属名额已全列；区属名额分配到本区区属高中，明细未收录。</p>
      <div class="kv">
        <div class="kv-row"><span>名额考生数</span><b>{{ quota.kaosheng ?? '—' }} 人</b></div>
        <div class="kv-row"><span>省市属名额</span><b>{{ quota.sheng_quota ?? '—' }} 个</b></div>
        <div class="kv-row"><span>区属名额</span><b>{{ quota.qu_quota ?? '—' }} 个</b></div>
      </div>
      <div v-if="batchMerged.length" class="tbl tbl-merged" style="margin-top:10px;">
        <div class="tbl-row tbl-head"><span>高中</span><span>名额</span><span>录取最低分</span></div>
        <div v-for="r in batchMerged" :key="r.campus" class="tbl-row">
          <span><RouterLink :to="`/school/high/${encodeURIComponent(r.school)}`" class="sch-link">{{ r.campus }}</RouterLink></span><span>{{ r.n ?? '—' }}</span><span>{{ r.min ?? '—' }}</span>
        </div>
      </div>
      <p class="sub-note" style="margin-top:8px;">第三批（省市属统招）、第四批（区属统招）按全市统一投档划线，官方不公布按初中学校的录取名单与分数，故不展示。</p>
    </div>

    <div class="card" v-if="!hasMiddleData">
      <div class="card-title">升学通道</div>
      <p class="empty">该初中暂未匹配到省市属高中升学通道数据（可能为未收录或非名额分配学校）。</p>
    </div>
  </template>

  <!-- ===== 高中视角：覆盖反查 ===== -->
  <template v-else>
    <div class="card" v-if="highCoverage.length">
      <div class="card-title">名额分配覆盖初中 · 2026（Top 30）</div>
      <p class="sub-note">按该高中各校区合计名额数（n<sub>ji</sub>）降序，合并展示。</p>
      <div class="tbl">
        <div class="tbl-row tbl-head"><span>初中</span><span>所在区</span><span>名额</span></div>
        <div v-for="r in highCoverage" :key="r.school" class="tbl-row">
          <span><RouterLink :to="`/school/middle/${encodeURIComponent(r.school)}`" class="sch-link">{{ r.school }}</RouterLink></span>
          <span>{{ r.districts.join('、') || '—' }}</span><span class="strong">{{ r.n }}</span>
        </div>
      </div>
    </div>

    <div class="card" v-if="highSpecialCoverage.length">
      <div class="card-title">特殊通道覆盖初中 · 2026（Top 30）</div>
      <div class="tbl">
        <div class="tbl-row tbl-head"><span>初中</span><span>自招</span><span>体育</span><span>艺术</span></div>
        <div v-for="r in highSpecialCoverage" :key="r.school" class="tbl-row">
          <span>{{ r.school }}</span><span>{{ r.autonomy }}</span><span>{{ r.sports }}</span><span>{{ r.arts }}</span>
        </div>
      </div>
    </div>

    <div class="card" v-if="!highCoverage.length && !highSpecialCoverage.length">
      <div class="card-title">升学通道</div>
      <p class="empty">暂未匹配到该校名额分配/特殊通道覆盖数据。</p>
    </div>
  </template>
</template>

<style scoped>
.card {
  background: #fff; border: 1px solid #e4e3dd; border-radius: 14px;
  padding: 14px 16px; margin-bottom: 12px;
}
.card-title { font-size: 13px; font-weight: 700; color: #1a1b1c; margin-bottom: 10px; }
.sub-note { font-size: 11px; color: #9aa0a6; line-height: 1.6; margin: 0 0 10px; }
.empty { font-size: 12.5px; color: #9aa0a6; margin: 4px 0; line-height: 1.6; }

.kv { display: flex; flex-direction: column; gap: 6px; }
.kv-row { display: flex; gap: 10px; font-size: 12.5px; align-items: baseline; }
.kv-row > span { flex: none; width: 100px; color: #6b7280; font-size: 11.5px; }
.kv-row > b { font-weight: 600; line-height: 1.6; }

.bars { display: flex; flex-direction: column; gap: 5px; margin-top: 10px; }
.bar-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.bar-name { flex: none; width: 76px; color: #6b7280; font-size: 11.5px; }
.bar-track { flex: 1; height: 12px; background: #f1f0ec; border-radius: 6px; overflow: hidden; }
.bar-fill { display: block; height: 100%; background: #9bbbf4; border-radius: 6px; }
.bar-val { flex: none; width: 26px; text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }

.tbl { display: flex; flex-direction: column; gap: 4px; }
.tbl-row { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 4px 6px; border-radius: 6px; }
.tbl-row > span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tbl-row > span:nth-child(n+2) { flex: none; width: 52px; text-align: right; font-variant-numeric: tabular-nums; }
.tbl-merged .tbl-row > span:nth-child(2) { width: 40px; }
.tbl-merged .tbl-row > span:nth-child(3) { width: 78px; }
.tbl-row .strong { color: #1a1b1c; font-weight: 700; }
.tbl-head { background: #f7f6f2; font-size: 11px; color: #6b7280; font-weight: 600; }
.tbl-head > span { color: #6b7280; }
.sch-link { color: #1a6bd6; text-decoration: none; }
.sch-link:hover { text-decoration: underline; }

@media (max-width: 600px) {
  .kv-row > span { width: 84px; }
  .bar-name { width: 64px; }
}
</style>
