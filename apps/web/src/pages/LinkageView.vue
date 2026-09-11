<script setup lang="ts">
/**
 * 升学路径页（查询总览）：
 * - 三学段链路示意（小学 → 初中 → 高中，四通道：名额分配/自招/体育/艺术）
 * - ① 初中视角：搜索选择初中 → LinkagePanel 展示四通道拆解
 * - ② 高中视角：选择省市属学校/校区 → LinkagePanel 展示名额分配覆盖 + 特殊通道覆盖
 * 与学校详情页共用 LinkagePanel 组件（此处带选择器，详情页指定当前学校）。
 * 合规口径：对外以"名额分配/录取分数/招生计划"官方数据为主，梯队与特控率为内部权重。
 */
import { computed, ref } from 'vue';
import { quotaMatrix, CAMPUS_SHORT, CAMPUS_SCHOOL } from '../data';
import LinkagePanel from '../components/LinkagePanel.vue';

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

/* ========== 高中视角 ========== */
const highSel = ref<string>(CAMPUS_SHORT[0]);
const highSchoolName = computed(() => CAMPUS_SCHOOL[highSel.value] || highSel.value);

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
        <RouterLink :to="`/school/${encodeURIComponent(selectedSchool.school)}?stage=middle`" class="detail-link">学校详情 →</RouterLink>
      </div>

      <LinkagePanel v-if="selectedSchool" :stage="'middle'" :school="selectedSchool.school" />
    </div>

    <!-- 高中视角 -->
    <div class="card">
      <div class="card-title">② 选省市属学校 → 看名额覆盖</div>
      <div class="chips">
        <button
          v-for="c in CAMPUS_SHORT"
          :key="c"
          class="chip"
          :class="{ on: c === highSel }"
          @click="highSel = c"
        >{{ c }}</button>
      </div>
      <p class="sub-note">当前：{{ highSchoolName }} · {{ highSel }}校区（按学校聚合全部校区展示）</p>

      <LinkagePanel :stage="'high'" :school="highSchoolName" />
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
