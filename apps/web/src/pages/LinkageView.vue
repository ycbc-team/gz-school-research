<script setup lang="ts">
/**
 * 升学路径页：
 * - 三学段链路示意（小学 → 初中 → 高中，四通道：名额分配/自招/体育/艺术）
 * - 初中视角：选择初中 → 四通道拆解（21 省市属校区名额 + 特殊通道 + 录取分数）
 * - 高中视角：选择省市属校区 → 名额分配覆盖初中 Top + 特殊通道覆盖
 * 合规口径：对外以"名额分配/录取分数/招生计划"官方数据为主，梯队与特控率为内部权重。
 */
import { computed, ref } from 'vue';
import {
  quotaMatrix,
  specialMatrix,
  batch2Scores,
  CAMPUS_SHORT,
  CAMPUS_SCHOOL,
  CAMPUS_TO_SPECIAL,
  CAMPUS_TO_BATCH2,
  quotaCoverage,
  specialCoverage,
} from '../data';

const ALL_SCHOOLS = [...quotaMatrix.schools].sort((a, b) => a.school.localeCompare(b.school, 'zh'));

/* ========== 初中视角 ========== */
const kw = ref('');
const middleSel = ref<string>(ALL_SCHOOLS.find((s) => s.school === '广州市第一中学')?.school || ALL_SCHOOLS[0]?.school || '');
const filteredSchools = computed(() => {
  const k = kw.value.trim();
  if (!k) return [];
  return ALL_SCHOOLS.filter((s) => s.school.includes(k)).slice(0, 12);
});
const selectedSchool = computed(() => ALL_SCHOOLS.find((s) => s.school === middleSel.value));

const quotaRows = computed(() => {
  const q = selectedSchool.value;
  if (!q) return [];
  return CAMPUS_SHORT.filter((c) => (q.sz[c] ?? 0) > 0)
    .map((c) => ({ campus: c, n: q.sz[c] as number, max: q.sz_sum }))
    .sort((a, b) => b.n - a.n);
});
const specialRows = computed(() => {
  const m = selectedSchool.value ? specialMatrix.matrix[selectedSchool.value.school] : undefined;
  if (!m) return [];
  const toShort = (full: string) => {
    for (const [s, f] of Object.entries(CAMPUS_TO_SPECIAL)) if (f === full) return s;
    return full;
  };
  return Object.entries(m).map(([k, v]) => ({
    campus: toShort(k),
    autonomy: v.autonomy ?? 0,
    sports: v.sports ?? 0,
    arts: v.arts ?? 0,
  }));
});
const batchRows = computed(() => {
  const name = selectedSchool.value?.school;
  if (!name) return [];
  const toShort = (full: string) => {
    for (const [s, f] of Object.entries(CAMPUS_TO_BATCH2)) if (f === full) return s;
    return full;
  };
  const out: { campus: string; min: number | null | undefined; last: number | null | undefined }[] = [];
  for (const [campus, rows] of Object.entries(batch2Scores.data)) {
    if (rows[name]) out.push({ campus: toShort(campus), min: rows[name].min_score, last: rows[name].last_score });
  }
  return out;
});

/* ========== 高中视角 ========== */
const highSel = ref<string>(CAMPUS_SHORT[0]);
const highCoverage = computed(() => quotaCoverage(highSel.value, 15));
const highSpecial = computed(() => specialCoverage(highSel.value).slice(0, 15));
const highSchoolName = computed(() => CAMPUS_SCHOOL[highSel.value]);

/* ========== 通用 ========== */
const pickSchool = (name: string) => {
  middleSel.value = name;
  kw.value = '';
};
</script>

