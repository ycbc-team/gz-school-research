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
export interface FeedRow { name: string; poiName: string | null; summary: string | null; hasQuota: boolean }
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
  /** 极少数校区的招生计划特殊备注（如执信水荫路仅初三就读；无备注为 null） */
  enrollNote: string | null;
  /* 学校信号（历史称号/集团/喜报/录取线等源数据） */
  signalRows: DetailRow[];
  /* 高中 */
  admissionRows: DetailRow[];
  gaokaoRows: DetailRow[];
  /* 品牌/校区 */
  brandCard: { brand: string; note?: string; sourceUrls: string[]; groups: { key: string; title: string; rows: BrandRow[] }[] } | null;
  brandCardUseful: boolean;
  campuses: string[] | null;
}

export function buildDetailModel(stage: SchoolStage, name: string, repo: Repository, schoolId?: string): DetailModel {
  const schoolName = name;
  const { primary: primarySchools, middle: middleSchools, high: highSchools } = repo.schools;

  /* ---------- 学部 tab ---------- */
  const POI_LISTS: Record<SchoolStage, SchoolPoi[]> = {
    primary: primarySchools.schools, middle: middleSchools.schools, high: highSchools.schools,
  };
  // 精确匹配：URL 带 id 按实体 id，否则按校名全等
  const findExact = (s: SchoolStage): SchoolPoi | undefined => schoolId
    ? POI_LISTS[s].find((p) => p.school_id === schoolId)
    : POI_LISTS[s].find((p) => normName(p.name) === normName(schoolName));
  // 同址集合：先取任一部命中 POI，再按同区同坐标把其它学部 POI 一并纳入（九年制小学部/初中部两个 POI，
  // 保证详情页学部 tab 完整；切 tab 时用对应学部 POI 的信息渲染）
  const hitPoi = (['primary', 'middle', 'high'] as SchoolStage[]).map(findExact).find((p) => !!p) ?? null;
  const sameSiteOf = (s: SchoolStage): SchoolPoi | undefined => {
    if (!hitPoi) return findExact(s);
    return (
      POI_LISTS[s].find((p) => p.adcode === hitPoi.adcode && p.lat === hitPoi.lat && p.lng === hitPoi.lng) ??
      findExact(s)
    );
  };
  const availableStages = (['primary', 'middle', 'high'] as SchoolStage[]).filter((s: SchoolStage) => !!sameSiteOf(s));
  const poi = sameSiteOf(stage) || null;

  /* ---------- 校名匹配（与地图同套逻辑） ---------- */
  const tierTables = {
    primary: buildAliasTable(repo.tier1Schools, repo.entities),
    middle: buildAliasTable(repo.middleTier1Schools, repo.entities),
  };
  const tier: Tier1School | undefined = (() => {
    if (stage === 'high') return undefined;
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
  const districtOf = (() => {
    if (poi?.adcode) {
      const d = ADCODE_TO_DISTRICT[poi.adcode];
      if (d) return d;
    }
    if (stage === 'high' && rec?.district) return rec.district;
    // 孤儿 tier1 记录保留 district；匹配上的从 school_id 前缀 adcode 兜底（gz-440104-xxx）
    return (
      tier?.district ||
      (tier?.school_ids?.[0] ? ADCODE_TO_DISTRICT[tier.school_ids[0].slice(3, 9)] : null) ||
      '—'
    );
  })();

  /* ---------- 小学 ---------- */
  const enrollment = stage === 'primary' ? repo.matchEnrollment(poi?.school_id || schoolName) : null;
  // 办学性质唯一真源：实体表 nature（公办不写字段）；招生记录不再携带 nature，公办为默认
  const entityNature = (() => {
    if (schoolId) {
      const e = repo.entities.find((x) => x.school_id === schoolId);
      if (e?.nature) return e.nature;
    }
    const byName = repo.entities.find((x) => normName(x.name) === normName(schoolName) && x.nature === '民办');
    if (byName?.nature) return byName.nature;
    return undefined;
  })();
  const primaryMechanism = (() => {
    if (stage !== 'primary' || !poi) return null;
    const d = repo.primaryTier1.districts;
    for (const k of Object.keys(d)) {
      if (schoolName.includes(k) && d[k]) return (d[k] as { xiaoshengchu_mechanism?: string | null }).xiaoshengchu_mechanism || null;
    }
    return null;
  })();
  const xsRecord = stage === 'primary' ? repo.xiaoshengchuOf(poi?.school_id ?? null) : null;
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
        return { name: n, poiName: repo.resolvePoiName(n), summary: q ? `省市属 ${q.sheng_quota ?? 0} · 名额考生 ${q.kaosheng ?? '—'}` : null, hasQuota: !!q };
      });
  })();

  /* ---------- 初中：生源小学反查 ---------- */
  const feedPrimarys = stage === 'middle' ? repo.middlePrimaryFeed(poi?.school_id ?? null) : [];

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
  /** URL 带校区实体时只展示该实体的录取线；学校聚合入口才展示各校区。 */
  const admissionScores = (() => {
    if (stage !== 'high' || !schoolId) return repo.scoresOfSchool(schoolName, rec?.campuses || []);
    const years = repo.scoresBySchoolId(schoolId);
    const first = years[0]?.records[0];
    return first ? [{ officialName: first.official_name, schoolId, years }] : [];
  })();
  const admissionRows: DetailRow[] = highScoreRows(admissionScores);
  const gaokaoRows = pickRows([
    ['gaofen_2026', '高分段 2026'], ['gaofen_2025', '高分段 2025'],
    ['tekong_2026', '特控线上线率 2026'], ['tekong_2025', '特控线上线率 2025'], ['note', '备注'],
  ]);

  /* ---------- 其他 ---------- */
  const badges = repo.schoolBadges(stage, { district: districtOf, tier, rec, name: schoolName, schoolId, singleStage: true });
  const headText = (() => {
    if (stage === 'high') {
      const r = rec;
      // 隶属展示：区属统一为「区属」（不带区名，如「天河区属」→「区属」，与区域徽章不重复）；
      // 省市属保留细粒度「省属/市属」（官方：省市属名额面向全市、区属面向本区）
      const affText = (a: string) => (a.endsWith('区属') ? '区属' : a);
      return r ? `${r.demo || ''}${r.demo && r.affiliation ? ' · ' : ''}${affText(r.affiliation || '')}${r.campuses?.length ? ` · ${r.campuses.length} 校区` : ''}`.trim() : '';
    }
    const t = tier;
    if (!t) return '';
    const parts: string[] = [];
    if (t.education_group) parts.push(`${t.education_group.name}（${t.education_group.role}）`);
    if (t.entity_relation) parts.push(t.entity_relation);
    return parts.join(' · ');
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
    // 统一入口：优先 school_id 查离线索引，再查 brandGroups，最后校名匹配
    const grp = repo.groupOfSchool(schoolName, schoolId);
    if (!grp) return null;

    // education 来源：区属官方集团（核心校多校区展开 + 成员校，简化渲染）
    if (grp.source === 'education') {
      /** 校区学段按实体 POI 表判定，不依赖成员静态 stage/当前查看 stage（十六中水荫=高中、本部=初中+高中） */
      const campusStageOf = (cn: string): string[] => {
        const n = normName(cn);
        const st: string[] = [];
        if (primarySchools.schools.some((s: SchoolPoi) => normName(s.name) === n)) st.push('小学');
        if (middleSchools.schools.some((s: SchoolPoi) => normName(s.name) === n)) st.push('初中');
        if (highSchools.schools.some((s: SchoolPoi) => normName(s.name) === n)) st.push('高中');
        return st;
      };
      const rows: BrandRow[] = grp.members.flatMap((m) => {
        // education 源无静态 stage，学段一律按校区/学部实体联查；查不到（远郊/未收录）不显示
        // 多校区成员（campuses 非空、poi_name/school_id 为空，如侨乐小学南北校区）平铺为每校区一行：
        // 各自按校区 POI 联查学段、携带各自 school_id 跳转，保证每校区详情页可独立命中
        const campusList: Array<{ poi_name: string; school_id?: string }> =
          m.campuses && m.campuses.length
            ? m.campuses
            : [{ poi_name: m.poi_name || m.name, school_id: m.school_id || '' }];
        return campusList.map((c) => {
          const cn = c.poi_name || m.name;
          const campusStages = campusStageOf(cn);
          const stages: string[] = campusStages;
          const finalStage = campusStages.includes('初中') ? 'middle'
            : campusStages.includes('高中') ? 'high'
            : campusStages.includes('小学') ? 'primary'
            : stage;
          const link = cn
            ? `/school/${encodeURIComponent(cn)}?stage=${finalStage || 'primary'}${c.school_id ? `&id=${c.school_id}` : ''}`
            : null;
          return {
            name: m.campuses && m.campuses.length ? cn : m.name,
            role: m.role,
            legal: 'same' as const,
            district: '',
            stages,
            badge: null,
            reason: null,
            isCurrent:
              // school_id 是精确主键：带 id 打开时只信 id（URL 带 id 的详情页）；
              // 不带 id（按名打开）时才用校区 poi_name / 成员通名兜底匹配
              (!!schoolId && !!c.school_id && c.school_id === schoolId) ||
              (!schoolId && normName(cn) === normName(schoolName)) ||
              // 多校区成员（campuses 非空）共享成员通名 m.name，通名不代表任何具体校区：
              // 仅单校区成员允许用通名兜底选中（否则通名打开详情页时所有校区行都命中）
              (!schoolId && !m.campuses?.length && normName(m.name) === normName(schoolName)),
            link,
          };
        });
      });
      const groups: { key: string; title: string; rows: BrandRow[] }[] = [];
      const coreRows = rows.filter((r) => r.role === '核心校');
      const memberRows = rows.filter((r) => r.role !== '核心校');
      if (coreRows.length) groups.push({ key: 'core', title: '集团核心校', rows: coreRows });
      if (memberRows.length) groups.push({ key: 'members', title: '集团成员校（区教育局官方口径）', rows: memberRows });
      return { brand: grp.brand, note: grp.note, sourceUrls: grp.source_urls || [], groups };
    }

    // brand 来源：8 个重点品牌（法人关系标注）。
    // groupOfSchool 已按 school_id 外键（优先）或按名解析到品牌组；此处直接用其结果，
    // 不再二次按名匹配（否则带外键但名字不含单位名的实体（如星悦初中部）会丢品牌卡片）。
    const units = grp.members as BrandUnit[];
    const unitCoreNorm = (n: string): string => normName(n.replace(/[（(][^）)]*[）)]/g, ''));
    const newOpeningOf = (s: 'primary' | 'middle', un: string): boolean => {
      const list = s === 'primary' ? primarySchools.schools : middleSchools.schools;
      return list.some((po: SchoolPoi) => normName(po.name) === un && !!po.note && po.note.includes('新开办'));
    };
    const rows: BrandRow[] = [];
    for (const u of units) {
      const unitNorm = unitCoreNorm(u.name);
      const fullUnitNorm = normName(u.name);
      const unitSchoolIds = u.school_ids || [];
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
      // school_id 外键命中的实体学段也算入（如星悦初中部：POI 名不含单位名，但外键实体存在）
      for (const s of ['primary', 'middle', 'high'] as SchoolStage[]) {
        if (!stages.includes(STAGE_SHORT[s]) && unitSchoolIds.some((id) => repo.entities.some((e) => e.school_id === id && e.stage === s))) {
          stages.push(STAGE_SHORT[s]);
        }
      }
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
      const reason = (() => {
        const gx = tierM || tierP;
        if (!gx) return null;
        const gaps = (gx.data_gaps || []).filter(Boolean);
        return gaps.length ? gaps.join('；') : null;
      })();
      const stageToKey: Record<string, SchoolStage> = { 小学: 'primary', 初中: 'middle', 高中: 'high' };
      const order = [stage, ...(['primary', 'middle', 'high'] as SchoolStage[]).filter((s) => s !== stage)];
      const stageKey = order.find((k: SchoolStage) => stages.includes(STAGE_SHORT[k])) || null;
      const linkedEntity = stageKey
        ? unitSchoolIds.map((id) => repo.entities.find((e) => e.school_id === id && e.stage === stageKey)).find(Boolean)
        : null;
      const link = stageKey
        ? `/school/${encodeURIComponent(linkedEntity?.name || u.name)}?stage=${stageKey}${linkedEntity ? `&id=${linkedEntity.school_id}` : ''}`
        : null;
      // 校区名称中的括号是身份的一部分，不能为“去别名”而被抹掉。
      // 无显式实体映射的历史单位才保留非校区别名的名称兼容。
      const hasCampusQualifier = /[（(][^）)]*校区[^）)]*[）)]/.test(u.name);
      const isCurrent =
        (!!schoolId && unitSchoolIds.includes(schoolId)) ||
        fullUnitNorm === normName(schoolName) ||
        poiNormExtras.includes(normName(schoolName)) ||
        (!hasCampusQualifier && unitNorm === normName(schoolName));
      rows.push({
        name: u.name, role: u.role, legal: u.legal, district, stages,
        badge: null, reason, isCurrent, link,
      });
    }
    const groups: { key: string; title: string; rows: BrandRow[] }[] = [];
    const sameRows = rows.filter((r) => r.legal === 'same');
    const indepRows = rows.filter((r) => r.legal === 'independent');
    if (sameRows.length) groups.push({ key: 'same', title: '同一法人单位（品牌本体/分校区）', rows: sameRows });
    if (indepRows.length) groups.push({ key: 'independent', title: '独立法人单位（品牌合作）', rows: indepRows });
    return { brand: grp.brand, note: grp.note, sourceUrls: [], groups };
  })();
  const brandCardUseful = !!brandCard && brandCard.groups.some((g) => g.rows.some((r) => !r.isCurrent));

  /* ---------- 客观信号（历史称号/集团/喜报/录取线等源数据） ---------- */
  const signalRows: DetailRow[] = (() => {
    if (stage === 'primary') return tier ? formatPrimarySignals(tier) : [];
    if (stage !== 'middle') return [];
    const rows = tier ? formatMiddleSignals(tier) : [];
    // 自主招生为升学数字：统一从 linkage/rankingMiddle（官方自招资格名单）取，tier1 只做学校信号
    if (repo.rankingMiddle) {
      const list = repo.rankingMiddle.schools;
      const byId = schoolId ? list.find((x) => x.school_id === schoolId) : undefined;
      const recAut = byId ?? list.find((x) => normName(x.name) === normName(schoolName));
      if (recAut && (recAut.autonomy_count ?? 0) > 0) {
        rows.push({ label: '自主招生', value: `2026 年 ${recAut.autonomy_count} 人（官方资格名单）` });
      }
    }
    return rows;
  })();

  return {
    stage,
    name: schoolName,
    availableStages,
    stageLabel: STAGE_SHORT[stage],
    district: districtOf,
    badges,
    headText,
    legalEntityText,
    poi: poi ? { lng: poi.lng, lat: poi.lat } : null,
    enrollment: enrollment ? { ...enrollment, nature: entityNature || '公办' } : null,
    primaryMechanism,
    feedJuniors,
    feedGap,
    feedRows,
    feedPrimarys,
    enrollNote: stage === 'middle' && poi?.school_id
      ? (repo.middleEnrollNotes?.[poi.school_id] ?? null)
      : null,
    signalRows,
    admissionRows,
    gaokaoRows,
    brandCard,
    brandCardUseful,
    campuses: rec?.campuses || null,
  };
}
