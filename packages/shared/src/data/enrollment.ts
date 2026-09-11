/**
 * 招生计划匹配域：小学 2026 招生计划（含校名变体归一：精确 → 归一 → 包含兜底）。
 */
import type { EnrollmentSnapshot } from '../types.js';
import type { DataLoaders } from './loader.js';

/** 归一：去 广州市/广州 前缀、去括号及括号内容、去 小学/学校/校区 后缀 */
export function normSchoolName(s: string): string {
  return s
    .replace(/^(广州市|广州)/, '')
    .replace(/（[^）]*）/g, '')
    .replace(/\([^)]*\)/g, '')
    .replace(/(小学|学校|校区|中学|初中)$/, '')
    .trim();
}

export interface EnrollmentMatch {
  school: string;
  school_id: string;
  poi_name: string;
  plan_classes?: number | null;
  nature?: string;
  zone?: string;
  note?: string;
  source?: string;
  matchedBy: string;
}

export function createEnrollmentApi(loaders: DataLoaders) {
  const enrollments = loaders.enrollments;
  const ENROLL_FLAT = enrollments.flatMap((e) => e.records);
  const enrollByExact = new Map<string, (typeof ENROLL_FLAT)[number]>();
  const enrollByNorm = new Map<string, (typeof ENROLL_FLAT)[number]>();
  for (const r of ENROLL_FLAT) {
    if (!enrollByExact.has(r.school)) enrollByExact.set(r.school, r);
    if (r.poi_name && !enrollByExact.has(r.poi_name)) enrollByExact.set(r.poi_name, r);
    if (r.school_id && !enrollByExact.has(r.school_id)) enrollByExact.set(r.school_id, r);
    const nk = normSchoolName(r.school);
    if (nk && !enrollByNorm.has(nk)) enrollByNorm.set(nk, r);
    const nk2 = normSchoolName(r.poi_name);
    if (nk2 && !enrollByNorm.has(nk2)) enrollByNorm.set(nk2, r);
  }

  /** 按小学名（POI 名）匹配 2026 招生计划：精确 → 归一 → 包含兜底 */
  function matchEnrollment(schoolName: string): EnrollmentMatch | null {
    const exact = enrollByExact.get(schoolName);
    if (exact) return { ...exact, matchedBy: 'exact' };
    const nk = normSchoolName(schoolName);
    if (nk) {
      const n = enrollByNorm.get(nk);
      if (n) return { ...n, matchedBy: 'norm' };
    }
    // 包含兜底：归一后互为子串（如 POI「沙面小学(凯粤湾校区)」↔ 计划「沙面小学凯粤湾校区」）
    const core = nk || schoolName;
    for (const [k, r] of enrollByNorm) {
      if (k.length >= 4 && (k.includes(core) || core.includes(k))) return { ...r, matchedBy: 'fuzzy' };
    }
    return null;
  }

  return { enrollments: enrollments as EnrollmentSnapshot[], matchEnrollment };
}
