/**
 * 升学通道域：详情页/通道页共用的升学数据模型。
 * - middle：指定初中的四通道（第一批特殊通道 / 第二批次额分配·省市属+区属）
 * - high：指定高中的覆盖反查（第一批特殊通道 / 第二批省市属+区属覆盖初中）
 * 从 Web LinkagePanel.vue 平移，纯逻辑零平台依赖。
 */
import type { Repository } from '../../data/repository.js';

export interface SpecialRow {
  /** 简称（内部 key，如「侨中」） */
  campus: string;
  /** 官方全称（特殊通道名单原文，如「华南师范大学附属中学（石牌）」） */
  campusFull: string;
  /** 归属高中全名（跳转用） */
  school: string;
  autonomy: number; sports: number; arts: number;
}
export interface BatchMergedRow {
  /** 简称（内部 key，如「侨中」） */
  campus: string;
  /** 官方全称（第二批次名单原文，如「华南师范大学附属中学（石牌校区）」） */
  campusFull: string;
  /** 归属高中全名（跳转用） */
  school: string;
  n: number | null; min: number | null;
}
export interface DistrictRow { name: string; n: number }
export interface HighCoverRow { school: string; n: number; districts: string[] }
export interface HighSpecialRow { school: string; autonomy: number; sports: number; arts: number }

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
  hasMiddleData: boolean;
  /** 高中：第一批特殊通道覆盖初中 */
  highSpecialCoverage: HighSpecialRow[];
  /** 高中：第二批省市属覆盖初中 */
  highCoverage: HighCoverRow[];
  /** 高中：区属覆盖初中 */
  highDistrictCoverage: { school: string; n: number }[];
  hasHighData: boolean;
}

/** POI 分校区名归一（去括号校区） */
function normCampus(s: string): string {
  return s.replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').trim();
}

/** special 名单原文 → 名额分配原文校名（跨源键对齐） */
function specialToCampus(specialKey: string, repo: Repository): string {
  const { CAMPUS_INFO } = repo;
  for (const [campus, info] of Object.entries(CAMPUS_INFO)) {
    if (info.special === specialKey) return campus;
  }
  return specialKey;
}

export function buildLinkageModel(stage: 'middle' | 'high', schoolName: string, repo: Repository): LinkageModel {
  const { CAMPUS_NAMES, CAMPUS_INFO } = repo;

  if (stage === 'middle') {
    const quota = repo.linkageOf(schoolName);
    const quotaRows = quota
      ? CAMPUS_NAMES.filter((c) => (quota.sz[c] ?? 0) > 0)
          .map((c) => ({ campus: c, campusFull: c, school: CAMPUS_INFO[c]!.school, n: quota.sz[c] as number }))
          .sort((a, b) => b.n - a.n)
      : [];
    const specialRows = (() => {
      const m = repo.specialOf(schoolName);
      if (!m) return [];
      return Object.entries(m)
        .map(([k, v]) => {
          const campus = specialToCampus(k, repo);
          return { campus, campusFull: k, school: CAMPUS_INFO[campus]?.school ?? normCampus(k), autonomy: v.autonomy ?? 0, sports: v.sports ?? 0, arts: v.arts ?? 0 };
        })
        .sort((a, b) => (b.autonomy + b.sports + b.arts) - (a.autonomy + a.sports + a.arts));
    })();
    const specialTotal = specialRows.reduce((s, r) => s + r.autonomy + r.sports + r.arts, 0);
    const batchRows = Object.entries(repo.batch2Of(schoolName)).map(([k, v]) => ({
      campus: k,
      campusFull: k,
      school: CAMPUS_INFO[k]?.school ?? normCampus(k),
      min: v.min_score,
      last: v.last_score,
    }));
    const qmap = new Map<string, { campus: string; campusFull: string; school: string; n: number }>(quotaRows.map((r) => [r.campus, r]));
    const bmap = new Map<string, { campus: string; campusFull: string; school: string; min: number | null }>(
      batchRows.map((r) => [r.campus, { campus: r.campus, campusFull: r.campusFull, school: r.school, min: r.min ?? null }]),
    );
    const batchMerged: BatchMergedRow[] = [...new Set([...qmap.keys(), ...bmap.keys()])]
      .map((c) => {
        const q = qmap.get(c);
        const b = bmap.get(c);
        return {
          campus: c,
          campusFull: b?.campusFull || q?.campusFull || c,
          school: b?.school || q?.school || normCampus(c),
          n: q?.n ?? null,
          min: b?.min ?? null,
        };
      })
      .sort((a, b) => (b.n ?? 0) - (a.n ?? 0));
    const districtRows: DistrictRow[] = Object.entries(repo.districtQuotaOf(schoolName))
      .map(([name, n]) => ({ name, n }))
      .sort((a, b) => b.n - a.n);
    return {
      specialRows,
      specialTotal,
      quota: quota ? { kaosheng: quota.kaosheng, sheng_quota: quota.sheng_quota, qu_quota: quota.qu_quota } : null,
      batchMerged,
      districtRows,
      hasMiddleData: !!quota || specialTotal > 0 || batchRows.length > 0,
      highSpecialCoverage: [],
      highCoverage: [],
      highDistrictCoverage: [],
      hasHighData: false,
    };
  }

  // high：按学校聚合全部校区
  const target = normCampus(schoolName);
  const highCampuses = CAMPUS_NAMES.filter(
    (c) => normCampus(CAMPUS_INFO[c]!.school) === target || CAMPUS_INFO[c]!.school === schoolName,
  );
  const mergedCover = new Map<string, { n: number; districts: Set<string> }>();
  for (const c of highCampuses) {
    for (const { school, n, district } of repo.quotaCoverage(c)) {
      const m = mergedCover.get(school) || { n: 0, districts: new Set<string>() };
      m.n += n;
      if (district) m.districts.add(district);
      mergedCover.set(school, m);
    }
  }
  const highCoverage: HighCoverRow[] = [...mergedCover.entries()]
    .map(([school, v]) => ({ school, n: v.n, districts: [...v.districts] }))
    .sort((a, b) => b.n - a.n)
    .slice(0, 30);
  const mergedSpecial = new Map<string, { autonomy: number; sports: number; arts: number }>();
  for (const c of highCampuses) {
    for (const s of repo.specialCoverage(c)) {
      const m = mergedSpecial.get(s.school) || { autonomy: 0, sports: 0, arts: 0 };
      m.autonomy += s.autonomy;
      m.sports += s.sports;
      m.arts += s.arts;
      mergedSpecial.set(s.school, m);
    }
  }
  const highSpecialCoverage: HighSpecialRow[] = [...mergedSpecial.entries()]
    .map(([school, v]) => ({ school, ...v }))
    .sort((a, b) => b.autonomy + b.sports + b.arts - (a.autonomy + a.sports + a.arts))
    .slice(0, 30);
  const highDistrictCoverage: { school: string; n: number }[] = repo.districtCoverage(schoolName).slice(0, 50);

  return {
    specialRows: [],
    specialTotal: 0,
    quota: null,
    batchMerged: [],
    districtRows: [],
    hasMiddleData: false,
    highSpecialCoverage,
    highCoverage,
    highDistrictCoverage,
    hasHighData: highCoverage.length > 0 || highSpecialCoverage.length > 0 || highDistrictCoverage.length > 0,
  };
}
