<script setup lang="ts">
/**
 * 学校详情页（三学段统一）：
 * - 小学：口碑/法人核验 + 小升初机制 + 2026 招生计划
 * - 初中：口碑/法人核验 + 升学通道（名额分配 21 校区 + 自招/体育/艺术 + 第二批次录取分数）
 * - 高中：分类/校区/出口数据（录取线·高分段·特控率，网传口径标注）+ 名额分配覆盖初中
 * 数据真源：data/ 各 JSON（apps/web/src/data 加载），链路数据为 2026 官方发布。
 */
import { computed } from 'vue';
import { useRouter } from 'vue-router';
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
  matchEnrollment,
  middleQuotaSummary,
  middlePrimaryFeed,
  schoolBadges,
  supportBadge,
} from '../data';
import LinkagePanel from '../components/LinkagePanel.vue';

const props = defineProps<{ stage: SchoolStage; name: string }>();
const schoolName = computed(() => decodeURIComponent(props.name || ''));
const router = useRouter();
/** 返回上一级（无历史则回地图） */
function goBack() {
  if (window.history.length > 1) router.back();
  else router.push('/map');
}
/** 在地图中查看：跳转地图并定位到本校 */
function viewOnMap() {
  router.push({ path: '/map', query: { focus: schoolName.value } });
}

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
/* ========== 小学：升学路线（对口初中 · 派位/直升） ========== */
const feedJuniors = computed(() => {
  if (props.stage !== 'primary') return null;
  const xs = tier.value?.xiaoshengchu;
  if (!xs) return null;
  return { group: xs.group, feed_junior_highs: xs.feed_junior_highs || [], direct_feed: xs.direct_feed, source_note: xs.source_note };
});
const feedRows = computed(() => {
  const f = feedJuniors.value;
  if (!f) return [];  return f.feed_junior_highs.map((name) => {
    const q = middleQuotaSummary(name);
    return { name, summary: q ? `省市属 ${q.sheng_quota ?? 0} · 名额考生 ${q.kaosheng ?? '—'}` : null, hasQuota: !!q };
  });
});

/* ========== 初中：生源小学反查 ========== */
const feedPrimarys = computed(() => {
  if (props.stage !== 'middle') return [];
  return middlePrimaryFeed(schoolName.value);
});

/* ========== 高中：出口数据（升学路径覆盖由 LinkagePanel 承载） ========== */
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

