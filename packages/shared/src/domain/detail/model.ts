/**
 * 详情域：学校详情模型（三学段统一）。
 * 从 Web SchoolDetailView.vue 平移的纯业务逻辑（字段行/徽章/出口/品牌关联），
 * Web 详情页与小程序详情页共用；本模块零平台依赖。
 * 注：tier1（口碑/学校信号）已于 2026-09-30 废弃归档，本模型不再输出口碑信号。
 */
import { normName } from '../../support.js';
import { highScoreRows } from '../../format.js';
import { ADCODE_TO_DISTRICT } from '../../const.js';
import type { HighLevelSchool, SchoolStage, SchoolPoi, SchoolsSnapshot } from '../../types.js';
import type { Repository } from '../../data/repository.js';
import type { BrandUnit } from '../../data/types.js';

const GAP_MARKERS = ['待查', '未在', '缺口', '暂缺'];
const STAGE_LABEL: Record<SchoolStage, string> = { primary: '小学部', middle: '初中部', high: '高中部' };
const STAGE_SHORT: Record<SchoolStage, string> = { primary: '小学', middle: '初中', high: '高中' };

/** 小学升学机制徽章 label（与初中招生机制 DEFAULT_DEFS label 完全一致；枚举 key 即配色类名）。
 * 机制枚举在数据层固化（parsed 转录解析 + from_middle 初中直写；dist 五区以初中反推为准），
 * 运行时只读数据字段、零文本匹配。 */
export const XS_MECH_LABELS: Record<string, string> = {
  zhi_sheng: '对口直升',
  single_zone: '单校划片',
  group_paidui: '多校电脑派位',
  single_paidui: '电脑派位',
  min_zi_zhu: '自主招生',
};

export interface DetailRow { label: string; value: string; strong?: boolean }
export interface DetailBadge { text: string; cls: string }
export interface FeedRow { name: string; poiName: string | null }
export interface BrandRow {
  name: string;
  role: string;
  legal: 'same' | 'independent';
  relationType?: 'entrusted' | 'cooperation' | 'brand';
  district: string;
  stages: string[]; // 小学/初中/高中
  badge: DetailBadge | null;
  reason: string | null;
  isCurrent: boolean;
  link: string | null;
}
export interface MultiCampusCard {
  groups: { key: string; title: string; rows: BrandRow[] }[];
}
export interface DetailModel {
  stage: SchoolStage;
  name: string;
  availableStages: SchoolStage[];
  stageLabel: string;
  district: string;
  badges: DetailBadge[];
  /** 办学性质（实体表真源：民办写"民办"，公办默认"公办"） */
  nature: string;
  headText: string;
  legalEntityText: string;
  poi: { lng: number; lat: number } | null;
  /* 小学 */
  enrollment: {
    school_id: string; plan_classes?: number | null; plan_count?: number | null; nature?: string;
    zone?: string; note?: string; district?: string; source?: string; matchedBy: string;
  } | null;
  feedJuniors: { group: string | null; mechanisms: string[]; feed_junior_highs: string[]; direct_feed: string | null; source_note?: string } | null;
  feedGap: string | null;
  feedRows: FeedRow[];
  /* 初中 */
  /** 极少数校区的招生计划特殊备注（如执信水荫路仅初三就读；无备注为 null） */
  enrollNote: string | null;
  /* 高中 */
  admissionRows: DetailRow[];
  gaokaoRows: DetailRow[];
  /* 品牌/校区 */
  brandCard: { brand: string; note?: string; sourceUrls: string[]; groups: { key: string; title: string; rows: BrandRow[] }[] } | null;
  brandCardUseful: boolean;
  multiCampusCard: MultiCampusCard | null;
  multiCampusCardUseful: boolean;
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

