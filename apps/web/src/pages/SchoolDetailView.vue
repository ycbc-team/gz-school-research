<script setup lang="ts">
/**
 * 学校详情页（三学段统一）：
 * - 小学：口碑/法人核验 + 小升初机制 + 2026 招生计划
 * - 初中：口碑/法人核验 + 升学通道（名额分配 21 校区 + 自招/体育/艺术 + 第二批次录取分数）
 * - 高中：分类/校区/出口数据（录取线·高分段·特控率，网传口径标注）+ 名额分配覆盖初中
 * 数据真源：data/ 各 JSON（apps/web/src/data 加载），链路数据为 2026 官方发布。
 */
import { computed, ref, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import type { SchoolStage, SchoolPoi } from '@gz/shared';
import {
  buildAliasTable,
  matchTier1ByPoiName,
  normName,
  formatPrimarySignals,
  formatMiddleSignals,
  highScoreRows,
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
  entities,
  matchEnrollment,
  middleQuotaSummary,
  middlePrimaryFeed,
  xiaoshengchuOf,
  schoolBadges,
  supportBadge,
  scoresOfSchool,
  isComprehensive,
  brandGroupOf,
  type BrandUnit,
} from '../data';
import LinkagePanel from '../components/LinkagePanel.vue';

const props = defineProps<{ name: string; stage?: string }>();
const route = useRoute();
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

/* ========== 学部 tab：同一学校名可能跨多个学部（完中），内部 tab 切换 ========== */
const POI_LISTS: Record<SchoolStage, any[]> = {
  primary: primarySchools.schools, middle: middleSchools.schools, high: highSchools.schools,
};
const STAGE_LABEL: Record<SchoolStage, string> = { primary: '小学部', middle: '初中部', high: '高中部' };
/** 该校名在哪些学部有 POI 点位（同名即视为该学部实体） */
const availableStages = computed<SchoolStage[]>(() => {
  const out: SchoolStage[] = [];
  for (const s of ['primary', 'middle', 'high'] as SchoolStage[]) {
    if (POI_LISTS[s].some((p) => normName(p.name) === normName(schoolName.value))) out.push(s);
  }
  return out;
});
/** 当前激活学部 tab；默认 query.stage 或第一个可用学部 */
const activeStage = ref<SchoolStage>('primary');
/** 解析初始/切换学校后的 tab：URL query.stage 优先，否则第一个可用学部 */
function resolveStage(): SchoolStage {
  const q = route.query.stage as string | undefined;
  const preferred = (['primary', 'middle', 'high'].includes(q as string) ? q : undefined) as SchoolStage | undefined;
  return preferred || availableStages.value[0] || 'primary';
}
// 切换学校时：优先 URL 指定 stage，否则重置到第一个可用学部
watch(schoolName, () => {
  activeStage.value = resolveStage();
}, { immediate: true });
// URL query.stage 变化（同 name 跨学部跳转，如小学 tab 点升学初中）→ 切换对应 tab
watch(
  () => route.query.stage,
  (s) => {
    if (['primary', 'middle', 'high'].includes(s as string)) activeStage.value = s as SchoolStage;
  },
);
// 手动切 tab：同步 URL（replace，不堆历史），保证跳转/后退一致
function switchStage(s: SchoolStage) {
  activeStage.value = s;
  router.replace({ path: `/school/${encodeURIComponent(schoolName.value)}`, query: { stage: s } });
}
const stage = computed(() => activeStage.value);

/* ========== 校名匹配（与 MapView 同套逻辑） ========== */
const tierTables = {
  primary: buildAliasTable(tier1Schools, entities.entities),
  middle: buildAliasTable(middleTier1Schools, entities.entities),
};
const tier = computed<Tier1School | undefined>(() => {
  if (stage.value === 'high') return undefined;
  // 新开办学校无成绩：不参与口碑/挂牌判定（数据层 note 标记「新开办（年份）·待首届成绩」，
  // 避免「广东实验中学天河学校」等独立法人新校因前缀匹配被误判为本部口碑校）
  const poiList = stage.value === 'primary' ? primarySchools.schools : middleSchools.schools;
  const poi = poiList.find((s) => normName(s.name) === normName(schoolName.value));
  if (poi?.note && poi.note.includes('新开办')) return undefined;
  return matchTier1ByPoiName(
    schoolName.value,
    stage.value === 'primary' ? tier1Schools : middleTier1Schools,
    tierTables[stage.value],
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
  if (stage.value === 'high') return highTable.get(normName(schoolName.value));
  // 完中初中也展示其高中部省/市示范 badge
  if (stage.value === 'middle' && isComprehensive(schoolName.value)) {
    return highTable.get(normName(schoolName.value));
  }
  return undefined;
});

/* ========== 基本信息 ========== */
const poi = computed(() => {
  const list = stage.value === 'primary' ? primarySchools.schools : stage.value === 'middle' ? middleSchools.schools : highSchools.schools;
  return list.find((s) => s.name === schoolName.value) || null;
});
const stageLabel = computed(() => (stage.value === 'primary' ? '小学' : stage.value === 'middle' ? '初中' : '高中'));

const ADCODE_TO_DISTRICT: Record<string, string> = {
  '440103': '荔湾区', '440104': '越秀区', '440105': '海珠区', '440106': '天河区',
  '440111': '白云区', '440112': '黄埔区', '440113': '番禺区',
};
const districtOf = computed(() => {
  if (poi.value?.adcode) {
    const d = ADCODE_TO_DISTRICT[poi.value.adcode];
    if (d) return d;
  }
  if (stage.value === 'high' && rec.value?.district) return rec.value.district;
  return tier.value?.district || '—';
});

/* ========== 小学：2026 招生计划匹配（含对口地段 zone） ========== */
const enrollment = computed(() => {
  if (stage.value !== 'primary') return null;
  return matchEnrollment(schoolName.value);
});
const primaryMechanism = computed(() => {
  if (stage.value !== 'primary' || !poi.value) return null;
  const d = primaryTier1.districts;
  for (const k of Object.keys(d)) {
    if (schoolName.value.includes(k) && d[k]) return d[k].xiaoshengchu_mechanism || null;
  }
  return null;
});
/* ========== 小学：升学路线（对口初中 · 派位/直升，全量 xiaoshengchu_all 真源） ========== */
const GAP_MARKERS = ['待查', '未在', '缺口', '暂缺'];
/** 本校升学路线记录（全等匹配；跨区同名按 adcode 精确消歧） */
const xsRecord = computed(() =>
  stage.value === 'primary' ? xiaoshengchuOf(schoolName.value, poi.value?.adcode) : null,
);
const feedJuniors = computed(() => {
  if (stage.value !== 'primary') return null;
  const xs = xsRecord.value;
  if (!xs) return null;
  return {
    group: xs.group,
    feed_junior_highs: xs.feed_junior_highs || [],
    direct_feed: xs.direct_feed,
    source_note: xs.source_note,
  };
});
const feedGap = computed(() => {
  if (stage.value !== 'primary') return null;
  const xs = xsRecord.value;
  if (!xs) return '本校未进入 2026 公办小学对口/派位名单。民办校无公办对口名单，以官方摇号 / 直升政策为准；公办新建校或未收录点位以最新官方公告为准。';
  if (xs.direct_feed) return null;
  const f = xs.feed_junior_highs || [];
  if (!f.length) return `升学路线数据缺口：${xs.data_gaps || '官方未公布该校对口/派位初中'}。`;
  const placeholder = f.filter((n) => GAP_MARKERS.some((m) => n.includes(m)));
  if (placeholder.length) return `升学路线数据缺口：${placeholder.join('；')}`;
  return null;
});
const feedRows = computed(() => {
  const f = feedJuniors.value;
  if (!f) return [];
  return f.feed_junior_highs
    .filter((name) => !GAP_MARKERS.some((m) => name.includes(m)))
    .map((name) => {
      const q = middleQuotaSummary(name);
      return { name, summary: q ? `省市属 ${q.sheng_quota ?? 0} · 名额考生 ${q.kaosheng ?? '—'}` : null, hasQuota: !!q };
    });
});

/* ========== 初中：生源小学反查 ========== */
const feedPrimarys = computed(() => {
  if (stage.value !== 'middle') return [];
  return middlePrimaryFeed(schoolName.value);
});

/* ========== 高中：招生（中考录取线）与高考（网传成绩）分卡片 ========== */
function pickRows(keys: [string, string, boolean?][]) {
  const ind = rec.value?.indicators || {};
  const rows: { label: string; value: string; strong?: boolean }[] = [];
  for (const [k, label, strong] of keys) {
    const v = ind[k];
    if (v !== undefined && v !== null && v !== '') rows.push({ label, value: String(v), strong });
  }
  return rows;
}
/** 高中招生：中考录取线（官方，2025/2026 两年；公办户籍生 / 民办最低分口径） */
const admissionRows = computed(() =>
  highScoreRows(scoresOfSchool(schoolName.value, rec.value?.campuses || [])),
);
/** 高考信息：高分段/特控率（网传喜报） */
const gaokaoRows = computed(() =>
  pickRows([['gaofen_2026', '高分段 2026'], ['gaofen_2025', '高分段 2025'], ['tekong_2026', '特控线上线率 2026'], ['tekong_2025', '特控线上线率 2025'], ['note', '备注']]),
);

/* ========== 其他 ========== */
const badges = computed<{ text: string; cls: string }[]>(() =>
  schoolBadges(stage.value, { district: districtOf.value, tier: tier.value, rec: rec.value, name: schoolName.value, singleStage: true }),
);
const support = computed(() => supportBadge(tier.value));
const headText = computed(() => {
  if (stage.value === 'high') {
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
  if (stage.value === 'primary') return tier.value ? formatPrimarySignals(tier.value) : [];
  if (stage.value === 'middle') return tier.value ? formatMiddleSignals(tier.value) : [];
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

/* ========== 品牌关联（同品牌多校区/多法人，解释挂牌口径） ========== */
interface BrandRow {
  name: string;
  role: string;
  legal: 'same' | 'independent';
  district: string;
  stages: string[]; // 小学/初中/高中
  badge: { text: string; cls: string } | null;
  reason: string | null;
  isCurrent: boolean;
  link: string | null;
}
const brandCard = computed<{ brand: string; note?: string; groups: { key: string; title: string; rows: BrandRow[] }[] } | null>(() => {
  const g = brandGroupOf(schoolName.value);
  if (!g) return null;
  /** unit 核心名：先去「（别名）」内容再归一，用于与 POI 名精确匹配（如「广东实验中学天河学校（省实天河）」→「广东实验中学天河学校」；注意 normName 已去括号字符，须先剥别名） */
  const unitCoreNorm = (n: string): string => normName(n.replace(/[（(][^）)]*[）)]/g, ''));
  /** 该 unit 对应 POI 是否为新开办待成绩（note 含「新开办」），是则跳过口碑/挂牌判定 */
  const newOpeningOf = (stage: 'primary' | 'middle', un: string): boolean => {
    const list = stage === 'primary' ? primarySchools.schools : middleSchools.schools;
    return list.some((s) => normName(s.name) === un && !!s.note && s.note.includes('新开办'));
  };
  const rows: BrandRow[] = [];
  for (const u of g.units as BrandUnit[]) {
    const unitNorm = unitCoreNorm(u.name);
    const newM = newOpeningOf('middle', unitNorm);
    const newP = newOpeningOf('primary', unitNorm);
    const tierM = newM
      ? undefined
      : middleTier1Schools.find((s) => s.name === u.name) ||
        matchTier1ByPoiName(u.name, middleTier1Schools, tierTables.middle);
    const tierP = newP
      ? undefined
      : tier1Schools.find((s) => s.name === u.name) ||
        matchTier1ByPoiName(u.name, tier1Schools, tierTables.primary);
    const rec = highTable.get(normName(u.name));
    const poiNormExtras = (u.poi_names || []).map(normName).filter(Boolean);
    /** 学段命中：POI 名与单位核心名精确归一相等；或 poi_names 覆盖；或该学段的 tier1 别名命中（同法人校区/挂牌校点位） */
    const hasPoiFor = (list: SchoolPoi[], aliasSrc: Tier1School | undefined): boolean =>
      list.some((s) => {
        const pn = normName(s.name);
        if (pn === unitNorm || poiNormExtras.includes(pn)) return true;
        if (!aliasSrc) return false;
        if (normName(aliasSrc.name) === pn) return true;
        return (aliasSrc.aliases || []).some((a) => normName(a) === pn);
      });
    const stages: string[] = [];
    if (hasPoiFor(primarySchools.schools, tierP)) stages.push('小学');
    if (hasPoiFor(middleSchools.schools, tierM)) stages.push('初中');
    if (hasPoiFor(highSchools.schools, tierM || tierP)) stages.push('高中');
    if (!stages.length) {
      if (tierM) stages.push('初中');
      else if (tierP) stages.push('小学');
    }
    // 区：优先 POI adcode，其次 tier1 口径
    let district = '';
    const poiHit = [primarySchools, middleSchools, highSchools]
      .map((snap) => snap.schools.find((s) => normName(s.name) === unitNorm))
      .find(Boolean);
    if (poiHit?.adcode) district = ADCODE_TO_DISTRICT[poiHit.adcode] || '';
    if (!district) district = tierM?.district || tierP?.district || rec?.district || '';
    // 口碑/挂牌徽章（来自 tier1 口径）
    const tier = tierM || tierP;
    const badge = tier
      ? tier.tier1_eligible === false
        ? { text: '挂牌', cls: 'b-license' }
        : { text: '口碑', cls: 'b-tier' }
      : null;
    const reason = tierM?.exclude_reason || tierP?.exclude_reason || null;
    // 详情链接：优先当前学段 → 初中 → 高中 → 小学
    const stageToKey: Record<string, SchoolStage> = { 小学: 'primary', 初中: 'middle', 高中: 'high' };
    const order = [stage.value, ...(['primary', 'middle', 'high'] as SchoolStage[]).filter((s) => s !== stage.value)];
    const stageKey = order.find((k) => stages.includes(k === 'primary' ? '小学' : k === 'middle' ? '初中' : '高中')) || null;
    const link = stageKey ? `/school/${encodeURIComponent(u.name)}?stage=${stageKey}` : null;
    rows.push({
      name: u.name,
      role: u.role,
      legal: u.legal,
      district,
      stages,
      badge,
      reason,
      isCurrent: unitNorm === normName(schoolName.value),
      link,
    });
  }
  const groups: { key: string; title: string; rows: BrandRow[] }[] = [];
  const sameRows = rows.filter((r) => r.legal === 'same');
  const indepRows = rows.filter((r) => r.legal === 'independent');
  if (sameRows.length) groups.push({ key: 'same', title: '同一法人单位（品牌本体/分校区 · 计入口碑）', rows: sameRows });
  if (indepRows.length) groups.push({ key: 'independent', title: '独立法人单位（品牌合作 · 口碑/挂牌按成绩判定）', rows: indepRows });
  return { brand: g.brand, note: g.brand_note, groups };
});
/** 品牌关联有兄弟校区才展示（只剩自己则不显示该模块） */
const brandCardUseful = computed(() =>
  !!brandCard.value && brandCard.value.groups.some((g) => g.rows.some((r) => !r.isCurrent)),
);
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

    <!-- 学部切换 tab（完中/多学部学校才显示） -->
    <nav v-if="availableStages.length > 1" class="stage-tabs">
      <button
        v-for="s in availableStages"
        :key="s"
        class="stage-tab"
        :class="{ on: stage === s }"
        @click="switchStage(s)"
      >{{ STAGE_LABEL[s] }}</button>
    </nav>

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
      <div class="card-title">口碑信号</div>
      <div class="title-note-row">
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

    <!-- 小学 tab：招生计划 + 所在区小升初机制 -->
    <div v-if="stage === 'primary'" class="card">
      <div class="card-title">招生计划（2026）</div>
      <div v-if="enrollment" class="kv">
        <div class="kv-row"><span>计划班数</span><b>{{ enrollment.plan_classes ?? '—' }} 个班</b></div>
        <div class="kv-row" v-if="enrollment.nature"><span>办学性质</span><b>{{ enrollment.nature }}</b></div>
        <div class="kv-row" v-if="enrollment.source"><span>数据来源</span><b>{{ enrollment.source }}</b></div>
        <div v-if="enrollment.zone" class="zone-block">
          <div class="zone-label">招生地段（对口）</div>
          <p>{{ enrollment.zone }}</p>
        </div>
      </div>
      <p v-else class="empty">未在 2026 招生计划中匹配到招生地段（数据覆盖七区；分校区、新建校暂缺，后续补录）。</p>
      <div v-if="primaryMechanism" class="kv" style="margin-top:10px;">
        <div class="kv-row"><span>所在区小升初机制</span><b style="font-weight:400;">{{ primaryMechanism }}</b></div>
      </div>
    </div>

    <!-- 小学 tab：升学路线（对口初中 · 派位/直升） -->
    <div v-if="stage === 'primary' && (feedRows.length || feedGap || feedJuniors?.direct_feed)" class="card">
      <div class="card-title">升学路线（2026）</div>
      <p v-if="feedJuniors?.group" class="sub-note">分组：{{ feedJuniors.group }}</p>
      <p v-if="feedJuniors?.direct_feed" class="sub-note">直升：{{ feedJuniors.direct_feed }}</p>
      <div v-if="feedRows.length" class="feed-list">
        <div v-for="r in feedRows" :key="r.name" class="feed-item">
          <RouterLink :to="`/school/${encodeURIComponent(r.name)}?stage=middle`" class="feed-name">{{ r.name }}</RouterLink>
          <span v-if="r.summary" class="tag">{{ r.summary }}</span>
          <span v-else class="tag tag-dim">区属初中</span>
        </div>
      </div>
      <p v-if="feedGap" class="empty" :style="feedRows.length ? 'margin-top:8px;text-align:left;' : ''">{{ feedGap }}</p>
      <p v-if="feedJuniors?.source_note" class="sub-note" style="margin-top:8px;">{{ feedJuniors.source_note }}</p>
      <p v-if="feedRows.length" class="sub-note" style="margin-top:4px;">点击初中可查看该校升学通道详情。</p>
    </div>

    <!-- 初中 tab：招生 · 生源小学 -->
    <div v-if="stage === 'middle'" class="card">
      <div class="card-title">招生计划（2026）</div>
      <template v-if="feedPrimarys.length">
        <p class="sub-note">以下小学的 2026 对口/派位名单包含本校（由七区全量小学升学路线反查，校名全等匹配）。</p>
        <div class="feed-list">
          <div v-for="r in feedPrimarys" :key="r.primary" class="feed-item">
            <RouterLink :to="`/school/${encodeURIComponent(r.primary)}?stage=primary`" class="feed-name">{{ r.primary }}</RouterLink>
            <span class="tag tag-dim">{{ r.direct_feed ? '对口直升' : (r.group || '对口') }}</span>
          </div>
        </div>
      </template>
      <p v-else class="empty">本校未进入 2026 公办小学对口/派位名单。民办校无公办对口名单，以官方摇号 / 直升政策为准；公办新建校或未收录点位以最新官方公告为准。</p>
    </div>

    <!-- 初中 tab：升学通道（名额分配/自招，LinkagePanel） -->
    <template v-if="stage === 'middle'">
      <LinkagePanel :stage="'middle'" :school="schoolName" />
    </template>

    <!-- 高中 tab：高考信息在上，招生计划（中考线+名额覆盖）在下 -->
    <template v-if="stage === 'high'">
      <div class="card" v-if="gaokaoRows.length">
        <div class="card-title">高考信息</div>
        <div class="kv">
          <div class="kv-row" v-for="r in gaokaoRows" :key="r.label">
            <span>{{ r.label }}</span><b>{{ r.value }}</b>
          </div>
        </div>
        <p class="sub-note">高分段/特控率为各校喜报或网传，非官方统一发布，仅供参考。</p>
      </div>
      <div class="card" v-if="admissionRows.length">
        <div class="card-title">招生计划</div>
        <div class="kv">
          <div class="kv-row" v-for="r in admissionRows" :key="r.label">
            <span>{{ r.label }}</span><b :class="{ strong: r.strong }">{{ r.value }}</b>
          </div>
        </div>
        <p class="sub-note">录取线为官方发布：公办为户籍生最低分，民办为最低分（含公费班），外语艺术类为末位考生分数；2025/2026 两年同屏展示。</p>
      </div>
      <LinkagePanel :stage="'high'" :school="schoolName" />
    </template>

    <!-- 品牌关联 + 校区（合并） -->
    <div v-if="brandCardUseful" class="card">
      <div class="card-title">品牌关联</div>
      <template v-if="brandCard">
        <p class="sub-note">同一品牌下的校区与学校，按法人关系分组。</p>
        <div class="brand-head">品牌 · {{ brandCard.brand }}</div>
        <p v-if="brandCard.note" class="brand-note">{{ brandCard.note }}</p>
        <div v-for="g in brandCard.groups" :key="g.key" class="brand-group">
          <div class="brand-group-title" :class="g.key">{{ g.title }}</div>
          <div v-for="r in g.rows" :key="r.name" class="brand-row" :class="{ current: r.isCurrent }">
            <div class="brand-row-main">
              <RouterLink v-if="r.link" :to="r.link" class="brand-name-link">{{ r.name }}</RouterLink>
              <span v-else class="brand-name-plain">{{ r.name }}</span>
              <span v-if="r.isCurrent" class="tag tag-now">当前查看</span>
              <span class="tag">{{ r.role }}</span>
            </div>
            <div class="brand-row-badges">
              <span v-if="r.district" class="badge b-district">{{ r.district }}</span>
              <span v-for="s in r.stages" :key="s" class="badge b-stage">{{ s }}</span>
              <span v-if="r.badge" class="badge" :class="r.badge.cls">{{ r.badge.text }}</span>
            </div>
            <p v-if="r.reason" class="brand-reason">{{ r.reason }}</p>
          </div>
        </div>
      </template>
      <!-- 无品牌集团卡片时，校区列表用 brand-row 风格（可点击 + 学部 badge） -->
      <div v-if="!brandCardUseful && rec?.campuses && rec.campuses.length > 1" class="brand-group">
        <div v-for="c in rec.campuses" :key="c" class="brand-row">
          <div class="brand-row-main">
            <RouterLink :to="`/school/${encodeURIComponent(c)}?stage=high`" class="brand-name-link">{{ c }}</RouterLink>
            <span class="tag">校区</span>
          </div>
        </div>
      </div>
    </div>

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
.stage-tabs { display: flex; gap: 8px; margin: 0 0 14px; }
.stage-tab { padding: 6px 16px; border: 1px solid #d9d9d9; border-radius: 999px; background: #fff; cursor: pointer; font-size: 14px; }
.stage-tab.on { background: #1a73e8; color: #fff; border-color: #1a73e8; }
.d-head h1 { font-size: 20px; font-weight: 700; margin: 0 0 8px; line-height: 1.4; }
.badges { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.badge { font-size: 12px; font-weight: 700; color: #fff; border-radius: 6px; padding: 2px 9px; }
.stage { font-size: 12px; color: #6b7280; }

.badge.sm { font-size: 10.5px; padding: 1px 7px; vertical-align: middle; margin-left: 6px; }
.title-note-row { margin: -4px 0 10px; display: flex; align-items: center; gap: 6px; }
.title-note { font-size: 11px; color: #9aa0a6; font-weight: 400; }

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

/* 品牌关联板块 */
.brand-head { font-size: 12.5px; font-weight: 700; color: #1a1b1c; margin-bottom: 4px; }
.brand-note { font-size: 12px; color: #444; line-height: 1.7; margin: 0 0 10px; background: #f7f6f2; border-radius: 8px; padding: 8px 10px; }
.brand-group { margin-bottom: 10px; }
.brand-group:last-child { margin-bottom: 0; }
.brand-group-title { font-size: 11.5px; font-weight: 700; color: #6b7280; margin-bottom: 6px; }
.brand-group-title.same { color: #1e40af; }
.brand-group-title.independent { color: #b45309; }
.brand-row { border: 1px solid #eee; border-radius: 10px; padding: 8px 10px; margin-bottom: 6px; }
.brand-row:last-child { margin-bottom: 0; }
.brand-row.current { border-color: #9bbbf4; background: rgba(155, 187, 244, 0.08); }
.brand-row-main { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 12.5px; }
.brand-name-link { color: #1a6bd6; text-decoration: none; font-weight: 600; }
.brand-name-link:hover { text-decoration: underline; }
.brand-name-plain { font-weight: 600; }
.tag-now { background: #9bbbf4; color: #fff; }
.brand-row-badges { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 6px; }
.brand-reason { font-size: 11px; color: #6b7280; line-height: 1.6; margin: 6px 0 0; }

@media (max-width: 600px) {
  .kv-row > span { width: 84px; }
  .bar-name { width: 64px; }
}
</style>