/* ========== 其他 ========== */
const badges = computed<{ text: string; cls: string }[]>(() =>
  schoolBadges(props.stage, { district: districtOf.value, tier: tier.value, rec: rec.value, name: schoolName.value }),
);
const support = computed(() => supportBadge(tier.value));
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
    <button class="back" @click="goBack">← 返回</button>
    <button class="back" style="margin-left:12px;" @click="viewOnMap">在地图中查看</button>

    <header class="d-head">
      <h1>{{ schoolName }}</h1>
      <div class="badges">
        <span v-for="b in badges" :key="b.cls + b.text" class="badge" :class="b.cls">{{ b.text }}</span>
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

    <!-- 口碑信号（民间口径，非官方评价） -->
    <div v-if="signalRows.length" class="card">
      <div class="card-title">
        口碑信号
        <span v-if="support" class="badge sm" :class="support.cls">{{ support.text }}</span>
        <span class="title-note">民间口径，非官方评价，仅供参考。</span>
      </div>
      <div class="kv">
        <div class="kv-row" v-for="r in signalRows" :key="r.label">
          <span>{{ r.label }}</span><b>{{ r.value }}</b>
        </div>
      </div>
      <p v-if="tierNote" class="sub-note">{{ tierNote }}</p>
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
      <p v-else class="empty">未在 2026 招生计划中匹配到招生地段（数据覆盖越秀/荔湾/海珠/天河/番禺/白云/黄埔七区；部分校名变体如分校区、新建校暂缺，后续补录）。</p>
    </div>

    <!-- 小学：升学路线（对口初中 · 派位/直升） -->
    <div v-if="stage === 'primary' && feedRows.length" class="card">
      <div class="card-title">升学路线 · 对口初中{{ feedJuniors?.group ? `（${feedJuniors.group}派位）` : '（对口直升）' }}</div>
      <p v-if="feedJuniors?.direct_feed" class="sub-note">直升：{{ feedJuniors.direct_feed }}</p>
      <div class="feed-list">
        <div v-for="r in feedRows" :key="r.name" class="feed-item">
          <RouterLink :to="`/school/middle/${encodeURIComponent(r.name)}`" class="feed-name">{{ r.name }}</RouterLink>
          <span v-if="r.summary" class="tag">{{ r.summary }}</span>
          <span v-else class="tag tag-dim">区属初中</span>
        </div>
      </div>
      <p v-if="feedJuniors?.source_note" class="sub-note" style="margin-top:8px;">{{ feedJuniors.source_note }}</p>
      <p class="sub-note" style="margin-top:4px;">点击初中可查看该校升学通道详情。</p>
    </div>

    <!-- 小学：小升初机制 -->
    <div v-if="stage === 'primary' && primaryMechanism" class="card">
      <div class="card-title">所在区小升初机制</div>
      <p class="note-text">{{ primaryMechanism }}</p>
    </div>

    <!-- 初中：招生 · 生源小学 -->
    <div v-if="stage === 'middle' && feedPrimarys.length" class="card">
      <div class="card-title">招生 · 生源小学</div>
      <p class="sub-note">以下口碑小学的对口初中包含本校（按小学划片/直升关系反查，非全量招生地段）。</p>
      <div class="feed-list">
        <div v-for="r in feedPrimarys" :key="r.primary" class="feed-item">
          <RouterLink :to="`/school/primary/${encodeURIComponent(r.primary)}`" class="feed-name">{{ r.primary }}</RouterLink>
          <span class="tag tag-dim">{{ r.direct_feed ? '对口直升' : (r.group ? r.group + '派位' : '对口') }}</span>
        </div>
      </div>
    </div>

    <!-- 初中：升学通道（LinkagePanel 公共组件） -->
    <template v-if="stage === 'middle'">
      <LinkagePanel :stage="'middle'" :school="schoolName" />
    </template>

    <!-- 高中：出口数据 + 升学路径覆盖（LinkagePanel 公共组件） -->
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

      <LinkagePanel :stage="'high'" :school="schoolName" />

      <div class="card" v-if="rec?.campuses?.length">
        <div class="card-title">校区</div>
        <ul class="campus-list">
          <li v-for="c in rec.campuses" :key="c">{{ c }}</li>
        </ul>
      </div>
    </template>

    <footer class="d-foot">
      <button class="back" @click="goBack">← 返回</button>
    <button class="back" style="margin-left:12px;" @click="viewOnMap">在地图中查看</button>
      <RouterLink v-if="stage === 'middle'" to="/linkage" class="back">升学路径总览 →</RouterLink>
    </footer>
  </section>
</template>

<style scoped>
.detail { max-width: 720px; margin: 0 auto; }
.back { display: inline-block; color: #1a6bd6; text-decoration: none; font-size: 13px; margin-bottom: 10px; background: none; border: none; cursor: pointer; font-family: inherit; padding: 0; }
.back:hover { text-decoration: underline; }
.d-head { margin-bottom: 14px; }
.d-head h1 { font-size: 20px; font-weight: 700; margin: 0 0 8px; line-height: 1.4; }
.badges { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.badge { font-size: 12px; font-weight: 700; color: #fff; border-radius: 6px; padding: 2px 9px; }
.stage { font-size: 12px; color: #6b7280; }

.badge.sm { font-size: 10.5px; padding: 1px 7px; vertical-align: middle; margin-left: 6px; }
.title-note { font-size: 11px; color: #9aa0a6; font-weight: 400; margin-left: 8px; }

.badge.b-district { background: #e5e7eb; color: #374151; }
.badge.b-stage { background: #dbeafe; color: #1e40af; }
.badge.b-tier { background: #e11d48; }
.badge.b-license { background: #4b5563; }
.badge.b-hcity { background: #b45309; }
.badge.b-hdist { background: #0f766e; }
.badge.b-full { background: #e11d48; }
.badge.b-part { background: #f59e0b; }
.badge.b-none { background: #8a94a6; }

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
.kv-row > b.strong { color: #1a1b1c; }

.zone-block { margin-top: 10px; }
.zone-label { font-size: 11px; color: #6b7280; font-weight: 600; margin-bottom: 4px; }
.zone-block p {
  margin: 0; background: #f7f6f2; border-radius: 8px; padding: 8px 10px;
  font-size: 12px; color: #444; line-height: 1.7;
}

.feed-list { display: flex; flex-direction: column; gap: 6px; }
.feed-item { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12.5px; }
.feed-name { color: #1a6bd6; text-decoration: none; font-weight: 500; }
.feed-name:hover { text-decoration: underline; }
.tag { font-size: 11px; color: #6b7280; background: #f1f0ec; border-radius: 5px; padding: 2px 8px; font-variant-numeric: tabular-nums; }
.tag-dim { color: #9aa0a6; }

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
