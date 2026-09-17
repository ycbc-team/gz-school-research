/**
 * 升学通道域：详情页/通道页共用的升学数据模型。
 * - middle：指定初中的四通道（第一批特殊通道 / 第二批次额分配·省市属+区属）
 * - high：指定高中的覆盖反查（第一批特殊通道 / 第二批省市属+区属覆盖初中）
 * 从 Web LinkagePanel.vue 平移，纯逻辑零平台依赖。
 */
import type { Repository } from '../../data/repository.js';
import type { QuotaSchool } from '../../data/types.js';

export interface SpecialRow {
  /** 简称（内部 key，如「侨中」） */
  campus: string;
  /** 官方全称（特殊通道名单原文，如「华南师范大学附属中学（石牌）」） */
  campusFull: string;
  /** 归属高中全名（跳转用） */
  school: string;
  /** 实体 POI 名（school_id → entities.name；无实体为 null = 不可跳转） */
  poiName: string | null;
  /** 高中实体外键；第一批招生跳转必须使用该字段 */
  schoolId: string | null;
  /** 2026 自主招生计划数（官方汇总表，按校区公布）；null=未收录/非自招校 */
  autonomyPlan: number | null;
  autonomy: number; sports: number; arts: number;
}
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
export interface HighSpecialRow { school: string; poiName: string | null; schoolId: string | null; autonomy: number; sports: number; arts: number; campuses: CampusLink[] }

/** 法人多校区跳转链接：官方升学文件按法人单位公布，一个法人名对应同 stage 全部校区实体；
 *  升学信息按法人聚合展示，各校区分别点击跳转各自详情页（1 id ↔ 1 详情页 ↔ 1 POI 不变）。 */
export interface CampusLink { schoolId: string; poiName: string | null; campus: string }

export interface LinkageModel {
  /** 初中：第一批特殊通道（自招/体育/艺术） */
  specialRows: SpecialRow[];
  specialTotal: number;
  /** 初中：名额分配汇总 */
  quota: { kaosheng: number | null; sheng_quota: number | null; qu_quota: number | null } | null;
  /** 初中：省市属（名额+录取最低分合并） */
  batchMerged: BatchMergedRow[];
  /** 初中：区属高中逐校名额 */
  districtRows: DistrictRow[];
  /** 初中：当前法人学校的全部校区（school_ids → 各校区详情跳转） */
  campuses: CampusLink[];
  hasMiddleData: boolean;
  /** 高中：第一批特殊通道覆盖初中 */
  highSpecialCoverage: HighSpecialRow[];
  /** 高中：第二批省市属覆盖初中 */
  highCoverage: HighCoverRow[];
  /** 高中：区属覆盖初中（poiName 无实体为 null = 不可跳转；campuses 法人多校区分别跳转） */
  highDistrictCoverage: { school: string; poiName: string | null; n: number; campuses: CampusLink[] }[];
  /** 高中：本校 2026 自主招生计划数（按校区；null=未收录/非自招校） */
  autonomyPlan: number | null;
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

  /** 法人行 school_ids → 各校区跳转链接（升学信息按法人聚合展示，各校区分别跳转各自详情页） */
  const campusesOf = (q: QuotaSchool | undefined): CampusLink[] =>
    (q?.school_ids || []).map((sid) => {
      const pn = poiNameOf(sid);
      return { schoolId: sid, poiName: pn, campus: pn || sid };
    });

