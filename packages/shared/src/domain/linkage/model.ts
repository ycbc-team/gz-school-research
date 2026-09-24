/**
 * 升学通道域：详情页/通道页共用的升学数据模型。
 * - middle：指定初中的四通道（第一批特殊通道 / 第二批次额分配·省市属+区属）
 * - high：指定高中的覆盖反查（第一批特殊通道 / 第二批省市属+区属覆盖初中）
 * 从 Web LinkagePanel.vue 平移，纯逻辑零平台依赖。
 */
import type { Repository } from '../../data/repository.js';
import type { QuotaSchool } from '../../data/types.js';
import { normName } from '../../support.js';

export interface BatchMergedRow {
  /** 简称（内部 key，如「侨中」） */
  campus: string;
  /** 官方全称（第二批次名单原文，如「华南师范大学附属中学（石牌校区）」） */
  campusFull: string;
  /** 归属高中全名（跳转用） */
  school: string;
  /** 实体 POI 名（无实体为 null = 不可跳转） */
  poiName: string | null;
  n: number | null; min: number | null;
}
export interface DistrictRow { name: string; poiName: string | null; n: number }
export interface HighCoverRow { school: string; poiName: string | null; n: number; districts: string[]; campuses: CampusLink[] }

/** 法人多校区跳转链接：官方升学文件按法人单位公布，一个法人名对应同 stage 全部校区实体；
 *  升学信息按法人聚合展示，各校区分别点击跳转各自详情页（1 id ↔ 1 详情页 ↔ 1 POI 不变）。 */
export interface CampusLink { schoolId: string; poiName: string | null; campus: string }

export interface LinkageModel {
  /** 初中：名额分配汇总 */
  quota: { kaosheng: number | null; sheng_quota: number | null; qu_quota: number | null } | null;
  /** 初中：省市属（名额+录取最低分合并） */
  batchMerged: BatchMergedRow[];
  /** 初中：区属高中逐校名额 */
  districtRows: DistrictRow[];
  /** 初中：当前法人学校的全部校区（school_ids → 各校区详情跳转） */
  campuses: CampusLink[];
  hasMiddleData: boolean;
  /** 高中：第二批省市属覆盖初中 */
  highCoverage: HighCoverRow[];
  /** 高中：区属覆盖初中（poiName 无实体为 null = 不可跳转；campuses 法人多校区分别跳转） */
  highDistrictCoverage: { school: string; poiName: string | null; n: number; campuses: CampusLink[] }[];
  /** 高中：本校 2026 自主招生计划数（按校区；null=未收录/非自招校） */
  autonomyPlan: number | null;
  /** 高中：本校 2026 体育/艺术特长生计划数（按校区；null=未收录/无特长生计划） */
  sportsPlan: number | null;
  artsPlan: number | null;
  /** 高中：体育/艺术特长生项目二级细项（官方明细表；空数组=无项目） */
  sportsProjects: { project: string; plan: number; note?: string }[] | null;
  artsProjects: { project: string; plan: number; note?: string }[] | null;
  /** 高中：特长生计划备注类型（'reserve'=含优秀体育后备人才名额 / 'lingjun'=领军龙足球试点单列），前端据此条件显示解释 */
  planNotes: ('reserve' | 'lingjun')[];
  hasHighData: boolean;
}

/** POI 分校区名归一（去括号校区） */
function normCampus(s: string): string {
  return s.replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').trim();
}

