/**
 * 招生计划匹配域：小学 2026 招生计划（含校名变体归一：精确 → 归一 → 包含兜底）。
 */
import type { EnrollmentSnapshot, MiddleEnrollmentSnapshot, MiddleEnrollmentRecord, MiddleMechanismDef, MiddleMechanism } from '../types.js';
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

/**
 * 初中 2026 招生计划查询域（初中视角）：按 school_id 索引，返回班数/范围/机制/派位组。
 * 与小学 matchEnrollment 不同：初中按 POI school_id 精确外键，不做模糊匹配。
 */
export interface MiddleEnrollmentMatch {
  record: MiddleEnrollmentRecord;
  mechanismDef: MiddleMechanismDef;
}
export function createMiddleEnrollmentApi(loaders: DataLoaders) {
  const list = loaders.middleEnrollments || [];
  const byId = new Map<string, MiddleEnrollmentRecord>();
  const byName = new Map<string, MiddleEnrollmentRecord>();
  const mechanismsByDistrict = new Map<string, Record<MiddleMechanism, MiddleMechanismDef>>();
  for (const snap of list) {
    if (snap.mechanisms) mechanismsByDistrict.set(snap.district, snap.mechanisms);
    for (const r of snap.records) {
      if (r.school_id && !byId.has(r.school_id)) byId.set(r.school_id, r);
      if (r.school && !byName.has(r.school)) byName.set(r.school, r);
    }
  }
  /** 按初中 POI school_id 查 2026 招生计划；无数据返回 null */
  function middleEnrollmentOf(schoolId: string | null | undefined): MiddleEnrollmentMatch | null {
    if (!schoolId) return null;
    const r = byId.get(schoolId);
    if (!r) return null;
    // 机制定义优先从区级快照取，否则用内置默认
    let def: MiddleMechanismDef | undefined;
    for (const snap of list) {
      if (snap.mechanisms && snap.mechanisms[r.mechanism]) { def = snap.mechanisms[r.mechanism]; break; }
    }
    if (!def) {
      def = { single_zone: {label:'单校划片',can_lose:false,lose_text:null},
              group_paidui: {label:'多校电脑派位',can_lose:false,lose_text:'组内学校兜底。'},
              single_lottery: {label:'单校电脑抽签',can_lose:true,lose_text:'未中签回原学区。'} }[r.mechanism];
    }
    return { record: r, mechanismDef: def };
  }
  return { middleEnrollmentOf };
}