  if (stage === 'middle') {
    const quota = repo.linkageOf(schoolName);
    const quotaRows = quota
      ? CAMPUS_NAMES.filter((c) => (quota.sz[c] ?? 0) > 0)
          .map((c) => ({ campus: c, campusFull: c, school: CAMPUS_INFO[c]!.school, poiName: poiOfRow(c, CAMPUS_INFO[c]!.school), n: quota.sz[c] as number }))
          .sort((a, b) => b.n - a.n)
      : [];
    const specialRows = (() => {
      const m = repo.specialOf(schoolName);
      if (!m) return [];
      return Object.entries(m)
        .map(([k, v]) => {
          const highId = repo.specialHighSchoolId(k);
          const poiName = poiNameOf(highId);
          // k 是官方名单原文，仅作展示；关联和跳转只使用 highId。
          return { campus: k, campusFull: k, school: poiName || normCampus(k), poiName, schoolId: highId, autonomyPlan: repo.autonomyPlanOf(k), autonomy: v.autonomy ?? 0, sports: v.sports ?? 0, arts: v.arts ?? 0 };
        })
        .sort((a, b) => (b.autonomy + b.sports + b.arts) - (a.autonomy + a.sports + a.arts));
    })();
    const specialTotal = specialRows.reduce((s, r) => s + r.autonomy + r.sports + r.arts, 0);
    const batchRows = Object.entries(repo.batch2Of(schoolName)).map(([k, v]) => ({
      campus: k,
      campusFull: k,
      school: CAMPUS_INFO[k]?.school ?? normCampus(k),
      poiName: CAMPUS_INFO[k] ? poiOfRow(k, CAMPUS_INFO[k]!.school) : resolvePoi(k),
      min: v.min_score,
      last: v.last_score,
    }));
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
      .map(([name, n]) => ({ name, poiName: resolvePoi(name), n }))
      .sort((a, b) => b.n - a.n);
    return {
      specialRows,
      specialTotal,
      quota: quota ? { kaosheng: quota.kaosheng, sheng_quota: quota.sheng_quota, qu_quota: quota.qu_quota } : null,
      batchMerged,
      districtRows,
      campuses: campusesOf(quota),
      hasMiddleData: !!quota || specialTotal > 0 || batchRows.length > 0,
      highSpecialCoverage: [],
      highCoverage: [],
      highDistrictCoverage: [],
      autonomyPlan: null,
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
    .map(([school, v]) => ({ school, poiName: poiNameOf(v.schoolId), n: v.n, districts: [...v.districts], campuses: campusesOf(repo.linkageOf(school)) }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 30);
  const mergedSpecial = new Map<string, { autonomy: number; sports: number; arts: number; schoolId: string | null }>();
  for (const s of repo.specialCoverageByHighSchoolId(schoolId)) {
    const m = mergedSpecial.get(s.school) || { autonomy: 0, sports: 0, arts: 0, schoolId: null };
    m.autonomy += s.autonomy;
    m.sports += s.sports;
    m.arts += s.arts;
    if (!m.schoolId && s.school_id) m.schoolId = s.school_id;
    mergedSpecial.set(s.school, m);
  }
  const highSpecialCoverage: HighSpecialRow[] = [...mergedSpecial.entries()]
    .map(([school, v]) => ({ school, poiName: poiNameOf(v.schoolId), schoolId: v.schoolId, autonomy: v.autonomy, sports: v.sports, arts: v.arts, campuses: campusesOf(repo.linkageOf(school)) }))
    .sort((a, b) => b.autonomy + b.sports + b.arts - (a.autonomy + a.sports + a.arts))
    .slice(0, 30);
  const highDistrictCoverage: { school: string; poiName: string | null; n: number; campuses: CampusLink[] }[] = repo
    .districtCoverage(schoolName)
    .slice(0, 50)
    .map((r) => ({ school: r.school, poiName: poiNameOf(r.school_id), n: r.n, campuses: campusesOf(repo.linkageOf(r.school)) }));

  const autonomyPlan = stage === 'high' ? repo.autonomyPlanOf(schoolName) : null;

  return {
    specialRows: [],
    specialTotal: 0,
    quota: null,
    batchMerged: [],
    districtRows: [],
    campuses: [],
    hasMiddleData: false,
    highSpecialCoverage,
    highCoverage,
    highDistrictCoverage,
    autonomyPlan,
    hasHighData: highCoverage.length > 0 || highSpecialCoverage.length > 0 || highDistrictCoverage.length > 0,
  };
}
