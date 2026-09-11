/**
 * 详情域：学校详情模型（三学段统一）。
 * 从 Web SchoolDetailView.vue 平移的纯业务逻辑（字段行/徽章/信号/出口/品牌关联），
 * Web 详情页与小程序详情页共用；本模块零平台依赖。
 */
import { buildAliasTable, matchTier1ByPoiName, normName } from '../../support.js';
import { formatPrimarySignals, formatMiddleSignals, highScoreRows } from '../../format.js';
import { ADCODE_TO_DISTRICT } from '../../const.js';
import type { Tier1School, HighLevelSchool, SchoolStage, SchoolPoi, SchoolsSnapshot } from '../../types.js';
import type { Repository } from '../../data/repository.js';
import type { BrandUnit } from '../../data/types.js';

const GAP_MARKERS = ['待查', '未在', '缺口', '暂缺'];
const STAGE_LABEL: Record<SchoolStage, string> = { primary: '小学部', middle: '初中部', high: '高中部' };
const STAGE_SHORT: Record<SchoolStage, string> = { primary: '小学', middle: '初中', high: '高中' };

export interface DetailRow { label: string; value: string; strong?: boolean }
export interface DetailBadge { text: string; cls: string }
export interface FeedRow { name: string; summary: string | null; hasQuota: boolean }
export interface FeedPrimaryRow { primary: string; group: string | null; direct_feed: string | null }
export interface BrandRow {
  name: string;
  role: string;
  legal: 'same' | 'independent';
  district: string;
  stages: string[]; // 小学/初中/高中
  badge: DetailBadge | null;
  reason: string | null;
  isCurrent: boolean;
  link: string | null;
}
export interface DetailModel {
  stage: SchoolStage;
  name: string;
  availableStages: SchoolStage[];
  stageLabel: string;
  district: string;
  badges: DetailBadge[];
  headText: string;
  support: DetailBadge | null;
  tierNote: string | null;
  legalEntityText: string;
  poi: { lng: number; lat: number } | null;
  /* 小学 */
  enrollment: {
    school: string; plan_classes?: number | null; nature?: string; zone?: string; note?: string;
    district?: string; source?: string; matchedBy: string;
  } | null;
  primaryMechanism: string | null;
  feedJuniors: { group: string | null; feed_junior_highs: string[]; direct_feed: string | null; source_note?: string } | null;
  feedGap: string | null;
  feedRows: FeedRow[];
  /* 初中 */
  feedPrimarys: FeedPrimaryRow[];
  /* 口碑信号 */
  signalRows: DetailRow[];
  /* 高中 */
  admissionRows: DetailRow[];
  gaokaoRows: DetailRow[];
  /* 品牌/校区 */
  brandCard: { brand: string; note?: string; groups: { key: string; title: string; rows: BrandRow[] }[] } | null;
  brandCardUseful: boolean;
  campuses: string[] | null;
}