<template>
  <section class="linkage">
    <h1>升学路径</h1>
    <p class="page-sub">小学 → 初中 → 高中的升学通道查询。数据为 2026 年官方发布（名额分配计划 / 自招与特长名单 / 第二批次录取分数），各初中是否获得省市属示范高中通道、通道强度如何，一页看清。</p>

    <!-- 链路示意 -->
    <div class="chain">
      <div class="chain-node"><span class="cn-name">小学</span><span class="cn-sub">对口 · 直升 / 派位</span></div>
      <div class="chain-arrow">→</div>
      <div class="chain-node chain-mid"><span class="cn-name">初中</span><span class="cn-sub">升学通道 Q<sub>j</sub>：名额分配 + 自招 + 体育 + 艺术</span></div>
      <div class="chain-arrow">→</div>
      <div class="chain-node"><span class="cn-name">省市属高中</span><span class="cn-sub">21 校区 · 录取分/出口</span></div>
    </div>

    <!-- 初中视角 -->
    <div class="card">
      <div class="card-title">① 选初中 → 看升学通道</div>
      <div class="search">
        <input v-model="kw" placeholder="输入初中校名（如：广州市第一中学）" class="search-input" />
        <ul v-if="filteredSchools.length" class="search-list">
          <li v-for="s in filteredSchools" :key="s.school" @mousedown.prevent="pickSchool(s.school)">{{ s.school }}</li>
        </ul>
      </div>

      <div v-if="selectedSchool" class="sel-school">
        <b>{{ selectedSchool.school }}</b>
        <span v-if="selectedSchool.district" class="tag">{{ selectedSchool.district }}</span>
        <span class="tag">名额考生 {{ selectedSchool.kaosheng ?? '—' }}</span>
        <RouterLink :to="`/school/middle/${encodeURIComponent(selectedSchool.school)}`" class="detail-link">学校详情 →</RouterLink>
      </div>

      <div v-if="quotaRows.length" class="block">
        <div class="block-title">名额分配 · 21 省市属校区（2026，n<sub>ji</sub>）</div>
        <div class="bars">
          <div v-for="r in quotaRows" :key="r.campus" class="bar-row">
            <span class="bar-name">{{ r.campus }}</span>
            <span class="bar-track"><i class="bar-fill" :style="{ width: Math.round((r.n / quotaRows[0]!.n) * 100) + '%' }"></i></span>
            <span class="bar-val">{{ r.n }}</span>
          </div>
        </div>
      </div>

      <div v-if="specialRows.length" class="block">
        <div class="block-title">特殊通道（自招 / 体育 / 艺术 · 2026 名单人数）</div>
        <div class="tbl">
          <div class="tbl-row tbl-head"><span>校区</span><span>自招</span><span>体育</span><span>艺术</span><span>合计</span></div>
          <div v-for="r in specialRows" :key="r.campus" class="tbl-row">
            <span>{{ r.campus }}</span><span>{{ r.autonomy }}</span><span>{{ r.sports }}</span><span>{{ r.arts }}</span><span class="strong">{{ r.autonomy + r.sports + r.arts }}</span>
          </div>
        </div>
      </div>

      <div v-if="batchRows.length" class="block">
        <div class="block-title">第二批次录取分数（2026 · 按初中学校排序）</div>
        <div class="tbl">
          <div class="tbl-row tbl-head"><span>校区</span><span>录取最低分</span><span>末位考生分</span></div>
          <div v-for="r in batchRows" :key="r.campus" class="tbl-row">
            <span>{{ r.campus }}</span><span>{{ r.min ?? '—' }}</span><span>{{ r.last ?? '—' }}</span>
          </div>
        </div>
      </div>

      <p v-if="selectedSchool && !quotaRows.length && !specialRows.length && !batchRows.length" class="empty">
        该初中暂未匹配到省市属高中通道数据。
      </p>
    </div>

    <!-- 高中视角 -->
    <div class="card">
      <div class="card-title">② 选省市属校区 → 看名额覆盖</div>
      <div class="chips">
        <button
          v-for="c in CAMPUS_SHORT"
          :key="c"
          class="chip"
          :class="{ on: c === highSel }"
          @click="highSel = c"
        >{{ c }}</button>
      </div>
      <p class="sub-note">当前：{{ highSchoolName }} · {{ highSel }}校区</p>

      <div v-if="highCoverage.length" class="block">
        <div class="block-title">名额分配覆盖初中 Top 15（n<sub>ji</sub> 降序）</div>
        <div class="tbl">
          <div class="tbl-row tbl-head"><span>初中</span><span>所在区</span><span>名额</span></div>
          <div v-for="r in highCoverage" :key="r.school" class="tbl-row">
            <span><RouterLink :to="`/school/middle/${encodeURIComponent(r.school)}`" class="sch-link">{{ r.school }}</RouterLink></span>
            <span>{{ r.district || '—' }}</span><span class="strong">{{ r.n }}</span>
          </div>
        </div>
      </div>

      <div v-if="highSpecial.length" class="block">
        <div class="block-title">特殊通道覆盖初中 Top 15（自招 / 体育 / 艺术）</div>
        <div class="tbl">
          <div class="tbl-row tbl-head"><span>初中</span><span>自招</span><span>体育</span><span>艺术</span></div>
          <div v-for="r in highSpecial" :key="r.school" class="tbl-row">
            <span>{{ r.school }}</span><span>{{ r.autonomy }}</span><span>{{ r.sports }}</span><span>{{ r.arts }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 口径 -->
    <div class="card note-card">
      <div class="card-title">口径说明</div>
      <ul class="notes">
        <li>名额分配：2026 年广州市高中名额分配计划（第一批），n<sub>ji</sub>=A 高中分配给 B 初中的名额数；"名额考生数"为该初中符合名额分配资格的考生数。</li>
        <li>自招：省市属高中综合能力考核资格名单（考核前 ≤5 倍计划，非最终预录取）；体育/艺术：专业测试通过名单。</li>
        <li>第二批次录取分数：官方"按初中学校排序"发布，含录取最低分与末位考生分；缺省表示有指标但无考生完成录取。</li>
        <li>内部评估模型：Q<sub>j</sub> = Σ(n<sub>ji</sub>/m<sub>j</sub> × H<sub>i</sub> × α) + 自招 + 体育 + 艺术（α 与特控率口径尚待定，暂不对外展示数值）。</li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.linkage { max-width: 760px; margin: 0 auto; }
h1 { font-size: 20px; font-weight: 700; margin: 0 0 8px; }
.page-sub { font-size: 13px; color: #6b7280; line-height: 1.7; margin: 0 0 16px; }

.chain {
  display: flex; align-items: stretch; gap: 6px; flex-wrap: wrap;
  background: #fff; border: 1px solid #e4e3dd; border-radius: 14px;
  padding: 12px 14px; margin-bottom: 12px;
}
.chain-node {
  flex: 1 1 130px; min-width: 0; padding: 10px; background: rgba(155,187,244,0.1);
  border: 1px solid rgba(155,187,244,0.4); border-radius: 10px; text-align: center;
}
.chain-node.chain-mid { background: rgba(220,38,38,0.06); border-color: rgba(220,38,38,0.3); }
.cn-name { display: block; font-size: 13px; font-weight: 700; color: #1a1b1c; }
.cn-sub { display: block; font-size: 11px; color: #6b7280; margin-top: 4px; line-height: 1.5; }
.chain-arrow { flex: none; align-self: center; font-size: 15px; color: #9bbbf4; }

.card { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; padding: 14px 16px; margin-bottom: 12px; }
.card-title { font-size: 13px; font-weight: 700; margin-bottom: 10px; }
.sub-note { font-size: 11.5px; color: #9aa0a6; line-height: 1.6; margin: 6px 0 10px; }
.empty { font-size: 12.5px; color: #9aa0a6; margin: 4px 0; line-height: 1.6; }

.search { position: relative; }
.search-input {
  width: 100%; box-sizing: border-box; padding: 8px 12px; font-size: 13px;
  border: 1px solid #d6d4cc; border-radius: 8px; outline: none;
}
.search-input:focus { border-color: #9bbbf4; box-shadow: 0 0 0 2px rgba(155,187,244,0.2); }
.search-list {
  position: absolute; z-index: 20; top: calc(100% + 4px); left: 0; right: 0; margin: 0; padding: 4px 0;
  background: #fff; border: 1px solid #e4e3dd; border-radius: 8px; list-style: none;
  max-height: 220px; overflow-y: auto; box-shadow: 0 6px 20px rgba(20,30,50,0.12);
}
.search-list li { padding: 7px 12px; font-size: 12.5px; cursor: pointer; }
.search-list li:hover { background: #f2f7ff; color: #1a6bd6; }

.sel-school { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 12px; font-size: 13px; }
.sel-school b { font-size: 14px; }
.tag { font-size: 11px; color: #6b7280; background: #f1f0ec; border-radius: 5px; padding: 2px 8px; }
.detail-link { margin-left: auto; color: #1a6bd6; font-size: 12.5px; text-decoration: none; }
.detail-link:hover { text-decoration: underline; }

.block { margin-top: 14px; }
.block-title { font-size: 12px; font-weight: 700; color: #444; margin-bottom: 8px; }

.bars { display: flex; flex-direction: column; gap: 5px; }
.bar-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.bar-name { flex: none; width: 76px; color: #6b7280; font-size: 11.5px; }
.bar-track { flex: 1; height: 12px; background: #f1f0ec; border-radius: 6px; overflow: hidden; }
.bar-fill { display: block; height: 100%; background: #9bbbf4; border-radius: 6px; }
.bar-val { flex: none; width: 26px; text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }

.tbl { display: flex; flex-direction: column; gap: 4px; }
.tbl-row { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 4px 6px; border-radius: 6px; }
.tbl-row > span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tbl-row > span:nth-child(n+2) { flex: none; width: 52px; text-align: right; font-variant-numeric: tabular-nums; }
.tbl-row .strong { color: #1a6bd6; font-weight: 700; }
.tbl-head { background: #f7f6f2; font-size: 11px; color: #6b7280; font-weight: 600; }
.tbl-head > span { color: #6b7280; }
.sch-link { color: #1a6bd6; text-decoration: none; }
.sch-link:hover { text-decoration: underline; }

.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  font-size: 11.5px; padding: 4px 10px; border: 1px solid #d6d4cc; background: #fff;
  border-radius: 999px; color: #444; cursor: pointer;
}
.chip:hover { border-color: #9bbbf4; }
.chip.on { background: #9bbbf4; border-color: #9bbbf4; color: #fff; font-weight: 600; }

.note-card { background: #fafaf8; }
.notes { margin: 0; padding-left: 18px; font-size: 12px; color: #6b7280; line-height: 1.8; }

@media (max-width: 600px) {
  .bar-name { width: 64px; }
  .chain { flex-direction: column; }
  .chain-arrow { transform: rotate(90deg); align-self: center; }
}
</style>