  /* ---------- 校名匹配（高中分类；小学/初中无口碑记录） ---------- */
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
    return '—';
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
  const xsRecord = stage === 'primary' ? repo.xiaoshengchuOf(poi?.school_id ?? null) : null;
  const feedJuniors = (() => {
    if (stage !== 'primary' || !xsRecord) return null;
    return {
      group: xsRecord.group,
      mechanisms: xsRecord.mechanisms || [],
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
      .map((n) => ({ name: n, poiName: repo.resolvePoiName(n) }));
  })();

  /* 生源小学反查（middlePrimaryFeed）已停用：2026-09-23 新数据（官方直建派位组对口小学）
     替代七区全量小升初反查口径，详情页不再展示反查生源小学段。 */

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
  const badges = repo.schoolBadges(stage, { district: districtOf, rec, name: schoolName, schoolId, singleStage: true });
  const headText = (() => {
    if (stage === 'high') {
      const r = rec;
      // 隶属展示：区属统一为「区属」（不带区名，如「天河区属」→「区属」，与区域徽章不重复）；
      // 省市属保留细粒度「省属/市属」（官方：省市属名额面向全市、区属面向本区）
      const affText = (a: string) => (a.endsWith('区属') ? '区属' : a);
      return r ? `${r.demo || ''}${r.demo && r.affiliation ? ' · ' : ''}${affText(r.affiliation || '')}${r.campuses?.length ? ` · ${r.campuses.length} 校区` : ''}`.trim() : '';
    }
    return '';
  })();
  /** 法人实体信息原来自 tier1 口碑数据（已废弃归档），无官方替代，固定为「—」。 */
  const legalEntityText = '—';

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
          // 该成员行的全部外键：merge_groups 对品牌组保留了完整 school_ids
          // （如「黄埔铁英」= 中学+小学两个实体），普通成员用单 school_id
          const idList: string[] = m.school_ids && m.school_ids.length
            ? m.school_ids
            : (c.school_id ? [c.school_id] : []);
          // 学段兜底：POI 名未命中（poi_name 缺失/为成员通名）但外键实体存在时，
          // 按实体学段补 Badge（与 brand 分支同款；防「黄埔铁英」等品牌成员 Badge 消失）
          const stages: string[] = [...campusStages];
          for (const s of ['primary', 'middle', 'high'] as SchoolStage[]) {
            if (!stages.includes(STAGE_SHORT[s]) && idList.some((id) => repo.entities.some((e) => e.school_id === id && e.stage === s))) {
              stages.push(STAGE_SHORT[s]);
            }
          }
          const stageKey = [stage, ...(['primary', 'middle', 'high'] as SchoolStage[]).filter((s) => s !== stage)]
            .find((k: SchoolStage) => stages.includes(STAGE_SHORT[k])) || null;
          // 跳转必须可解析：外键实体命中，或成员名/POI 名能解析到在册实体。
          // 7 区外远郊成员（南沙铁英/增城/英德等，无实体无 POI）只作信息行，不生成可点击跳转
          const linkedEntity = stageKey
            ? idList.map((id) => repo.entities.find((e) => e.school_id === id && e.stage === stageKey)).find(Boolean)
            : null;
          const resolvable = !!linkedEntity || idList.length > 0 || !!repo.resolvePoiName(cn);
          const link = cn && resolvable
            ? `/school/${encodeURIComponent(linkedEntity?.name || cn)}?stage=${stageKey || 'primary'}${linkedEntity ? `&id=${linkedEntity.school_id}` : (c.school_id ? `&id=${c.school_id}` : '')}`
            : null;
          return {
            name: m.campuses && m.campuses.length ? cn : m.name,
            role: m.role,
            legal: m.legal === 'same' ? 'same' as const : 'independent' as const,
            relationType: m.relation_type === 'same' ? undefined : m.relation_type,
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
    const rows: BrandRow[] = [];
    for (const u of units) {
      const unitNorm = unitCoreNorm(u.name);
      const fullUnitNorm = normName(u.name);
      const unitSchoolIds = u.school_ids || [];
      const recH = highTable.get(normName(u.name));
      const poiNormExtras = (u.poi_names || []).map(normName).filter(Boolean);
      const hasPoiFor = (list: SchoolPoi[]): boolean =>
        list.some((s) => {
          const pn = normName(s.name);
          return pn === unitNorm || poiNormExtras.includes(pn);
        });
      const stages: string[] = [];
      if (hasPoiFor(primarySchools.schools)) stages.push('小学');
      if (hasPoiFor(middleSchools.schools)) stages.push('初中');
      if (hasPoiFor(highSchools.schools)) stages.push('高中');
      // school_id 外键命中的实体学段也算入（如星悦初中部：POI 名不含单位名，但外键实体存在）
      for (const s of ['primary', 'middle', 'high'] as SchoolStage[]) {
        if (!stages.includes(STAGE_SHORT[s]) && unitSchoolIds.some((id) => repo.entities.some((e) => e.school_id === id && e.stage === s))) {
          stages.push(STAGE_SHORT[s]);
        }
      }
      let district = '';
      const poiHit = [primarySchools, middleSchools, highSchools]
        .map((snap: SchoolsSnapshot) => snap.schools.find((s: SchoolPoi) => normName(s.name) === unitNorm))
        .find(Boolean);
      if (poiHit?.adcode) district = ADCODE_TO_DISTRICT[poiHit.adcode] || '';
      if (!district) district = recH?.district || '';
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
        badge: null, reason: null, isCurrent, link,
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
  /** 无教育集团时，实体注册表派生的同法人多校区；仅按 school_id 外键命中。 */
  const multiCampusCard: MultiCampusCard | null = (() => {
    if (brandCard) return null;
    const family = repo.multiCampusOfSchool(schoolName, schoolId);
    if (!family) return null;
    const rows: BrandRow[] = family.school_ids.map((id) => {
      const entities = repo.entities.filter((entity) => entity.school_id === id);
      const preferred = entities.find((entity) => entity.stage === stage) || entities[0];
      const stages = (['primary', 'middle', 'high'] as SchoolStage[])
        .filter((candidate) => entities.some((entity) => entity.stage === candidate))
        .map((candidate) => STAGE_SHORT[candidate]);
      return {
        name: preferred?.name || id,
        role: '校区',
        legal: 'same',
        district: ADCODE_TO_DISTRICT[id.slice(3, 9)] || '',
        stages,
        badge: null,
        reason: null,
        isCurrent: id === schoolId,
        link: preferred ? `/school/${encodeURIComponent(preferred.name)}?stage=${preferred.stage}&id=${id}` : null,
      };
    });
    return { groups: [{ key: 'campuses', title: '多校区', rows }] };
  })();
  const multiCampusCardUseful = !!multiCampusCard && multiCampusCard.groups.some((g) => g.rows.some((r) => !r.isCurrent));

  return {
    stage,
    name: schoolName,
    availableStages,
    stageLabel: STAGE_SHORT[stage],
    district: districtOf,
    badges,
    nature: entityNature ?? '公办',
    headText,
    legalEntityText,
    poi: poi ? { lng: poi.lng, lat: poi.lat } : null,
    enrollment: enrollment ? { ...enrollment, nature: entityNature || '公办' } : null,
    feedJuniors,
    feedGap,
    feedRows,
    enrollNote: stage === 'middle' && poi?.school_id
      ? (repo.middleEnrollNotes?.[poi.school_id] ?? null)
      : null,
    admissionRows,
    gaokaoRows,
    brandCard,
    brandCardUseful,
    multiCampusCard,
    multiCampusCardUseful,
    campuses: rec?.campuses || null,
  };
}