export function buildDetailModel(stage: SchoolStage, name: string, repo: Repository): DetailModel {
  const schoolName = name;
  const { primary: primarySchools, middle: middleSchools, high: highSchools } = repo.schools;

  /* ---------- 学部 tab ---------- */
  const POI_LISTS: Record<SchoolStage, SchoolPoi[]> = {
    primary: primarySchools.schools, middle: middleSchools.schools, high: highSchools.schools,
  };
  const availableStages = (['primary', 'middle', 'high'] as SchoolStage[]).filter((s: SchoolStage) =>
    POI_LISTS[s].some((p: SchoolPoi) => normName(p.name) === normName(schoolName)),
  );

  /* ---------- 校名匹配（与地图同套逻辑） ---------- */
  const tierTables = {
    primary: buildAliasTable(repo.tier1Schools, repo.entities),
    middle: buildAliasTable(repo.middleTier1Schools, repo.entities),
  };
  const tier: Tier1School | undefined = (() => {
    if (stage === 'high') return undefined;
    const poiList = stage === 'primary' ? primarySchools.schools : middleSchools.schools;
    const poi = poiList.find((s: SchoolPoi) => normName(s.name) === normName(schoolName));
    if (poi?.note && poi.note.includes('新开办')) return undefined;
    return matchTier1ByPoiName(
      schoolName,
      stage === 'primary' ? repo.tier1Schools : repo.middleTier1Schools,
      tierTables[stage],
    );
  })();

  const highTable = new Map<string, HighLevelSchool>();
  for (const sc of repo.highLevels.schools) {
    for (const k of [sc.name, ...(sc.aliases || []), ...(sc.campuses || [])]) {
      const nk = normName(k);
      if (nk && !highTable.has(nk)) highTable.set(nk, sc);
    }
  }
  const rec: HighLevelSchool | undefined = (() => {
    if (stage === 'high') return highTable.get(normName(schoolName));
    if (stage === 'middle' && repo.isComprehensive(schoolName)) return highTable.get(normName(schoolName));
    return undefined;
  })();

  /* ---------- 基本信息 ---------- */
  const poi = POI_LISTS[stage].find((s) => s.name === schoolName) || null;
  const districtOf = (() => {
    if (poi?.adcode) {
      const d = ADCODE_TO_DISTRICT[poi.adcode];
      if (d) return d;
    }
    if (stage === 'high' && rec?.district) return rec.district;
    // 孤儿口碑记录保留 district；匹配上的从 school_id 前缀 adcode 兜底（gz-440104-xxx）
    return (
      tier?.district ||
      (tier?.school_ids?.[0] ? ADCODE_TO_DISTRICT[tier.school_ids[0].slice(3, 9)] : null) ||
      '—'
    );
  })();

  /* ---------- 小学 ---------- */
  const enrollment = stage === 'primary' ? repo.matchEnrollment(schoolName) : null;
  const primaryMechanism = (() => {
    if (stage !== 'primary' || !poi) return null;
    const d = repo.primaryTier1.districts;
    for (const k of Object.keys(d)) {
      if (schoolName.includes(k) && d[k]) return (d[k] as { xiaoshengchu_mechanism?: string | null }).xiaoshengchu_mechanism || null;
    }
    return null;
  })();
  const xsRecord = stage === 'primary' ? repo.xiaoshengchuOf(schoolName, poi?.adcode) : null;
  const feedJuniors = (() => {
    if (stage !== 'primary' || !xsRecord) return null;
    return {
      group: xsRecord.group,
      feed_junior_highs: xsRecord.feed_junior_highs || [],
      direct_feed: xsRecord.direct_feed,
      source_note: xsRecord.source_note,
    };
  })();
  const feedGap = (() => {
    if (stage !== 'primary') return null;
    if (!xsRecord) return '本校未进入 2026 公办小学对口/派位名单。民办校无公办对口名单，以官方摇号 / 直升政策为准；公办新建校或未收录点位以最新官方公告为准。';
    if (xsRecord.direct_feed) return null;
    const f = xsRecord.feed_junior_highs || [];
    if (!f.length) return `升学路线数据缺口：${xsRecord.data_gaps || '官方未公布该校对口/派位初中'}。`;
    const placeholder = f.filter((n) => GAP_MARKERS.some((m) => n.includes(m)));
    if (placeholder.length) return `升学路线数据缺口：${placeholder.join('；')}`;
    return null;
  })();
  const feedRows: FeedRow[] = (() => {
    const f = feedJuniors;
    if (!f) return [];
    return f.feed_junior_highs
      .filter((n) => !GAP_MARKERS.some((m) => n.includes(m)))
      .map((n) => {
        const q = repo.middleQuotaSummary(n);
        return { name: n, summary: q ? `省市属 ${q.sheng_quota ?? 0} · 名额考生 ${q.kaosheng ?? '—'}` : null, hasQuota: !!q };
      });
  })();

  /* ---------- 初中：生源小学反查 ---------- */
  const feedPrimarys = stage === 'middle' ? repo.middlePrimaryFeed(schoolName) : [];

  /* ---------- 高中 ---------- */
  const pickRows = (keys: [string, string, boolean?][]): DetailRow[] => {
    const ind = rec?.indicators || {};
    const rows: DetailRow[] = [];
    for (const [k, label, strong] of keys) {
      const v = ind[k];
      if (v !== undefined && v !== null && v !== '') rows.push({ label, value: String(v), strong });
    }
    return rows;
  };
  const admissionRows: DetailRow[] = highScoreRows(
    repo.scoresOfSchool(schoolName, rec?.campuses || []),
  );
  const gaokaoRows = pickRows([
    ['gaofen_2026', '高分段 2026'], ['gaofen_2025', '高分段 2025'],
    ['tekong_2026', '特控线上线率 2026'], ['tekong_2025', '特控线上线率 2025'], ['note', '备注'],
  ]);

  /* ---------- 其他 ---------- */
  const badges = repo.schoolBadges(stage, { district: districtOf, tier, rec, name: schoolName, singleStage: true });
  const support = repo.supportBadge(tier);
  const headText = (() => {
    if (stage === 'high') {
      const r = rec;
      return r ? `${r.demo || ''}${r.demo && r.affiliation ? ' · ' : ''}${r.affiliation || ''}${r.campuses?.length ? ` · ${r.campuses.length} 校区` : ''}`.trim() : '';
    }
    const t = tier;
    if (!t) return '';
    const parts: string[] = [];
    if (t.education_group) parts.push(`${t.education_group.name}（${t.education_group.role}）`);
    if (t.entity_relation) parts.push(t.entity_relation);
    return parts.join(' · ');
  })();
  const tierNote = (() => {
    const t = tier;
    if (!t) return null;
    if (t.tier1_eligible === false) return t.exclude_reason || '网传口碑校，独立法人，未计入口碑学校';
    return t.conclusion_basis || null;
  })();
  const legalEntityText = (() => {
    const le = tier?.legal_entity;
    if (!le || typeof le !== 'object') return '—';
    const leObj = le as { name?: unknown; type?: unknown };
    const nm = leObj.name ? String(leObj.name) : '—';
    const ty = leObj.type ? String(leObj.type) : '';
    return ty ? `${nm}（${ty}）` : nm;
  })();

  /* ---------- 品牌关联 ---------- */
  const brandCard = (() => {
    const g = repo.brandGroupOf(schoolName);
    if (!g) return null;
    const unitCoreNorm = (n: string): string => normName(n.replace(/[（(][^）)]*[）)]/g, ''));
    const newOpeningOf = (s: 'primary' | 'middle', un: string): boolean => {
      const list = s === 'primary' ? primarySchools.schools : middleSchools.schools;
      return list.some((po: SchoolPoi) => normName(po.name) === un && !!po.note && po.note.includes('新开办'));
    };
    const rows: BrandRow[] = [];
    for (const u of g.units as BrandUnit[]) {
      const unitNorm = unitCoreNorm(u.name);
      const newM = newOpeningOf('middle', unitNorm);
      const newP = newOpeningOf('primary', unitNorm);
      const tierM = newM
        ? undefined
        : repo.middleTier1Schools.find((s) => s.name === u.name) ||
          matchTier1ByPoiName(u.name, repo.middleTier1Schools, tierTables.middle);
      const tierP = newP
        ? undefined
        : repo.tier1Schools.find((s) => s.name === u.name) ||
          matchTier1ByPoiName(u.name, repo.tier1Schools, tierTables.primary);
      const recH = highTable.get(normName(u.name));
      const poiNormExtras = (u.poi_names || []).map(normName).filter(Boolean);
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
      let district = '';
      const poiHit = [primarySchools, middleSchools, highSchools]
        .map((snap: SchoolsSnapshot) => snap.schools.find((s: SchoolPoi) => normName(s.name) === unitNorm))
        .find(Boolean);
      if (poiHit?.adcode) district = ADCODE_TO_DISTRICT[poiHit.adcode] || '';
      if (!district) district = tierM?.district || tierP?.district || recH?.district || '';
      const tierX = tierM || tierP;
      const badge = tierX
        ? tierX.tier1_eligible === false
          ? { text: '挂牌', cls: 'b-license' }
          : { text: '口碑', cls: 'b-tier' }
        : null;
      const reason = tierM?.exclude_reason || tierP?.exclude_reason || null;
      const stageToKey: Record<string, SchoolStage> = { 小学: 'primary', 初中: 'middle', 高中: 'high' };
      const order = [stage, ...(['primary', 'middle', 'high'] as SchoolStage[]).filter((s) => s !== stage)];
      const stageKey = order.find((k: SchoolStage) => stages.includes(STAGE_SHORT[k])) || null;
      const link = stageKey ? `/school/${encodeURIComponent(u.name)}?stage=${stageKey}` : null;
      rows.push({
        name: u.name, role: u.role, legal: u.legal, district, stages,
        badge, reason, isCurrent: unitNorm === normName(schoolName), link,
      });
    }
    const groups: { key: string; title: string; rows: BrandRow[] }[] = [];
    const sameRows = rows.filter((r) => r.legal === 'same');
    const indepRows = rows.filter((r) => r.legal === 'independent');
    if (sameRows.length) groups.push({ key: 'same', title: '同一法人单位（品牌本体/分校区 · 计入口碑）', rows: sameRows });
    if (indepRows.length) groups.push({ key: 'independent', title: '独立法人单位（品牌合作 · 口碑/挂牌按成绩判定）', rows: indepRows });
    return { brand: g.brand, note: g.brand_note, groups };
  })();
  const brandCardUseful = !!brandCard && brandCard.groups.some((g) => g.rows.some((r) => !r.isCurrent));

  /* ---------- 口碑信号 ---------- */
  const signalRows: DetailRow[] = stage === 'primary'
    ? (tier ? formatPrimarySignals(tier) : [])
    : stage === 'middle'
      ? (tier ? formatMiddleSignals(tier) : [])
      : [];

  return {
    stage,
    name: schoolName,
    availableStages,
    stageLabel: STAGE_SHORT[stage],
    district: districtOf,
    badges,
    headText,
    support,
    tierNote,
    legalEntityText,
    poi: poi ? { lng: poi.lng, lat: poi.lat } : null,
    enrollment,
    primaryMechanism,
    feedJuniors,
    feedGap,
    feedRows,
    feedPrimarys,
    signalRows,
    admissionRows,
    gaokaoRows,
    brandCard,
    brandCardUseful,
    campuses: rec?.campuses || null,
  };
}
