<script setup lang="ts">
/**
 * 学校详情页（三学段统一）：
 * - 小学：口碑/法人核验 + 小升初机制 + 2026 招生计划
 * - 初中：口碑/法人核验 + 升学通道（名额分配 21 校区 + 自招/体育/艺术 + 第二批次录取分数）
 * - 高中：分类/校区/出口数据（录取线·高分段·特控率，网传口径标注）+ 名额分配覆盖初中
 * 数据真源：data/ 各 JSON（apps/web/src/data 加载），链路数据为 2026 官方发布。
 */
import { computed } from 'vue';
import type { SchoolStage } from '@gz/shared';
import {
  buildAliasTable,
  matchTier1ByPoiName,
  normName,
  formatPrimarySignals,
  formatMiddleSignals,
  type Tier1School,
  type HighLevelSchool,
} from '@gz/shared';
import {
  primarySchools,
  middleSchools,
  highSchools,
  primaryTier1,
  middleTier1,
  highLevels,
  tier1Schools,
  middleTier1Schools,
  enrollments,
  matchEnrollment,
  quotaMatrix,
  specialMatrix,
  batch2Scores,
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

const props = defineProps<{ stage: SchoolStage; name: string }>();
const schoolName = computed(() => decodeURIComponent(props.name || ''));

/* ========== 校名匹配（与 MapView 同套逻辑） ========== */
const tierTables = {
  primary: buildAliasTable(tier1Schools),
  middle: buildAliasTable(middleTier1Schools),
};
const tier = computed<Tier1School | undefined>(() => {
  if (props.stage === 'high') return undefined;
  return matchTier1ByPoiName(
    schoolName.value,
    props.stage === 'primary' ? tier1Schools : middleTier1Schools,
    tierTables[props.stage],
  );
});

const highTable = new Map<string, HighLevelSchool>();
for (const sc of highLevels.schools) {
  for (const k of [sc.name, ...(sc.aliases || []), ...(sc.campuses || [])]) {
    const nk = normName(k);
    if (nk && !highTable.has(nk)) highTable.set(nk, sc);
  }
}
const rec = computed<HighLevelSchool | undefined>(() => {
  if (props.stage !== 'high') return undefined;
  return highTable.get(normName(schoolName.value));
});

/* ========== 基本信息 ========== */
const poi = computed(() => {
  const list = props.stage === 'primary' ? primarySchools.schools : props.stage === 'middle' ? middleSchools.schools : highSchools.schools;
  return list.find((s) => s.name === schoolName.value) || null;
});
const stageLabel = computed(() => (props.stage === 'primary' ? '小学' : props.stage === 'middle' ? '初中' : '高中'));

const ADCODE_TO_DISTRICT: Record<string, string> = {
  '440103': '荔湾区', '440104': '越秀区', '440105': '海珠区', '440106': '天河区',
  '440111': '白云区', '440112': '黄埔区', '440113': '番禺区',
};
const districtOf = computed(() => {
  if (poi.value?.adcode) {
    const d = ADCODE_TO_DISTRICT[poi.value.adcode];
    if (d) return d;
  }
  if (props.stage === 'high' && rec.value?.district) return rec.value.district;
  return tier.value?.district || '—';
});

/* ========== 小学：2026 招生计划匹配（含对口地段 zone） ========== */
const enrollment = computed(() => {
  if (props.stage !== 'primary') return null;
  return matchEnrollment(schoolName.value);
});
const primaryMechanism = computed(() => {
  if (props.stage !== 'primary' || !poi.value) return null;
  const d = primaryTier1.districts;
  for (const k of Object.keys(d)) {
    if (schoolName.value.includes(k) && d[k]) return d[k].xiaoshengchu_mechanism || null;
  }
  return null;
});

/* ========== 初中：升学通道（linkage 2026） ========== */
const quota = computed(() => (props.stage === 'middle' ? linkageOf(schoolName.value) : undefined));
const quotaRows = computed(() => {
  const q = quota.value;
  if (!q) return [];
  return CAMPUS_SHORT.filter((c) => (q.sz[c] ?? 0) > 0)
    .map((c) => ({ campus: c, n: q.sz[c] as number }))
    .sort((a, b) => b.n - a.n);
});
/** special 全称 → quota 简称（反向映射） */
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

/* ========== 高中：出口数据 + 名额分配覆盖（反查） ========== */
const indRows = computed(() => {
  const r = rec.value;
  if (!r) return [];
  const ind = r.indicators || {};
  const rows: { label: string; value: string; strong?: boolean }[] = [];
  const put = (k: string, label: string, strong = false) => {
    const v = ind[k];
    if (v !== undefined && v !== null && v !== '') rows.push({ label, value: String(v), strong });
  };
  put('score_2025', '2025 中考录取线（户籍生）', true);
  put('gaofen_2026', '高分段 2026');
  put('gaofen_2025', '高分段 2025');
  put('tekong_2026', '特控线上线率 2026');
  put('tekong_2025', '特控线上线率 2025');
  put('note', '备注');
  return rows;
});
/** 该校各校区名额分配覆盖初中（n_ji 合并） */
const highCoverage = computed(() => {
  const r = rec.value;
  if (!r) return [];
  const shorts = CAMPUS_SHORT.filter((c) => CAMPUS_SCHOOL[c] === r.name);
  const merged = new Map<string, { n: number; districts: Set<string> }>();
  for (const c of shorts) {
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
/** 该校各校区特殊通道覆盖（自招/体育/艺术） */
const highSpecialCoverage = computed(() => {
  const r = rec.value;
  if (!r) return [];
  const shorts = CAMPUS_SHORT.filter((c) => CAMPUS_SCHOOL[c] === r.name);
  const merged = new Map<string, { autonomy: number; sports: number; arts: number }>();
  for (const c of shorts) {
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

/* ========== 其他 ========== */
const hasLinkage = computed(() => !!quota.value || specialTotal.value > 0 || batchRows.value.length > 0);
const badgeCls = computed(() => {
  if (props.stage === 'high') {
    const c = rec.value?.category;
    return c === '省市属示范' ? 'h-city' : c === '区属示范' ? 'h-dist' : 'h-normal';
  }
  const t = tier.value;
  if (t?.tier1_eligible === false) return 'license';
  const c = t?.conclusion;
  return c === '有支撑' ? 'tier-full' : c === '部分支撑' ? 'tier-part' : 'tier-none';
});
const badgeText = computed(() => {
  if (props.stage === 'high') return rec.value?.category || '普通高中';
  const t = tier.value;
  if (t?.tier1_eligible === false) return '独立法人挂牌校';
  return t?.conclusion || '普通学校';
});
const headText = computed(() => {
  if (props.stage === 'high') {
    const r = rec.value;
    return r ? `${r.demo || ''}${r.demo && r.affiliation ? ' · ' : ''}${r.affiliation || ''}${r.campuses?.length ? ` · ${r.campuses.length} 校区` : ''}`.trim() : '';
  }
  const t = tier.value;
  if (!t) return '';
  const parts: string[] = [];
  if (t.education_group) parts.push(`${t.education_group.name}（${t.education_group.role}）`);
  if (t.entity_relation) parts.push(t.entity_relation);
  return parts.join(' · ');
});
const signalRows = computed(() => {
  if (props.stage === 'primary') return tier.value ? formatPrimarySignals(tier.value) : [];
  if (props.stage === 'middle') return tier.value ? formatMiddleSignals(tier.value) : [];
  return [];
});
const tierNote = computed(() => {
  const t = tier.value;
  if (!t) return null;
  if (t.tier1_eligible === false) return t.exclude_reason || '网传口碑校，独立法人，未计入口碑学校';
  return t.conclusion_basis || null;
});
const legalEntityText = computed(() => {
  const le = tier.value?.legal_entity;
  if (!le || typeof le !== 'object') return '—';
  const leObj = le as { name?: unknown; type?: unknown };
  const name = leObj.name ? String(leObj.name) : '—';
  const type = leObj.type ? String(leObj.type) : '';
  return type ? `${name}（${type}）` : name;
});
</script>

<template>
  <section class="detail">
    <RouterLink to="/map" class="back">← 返回地图</RouterLink>

    <header class="d-head">
      <h1>{{ schoolName }}</h1>
      <div v-if="badgeText" class="badges">
        <span class="badge" :class="badgeCls">{{ badgeText }}</span>
        <span class="stage">{{ stageLabel }}</span>
      </div>
      <p v-if="headText" class="d-sub">{{ headText }}</p>
    </header>

    <!-- 基本信息 -->
    <div class="card">
      <div class="card-title">基本信息</div>
      <div class="kv">
        <div class="kv-row"><span>学段</span><b>{{ stageLabel }}</b></div>
        <div class="kv-row"><span>所属区</span><b>{{ districtOf }}</b></div>
        <div class="kv-row" v-if="tier?.district"><span>口碑归属</span><b>{{ tier.district }}</b></div>
        <div class="kv-row" v-if="poi?.lng"><span>坐标</span><b>{{ poi.lng.toFixed(5) }}, {{ poi.lat.toFixed(5) }}</b></div>
        <div class="kv-row" v-if="tier?.legal_entity"><span>法人实体</span><b>{{ legalEntityText }}</b></div>
      </div>
    </div>

    <!-- 小学：招生计划 + 对口地段 -->
    <div v-if="stage === 'primary'" class="card">
      <div class="card-title">2026 小学招生计划</div>
      <div v-if="enrollment" class="kv">
        <div class="kv-row"><span>计划班数</span><b>{{ enrollment.plan_classes ?? '—' }} 个班</b></div>
        <div class="kv-row" v-if="enrollment.nature"><span>办学性质</span><b>{{ enrollment.nature }}</b></div>
        <div class="kv-row" v-if="enrollment.source"><span>数据来源</span><b>{{ enrollment.source }}</b></div>
        <div v-if="enrollment.zone" class="zone-block">
          <div class="zone-label">招生地段（对口）</div>
          <p>{{ enrollment.zone }}</p>
        </div>
      </div>
      <p v-else class="empty">未在 2026 招生计划中匹配到招生地段（数据暂覆盖越秀/荔湾/海珠/天河/番禺五区；白云/黄埔及部分校名变体暂缺，后续补录）。</p>
    </div>

    <!-- 小学：小升初机制 -->
    <div v-if="stage === 'primary' && primaryMechanism" class="card">
      <div class="card-title">所在区小升初机制</div>
      <p class="note-text">{{ primaryMechanism }}</p>
    </div>

    <!-- 初中：升学通道（核心） -->
    <template v-if="stage === 'middle'">
      <div class="card" v-if="quota">
        <div class="card-title">名额分配 · 2026（官方）</div>
        <div class="kv">
          <div class="kv-row"><span>名额考生数</span><b>{{ quota.kaosheng ?? '—' }} 人</b></div>
          <div class="kv-row"><span>省市属名额</span><b>{{ quota.sheng_quota ?? '—' }} 个</b></div>
          <div class="kv-row"><span>区属名额</span><b>{{ quota.qu_quota ?? '—' }} 个</b></div>
        </div>
        <div v-if="quotaRows.length" class="bars">
          <div v-for="r in quotaRows" :key="r.campus" class="bar-row">
            <span class="bar-name">{{ r.campus }}</span>
            <span class="bar-track"><i class="bar-fill" :style="{ width: Math.round((r.n / quotaRows[0]!.n) * 100) + '%' }"></i></span>
            <span class="bar-val">{{ r.n }}</span>
          </div>
        </div>
        <p v-else class="empty">该初中未获得省市属示范高中名额分配。</p>
      </div>

      <div class="card" v-if="specialRows.length">
        <div class="card-title">特殊通道 · 2026（自招 / 体育 / 艺术）</div>
        <p class="sub-note">自招=综合能力考核资格名单（考核前名单，非最终预录取）；体育/艺术=专业测试通过名单。</p>
        <div class="tbl">
          <div class="tbl-row tbl-head"><span>校区</span><span>自招</span><span>体育</span><span>艺术</span><span>合计</span></div>
          <div v-for="r in specialRows" :key="r.campus" class="tbl-row">
            <span>{{ r.campus }}</span><span>{{ r.autonomy }}</span><span>{{ r.sports }}</span><span>{{ r.arts }}</span><span class="strong">{{ r.autonomy + r.sports + r.arts }}</span>
          </div>
        </div>
      </div>

      <div class="card" v-if="batchRows.length">
        <div class="card-title">第二批次录取分数 · 2026（按初中学校排序）</div>
        <div class="tbl">
          <div class="tbl-row tbl-head"><span>校区</span><span>录取最低分</span><span>末位考生分</span></div>
          <div v-for="r in batchRows" :key="r.campus" class="tbl-row">
            <span>{{ r.campus }}</span><span>{{ r.min ?? '—' }}</span><span>{{ r.last ?? '—' }}</span>
          </div>
        </div>
      </div>

      <div class="card" v-if="!hasLinkage">
        <div class="card-title">升学通道</div>
        <p class="empty">该初中暂未匹配到省市属高中升学通道数据（可能为未收录或非名额分配学校）。</p>
      </div>
    </template>

    <!-- 高中：出口数据 + 覆盖 -->
    <template v-if="stage === 'high'">
      <div class="card" v-if="indRows.length">
        <div class="card-title">出口数据</div>
        <div class="kv">
          <div class="kv-row" v-for="r in indRows" :key="r.label">
            <span>{{ r.label }}</span><b :class="{ strong: r.strong }">{{ r.value }}</b>
          </div>
        </div>
        <p class="sub-note">口径：录取线为官方发布；高分段/特控率为各校喜报或网传数据，非官方统一发布，仅供参考。</p>
      </div>

      <div class="card" v-if="highCoverage.length">
        <div class="card-title">名额分配覆盖初中 · 2026（Top 30）</div>
        <p class="sub-note">按该高中各校区合计名额数（n_ji）降序，合并展示。</p>
        <div class="tbl">
          <div class="tbl-row tbl-head"><span>初中</span><span>所在区</span><span>名额</span></div>
          <div v-for="r in highCoverage" :key="r.school" class="tbl-row">
            <span>{{ r.school }}</span><span>{{ r.districts.join('、') || '—' }}</span><span class="strong">{{ r.n }}</span>
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

      <div class="card" v-if="rec?.campuses?.length">
        <div class="card-title">校区</div>
        <ul class="campus-list">
          <li v-for="c in rec.campuses" :key="c">{{ c }}</li>
        </ul>
      </div>
    </template>

    <!-- 口碑信号（小学/初中） -->
    <div v-if="signalRows.length" class="card">
      <div class="card-title">口碑信号（民间口径，非官方评价）</div>
      <div class="kv">
        <div class="kv-row" v-for="r in signalRows" :key="r.label">
          <span>{{ r.label }}</span><b :class="{ strong: r.strong }">{{ r.value }}</b>
        </div>
      </div>
      <p v-if="tierNote" class="sub-note">{{ tierNote }}</p>
    </div>

    <footer class="d-foot">
      <RouterLink to="/map" class="back">← 返回地图</RouterLink>
      <RouterLink v-if="stage === 'middle'" to="/linkage" class="back">升学路径总览 →</RouterLink>
    </footer>
  </section>
</template>

<style scoped>
.detail { max-width: 720px; margin: 0 auto; }
.back { display: inline-block; color: #1a6bd6; text-decoration: none; font-size: 13px; margin-bottom: 10px; }
.back:hover { text-decoration: underline; }
.d-head { margin-bottom: 14px; }
.d-head h1 { font-size: 20px; font-weight: 700; margin: 0 0 8px; line-height: 1.4; }
.badges { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.badge { font-size: 12px; font-weight: 700; color: #fff; border-radius: 6px; padding: 2px 9px; }
.stage { font-size: 12px; color: #6b7280; }
.d-sub { font-size: 12.5px; color: #6b7280; margin: 8px 0 0; line-height: 1.6; }

.badge.tier-full { background: #e11d48; }
.badge.tier-part { background: #f59e0b; }
.badge.tier-none { background: #8a94a6; }
.badge.license { background: #4b5563; }
.badge.h-city { background: #b45309; }
.badge.h-dist { background: #0f766e; }
.badge.h-normal { background: #57534e; }

.card {
  background: #fff; border: 1px solid #e4e3dd; border-radius: 14px;
  padding: 14px 16px; margin-bottom: 12px;
}
.card-title { font-size: 13px; font-weight: 700; color: #1a1b1c; margin-bottom: 10px; }
.sub-note { font-size: 11px; color: #9aa0a6; line-height: 1.6; margin: 0 0 10px; }
.empty { font-size: 12.5px; color: #9aa0a6; margin: 4px 0; line-height: 1.6; }
.note-text { font-size: 12.5px; color: #444; margin: 0; line-height: 1.7; }

.kv { display: flex; flex-direction: column; gap: 6px; }
.kv-row { display: flex; gap: 10px; font-size: 12.5px; align-items: baseline; }
.kv-row > span { flex: none; width: 100px; color: #6b7280; font-size: 11.5px; }
.kv-row > b { font-weight: 600; line-height: 1.6; }
.kv-row > b.strong { color: #1a6bd6; }

.zone-block { margin-top: 10px; }
.zone-label { font-size: 11px; color: #6b7280; font-weight: 600; margin-bottom: 4px; }
.zone-block p {
  margin: 0; background: #f7f6f2; border-radius: 8px; padding: 8px 10px;
  font-size: 12px; color: #444; line-height: 1.7;
}

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
.tbl-row .strong { color: #1a6bd6; font-weight: 700; }
.tbl-head { background: #f7f6f2; font-size: 11px; color: #6b7280; font-weight: 600; }
.tbl-head > span { color: #6b7280; }

.campus-list { margin: 0; padding-left: 18px; font-size: 12.5px; color: #444; line-height: 1.8; }
.d-foot { display: flex; justify-content: space-between; margin-top: 6px; }

@media (max-width: 600px) {
  .kv-row > span { width: 84px; }
  .bar-name { width: 64px; }
}
</style>
