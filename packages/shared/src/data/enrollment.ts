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
  school_id: string;
  plan_classes?: number | null;
  plan_count?: number | null;
  nature?: string;
  zone?: string;
  note?: string;
  source?: string;
  matchedBy: string;
}

/**
 * 小学 2026 招生计划查询域（school_id 外键驱动）：
 * - 构建期已由 Python SchoolMatcher 把官方名 → 实体 school_id 匹配完成，records 只存
 *   school_id + 招生字段（无名字/坐标——实体表/POI 表按 school_id 联查）
 * - 运行时优先 school_id 精确命中；仅当调用方只有名字（无 school_id）时，
 *   用实体表（name/aliases，stage=primary）做 精确 → 归一 → 包含 兜底，命中后按 id 查
 */
export function createEnrollmentApi(loaders: DataLoaders) {
  const enrollments = loaders.enrollments;
  // records（公办）+ minban（民办招生计划）统一按 school_id 建索引
  const ENROLL_BY_ID = new Map<string, EnrollmentMatch>();
  for (const e of enrollments) {
    for (const r of e.records) if (r.school_id) ENROLL_BY_ID.set(r.school_id, { ...r, matchedBy: '' });
    for (const m of e.minban || []) {
      const sid = m.school_id;
      if (!sid) continue;
      ENROLL_BY_ID.set(sid, { ...m, school_id: sid, nature: '民办', matchedBy: '' });
    }
  }
  // 实体表名索引（小学实体）：school_id 是匹配真源，名字/别名只是搜索入口
  const entityByName = new Map<string, { school_id: string; name: string }>();
  const entityByNorm = new Map<string, { school_id: string; name: string }>();
  for (const ent of loaders.entities?.entities ?? []) {
    if (ent.stage !== 'primary') continue;
    if (!entityByName.has(ent.name)) entityByName.set(ent.name, ent);
    for (const a of ent.aliases ?? []) if (a && !entityByName.has(a)) entityByName.set(a, ent);
  }
  for (const [k, ent] of entityByName) {
    const nk = normSchoolName(k);
    if (nk && !entityByNorm.has(nk)) entityByNorm.set(nk, ent);
  }

  /**
   * 按小学 school_id 或名字匹配 2026 招生计划：school_id 精确 → 实体表精确/归一 → 包含兜底。
   * 调用方优先传 school_id（地图点/详情页均有），名字仅作无 id 时兜底。
   */
  function matchEnrollment(schoolNameOrId: string): EnrollmentMatch | null {
    const byId = ENROLL_BY_ID.get(schoolNameOrId);
    if (byId) return { ...byId, matchedBy: 'id' };
    const ent = entityByName.get(schoolNameOrId) || entityByNorm.get(normSchoolName(schoolNameOrId));
    if (ent) {
      const r = ENROLL_BY_ID.get(ent.school_id);
      if (r) return { ...r, matchedBy: ent.name === schoolNameOrId ? 'entity_exact' : 'entity_norm' };
    }
    // 包含兜底：实体表归一名互为子串（搜索场景）
    const core = normSchoolName(schoolNameOrId);
    if (core && core.length >= 4) {
      for (const [k, ent2] of entityByNorm) {
        // k 也需足够长（≥4）："实验"/"小学"等泛化归一 key 会串扰任意含其子串的学校
        if (k.length >= 4 && (k.includes(core) || core.includes(k))) {
          const r = ENROLL_BY_ID.get(ent2.school_id);
          if (r) return { ...r, matchedBy: 'fuzzy' };
        }
      }
    }
    return null;
  }

  return { enrollments: enrollments as EnrollmentSnapshot[], matchEnrollment };
}

/**
 * 初中 2026 招生计划查询域（初中视角）：按 school_id 索引，返回班数/范围/机制/派位组。
 * 与小学 matchEnrollment 不同：初中按 POI school_id 精确外键，不做模糊匹配。
 *
 * 「一校多规则」：同一 school_id 可能对应多条招生记录（同一初中在多区、或多机制并存，
 * 例如番禺校区+越秀派位、单校划片+全区电脑派位）。middleEnrollmentsOf 返回全部记录，
 * 由调用方逐条渲染；middleEnrollmentOf 保留首条语义供兼容。
 */
export interface MiddleEnrollmentMatch {
  record: MiddleEnrollmentRecord;
  mechanismDef: MiddleMechanismDef;
  /** 记录所在区（多区并存时用于区分规则来源） */
  district: string;
}
const DEFAULT_DEFS: Record<MiddleMechanism, MiddleMechanismDef> = {
  single_zone: { label: '单校划片', can_lose: false, lose_text: null },
  group_paidui: { label: '多校电脑派位', can_lose: false, lose_text: '组内学校兜底。' },
  single_lottery: { label: '单校电脑抽签', can_lose: true, lose_text: '未中签回原学区。' },
};
export function createMiddleEnrollmentApi(loaders: DataLoaders) {
  const list = loaders.middleEnrollments || [];
  // dist 合并结构（2026-09-23）：mechanisms 顶层一份；group_id 引用独立组表。
  // 2026-09-24 精简：dist record 不存 school 名称/group_members（组表 members 已删，无前端消费），
  // 组信息（组名/生源小学）由调用方经 middleEnrollmentGroups 联查。
  const mechanisms = loaders.middleEnrollmentMechanisms || {};
  const byId = new Map<string, MiddleEnrollmentRecord>();
  const byIdAll = new Map<string, MiddleEnrollmentMatch[]>();
  for (const snap of list) {
    for (const r0 of snap.records) {
      const r = r0;
      if (r.school_id && !byId.has(r.school_id)) byId.set(r.school_id, r);
      const def = mechanisms[r.mechanism] || DEFAULT_DEFS[r.mechanism];
      const match: MiddleEnrollmentMatch = { record: r, mechanismDef: def, district: snap.district };
      const ids = r.school_id ? [r.school_id, ...(r.school_ids || [])] : (r.school_ids || []);
      for (const id of ids) {
        const arr = byIdAll.get(id) || [];
        arr.push(match);
        byIdAll.set(id, arr);
      }
    }
  }
  /** 按初中 POI school_id 查 2026 招生计划全部规则（一校多规则）；无数据返回 null */
  function middleEnrollmentsOf(schoolId: string | null | undefined): MiddleEnrollmentMatch[] | null {
    if (!schoolId) return null;
    return byIdAll.get(schoolId) || null;
  }
  /** 兼容：返回该 school_id 的首条规则；无数据返回 null */
  function middleEnrollmentOf(schoolId: string | null | undefined): MiddleEnrollmentMatch | null {
    const arr = middleEnrollmentsOf(schoolId);
    return arr && arr.length ? (arr[0] ?? null) : null;
  }
  return { middleEnrollmentOf, middleEnrollmentsOf };
}