/** special 名单原文 → 名额分配原文校名（跨源键对齐） */
export function buildLinkageModel(stage: 'middle' | 'high', schoolName: string, repo: Repository, schoolId?: string | null): LinkageModel {
  const { CAMPUS_NAMES, CAMPUS_INFO } = repo;
  /** school_id → 实体 POI 名（跳转目标归一：有实体才可跳详情页） */
  const poiNameOf = (schoolId: string | null | undefined): string | null => {
    if (!schoolId) return null;
    return repo.entities.find((e) => e.school_id === schoolId)?.name ?? null;
  };
  /** 任意名 → 实体 POI 名（CAMPUS_INFO 学校名等未回填场景，loose 容错） */
  const resolvePoi = (name: string): string | null => repo.resolvePoiName?.(name) ?? null;
  /** 行跳转目标：优先用校区官方原文名（精确到校区实体），学校名兜底（多校区歧义时取第一个实体） */
  const poiOfRow = (campusFull: string, school: string): string | null => resolvePoi(campusFull) ?? resolvePoi(school);
  /** dist 键可能是 school_id（ids 层）或原文名（schools 层）：统一转展示名（实体表 join） */
  const nameOfKey = (k: string): string => {
    const e = repo.entities.find((x) => x.school_id === k);
    return e ? e.name : k;
  };
  /** 键 → POI 跳转名：id 层直接实体名（精确到校区）；原文层 resolvePoi 容错 */
  const poiOfKey = (k: string): string | null => {
    const e = repo.entities.find((x) => x.school_id === k);
    return e ? e.name : resolvePoi(k);
  };

  /** school_id → 校区跳转链接 */
  const linkOf = (sid: string): CampusLink => {
    const pn = poiNameOf(sid);
    return { schoolId: sid, poiName: pn, campus: pn || sid };
  };
  /** 法人行 school_ids → 校区跳转链接（升学信息按法人聚合展示，各校区分别跳转各自详情页）。
   *  exactName 传入行/输入名：带括号（已精确到校区，如「铁一中学(越秀校区)」「西关外国语学校(初中部)」）
   *  时只返回与该名归一全等的校区，避免"已指定校区仍弹多校区聚合面板"；
   *  法人名（无括号，如「广东仲元中学」）才全校区列出供弹窗选择。 */
  const campusesOf = (q: QuotaSchool | undefined, exactName?: string): CampusLink[] => {
    if (!q || !('school_ids' in q)) return [];
    const sids = q.school_ids || [];
    if (exactName && /[（(]/.test(exactName)) {
      const nk = normName(exactName);
      const hit = sids.filter((sid) => {
        const e = repo.entities.find((x) => x.school_id === sid);
        return !!e && normName(e.name) === nk;
      });
      if (hit.length) return hit.map(linkOf);
    }
    return sids.map(linkOf);
  };

  if (stage === 'middle') {
    const quota = repo.linkageOf(schoolName);
    const quotaRows = quota
      ? CAMPUS_NAMES.filter((c) => (quota.sz[c] ?? 0) > 0)
          .map((c) => ({ campus: c, campusFull: c, school: CAMPUS_INFO[c]!.school, poiName: poiOfRow(c, CAMPUS_INFO[c]!.school), n: quota.sz[c] as number }))
          .sort((a, b) => b.n - a.n)
      : [];
    const batchRows = Object.entries(repo.batch2Of(schoolName)).map(([k, v]) => {
      const nm = nameOfKey(k);
      const ci = CAMPUS_INFO[k] ?? CAMPUS_INFO[nm];
      return {
        campus: nm, // 与 quotaRows 的 CAMPUS_NAMES 对齐（实体校区名=官方原文）
        campusFull: nm,
        school: ci?.school ?? nm,
        poiName: ci ? poiOfRow(nm, ci.school) : poiOfKey(k),
        min: v.min_score,
        last: v.last_score,
      };
    });
    const qmap = new Map<string, { campus: string; campusFull: string; school: string; poiName: string | null; n: number }>(quotaRows.map((r) => [r.campus, r]));
    const bmap = new Map<string, { campus: string; campusFull: string; school: string; poiName: string | null; min: number | null }>(
      batchRows.map((r) => [r.campus, { campus: r.campus, campusFull: r.campusFull, school: r.school, poiName: r.poiName, min: r.min ?? null }]),
    );
    const batchMerged: BatchMergedRow[] = [...new Set([...qmap.keys(), ...bmap.keys()])]
      .map((c) => {
        const q = qmap.get(c);
        const b = bmap.get(c);
        return {
          campus: c,
          campusFull: b?.campusFull || q?.campusFull || c,
          school: b?.school || q?.school || normCampus(c),
          poiName: b?.poiName || q?.poiName || null,
          n: q?.n ?? null,
          min: b?.min ?? null,
        };
      })
      .sort((a, b) => (b.n ?? 0) - (a.n ?? 0));
    const districtRows: DistrictRow[] = Object.entries(repo.districtQuotaOf(schoolName))
      .map(([k, n]) => ({ name: nameOfKey(k), poiName: poiOfKey(k), n }))
      .sort((a, b) => b.n - a.n);
    return {
      quota: quota ? { kaosheng: quota.kaosheng, sheng_quota: quota.sheng_quota, qu_quota: quota.qu_quota } : null,
      batchMerged,
      districtRows,
      campuses: campusesOf(quota, schoolName),
      hasMiddleData: !!quota || batchRows.length > 0,
      highCoverage: [],
      highDistrictCoverage: [],
      autonomyPlan: null,
      sportsPlan: null,
      artsPlan: null,
      sportsProjects: null,
      artsProjects: null,
      planNotes: [],
      hasHighData: false,
    };
  }

  // high：第一批按 school_id 精确查询；名称仅用于第二批历史兼容查询。
  // 1) 全半角统一后精确匹配校区键 → 只展示该校区；2) 传入归属学校名（无校区）时兼容聚合全部校区
  const zq = (s: string) => s.replace(/（/g, '(').replace(/）/g, ')');
  const exactCampuses = CAMPUS_NAMES.filter((c) => zq(c) === zq(schoolName));
  const target = normCampus(schoolName);
  const highCampuses =
    exactCampuses.length > 0
      ? exactCampuses
      : CAMPUS_NAMES.filter(
          (c) => normCampus(CAMPUS_INFO[c]!.school) === target || CAMPUS_INFO[c]!.school === schoolName,
        );
  const mergedCover = new Map<string, { n: number; districts: Set<string>; schoolId: string | null }>();
  for (const c of highCampuses) {
    for (const { school, school_id, n, district } of repo.quotaCoverage(c)) {
      const m = mergedCover.get(school) || { n: 0, districts: new Set<string>(), schoolId: null };
      m.n += n;
      if (district) m.districts.add(district);
      if (!m.schoolId && school_id) m.schoolId = school_id;
      mergedCover.set(school, m);
    }
  }
  const highCoverage: HighCoverRow[] = [...mergedCover.entries()]
    .map(([school, v]) => ({ school, poiName: poiNameOf(v.schoolId), n: v.n, districts: [...v.districts], campuses: campusesOf(repo.linkageOf(school), school) }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 30);
  const highDistrictCoverage: { school: string; poiName: string | null; n: number; campuses: CampusLink[] }[] = repo
    .districtCoverage(schoolName)
    .slice(0, 50)
    .map((r) => ({ school: r.school, poiName: poiNameOf(r.school_id), n: r.n, campuses: campusesOf(repo.linkageOf(r.school), r.school) }));

  const autonomyPlan = stage === 'high' ? repo.autonomyPlanOf(schoolName) : null;
  const specialPlan = stage === 'high' && schoolId ? repo.specialPlanOf(schoolId) : null;
  const planNotes: ('reserve' | 'lingjun')[] = [];
  if (specialPlan?.sportsProjects?.some((p) => p.note?.includes('体育后备人才'))) planNotes.push('reserve');
  if (specialPlan?.sportsProjects?.some((p) => p.note?.includes('领军龙'))) planNotes.push('lingjun');

  return {
    quota: null,
    batchMerged: [],
    districtRows: [],
    campuses: [],
    hasMiddleData: false,
    highCoverage,
    highDistrictCoverage,
    autonomyPlan,
    sportsPlan: specialPlan?.sports ?? null,
    artsPlan: specialPlan?.arts ?? null,
    sportsProjects: specialPlan?.sportsProjects ?? null,
    artsProjects: specialPlan?.artsProjects ?? null,
    planNotes,
    hasHighData: highCoverage.length > 0 || highDistrictCoverage.length > 0 || autonomyPlan != null || specialPlan != null,
  };
}
