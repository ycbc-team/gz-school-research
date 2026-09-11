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

/** POI 分校区名归一（去括号校区），与 CAMPUS_SCHOOL 标准名对齐 */
function normCampus(s: string): string {
  return s.replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').trim();
}

export function buildLinkageModel(stage: 'middle' | 'high', schoolName: string, repo: Repository): LinkageModel {
  const { CAMPUS_SHORT, CAMPUS_SCHOOL, CAMPUS_TO_SPECIAL, CAMPUS_TO_BATCH2 } = repo;

  const specialKeyToShort = (spKey: string): string => {
    for (const [short, full] of Object.entries(CAMPUS_TO_SPECIAL)) if (full === spKey) return short;
    return spKey;
  };
  const batchKeyToShort = (bk: string): string => {
    for (const [short, full] of Object.entries(CAMPUS_TO_BATCH2)) if (full === bk) return short;
    return bk;
  };
  const schoolOf = (campus: string): string => (CAMPUS_SCHOOL as Record<string, string>)[campus] ?? campus;
  /** 简称 → 官方全称（优先第二批次名单原文，回退特殊通道名单，再回退归属高中全名） */
  const shortToFull = (c: string): string =>
    (CAMPUS_TO_BATCH2 as Record<string, string>)[c] || (CAMPUS_TO_SPECIAL as Record<string, string>)[c] || schoolOf(c);

  if (stage === 'middle') {
    const quota = repo.linkageOf(schoolName);
    const quotaRows = quota
      ? CAMPUS_SHORT.filter((c) => (quota.sz[c] ?? 0) > 0)
          .map((c) => ({ campus: c, campusFull: shortToFull(c), school: schoolOf(c), n: quota.sz[c] as number }))
          .sort((a, b) => b.n - a.n)
      : [];
    const specialRows = (() => {
      const m = repo.specialOf(schoolName);
      if (!m) return [];
      return Object.entries(m)
        .map(([k, v]) => {
          const short = specialKeyToShort(k);
          return { campus: short, campusFull: k, school: schoolOf(short), autonomy: v.autonomy ?? 0, sports: v.sports ?? 0, arts: v.arts ?? 0 };
        })
        .sort((a, b) => (b.autonomy + b.sports + b.arts) - (a.autonomy + a.sports + a.arts));
    })();
    const specialTotal = specialRows.reduce((s, r) => s + r.autonomy + r.sports + r.arts, 0);
    const batchRows = Object.entries(repo.batch2Of(schoolName)).map(([k, v]) => {
      const short = batchKeyToShort(k);
      return { campus: short, campusFull: k, school: schoolOf(short), min: v.min_score, last: v.last_score };
    });
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
          campusFull: b?.campusFull || q?.campusFull || shortToFull(c),
          school: b?.school || q?.school || schoolOf(c),
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
  const highShorts = CAMPUS_SHORT.filter(
    (c) => normCampus(CAMPUS_SCHOOL[c] ?? '') === target || CAMPUS_SCHOOL[c] === schoolName,
  );
  const mergedCover = new Map<string, { n: number; districts: Set<string> }>();
  for (const c of highShorts) {
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
  for (const c of highShorts) {
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
