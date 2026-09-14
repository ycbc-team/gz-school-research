/**
 * 升学通道查询域：名额分配（quota_matrix）/ 特招（special_matrix）/ 第二批次（batch2_scores）/
 * 区属指标到校（district_quota）/ 小学升学路线（xiaoshengchu）+ 生源反查。
 */
import { normName, looseNorm } from '../support.js';
import type { XiaoshengchuRecord } from '../types.js';
import type { DataLoaders } from './loader.js';
import { normSchoolName } from './enrollment.js';
import { CAMPUS_INFO } from './campuses.js';
import type { QuotaSchool } from './types.js';

export function createQuotaApi(loaders: DataLoaders) {
  const { quotaMatrix, specialMatrix, batch2Scores, districtQuota, middleSchools } = loaders;

  /** 任意名 → 实体 school_id（registry 同规则；local 实现避免循环依赖） */
  function resolveSchoolIdOf(name: string): string | null {
    if (!name) return null;
    const n = normName(name);
    const ln = looseNorm(name);
    for (const e of loaders.entities.entities) {
      if (normName(e.name) === n) return e.school_id;
      for (const a of e.aliases || []) {
        if (normName(a) === n) return e.school_id;
      }
    }
    for (const e of loaders.entities.entities) {
      if (looseNorm(e.name) === ln) return e.school_id;
      for (const a of e.aliases || []) {
        if (looseNorm(a) === ln) return e.school_id;
      }
    }
    return null;
  }

  /** 初中名归一查找：POI 简称/变体 → quota_matrix 标准全称（精确→归一→包含兜底） */
  const middleByNorm = new Map<string, string>();
  for (const s of quotaMatrix.schools) {
    const nk = normSchoolName(s.school);
    if (nk && !middleByNorm.has(nk)) middleByNorm.set(nk, s.school);
  }
  /** 新开办待成绩初中（note 含「新开办」）：无成绩亦无升学通道数据，禁止模糊匹配到本部链路数据 */
  const newOpeningMiddles = new Set<string>();
  for (const s of middleSchools.schools) {
    if (s.note && s.note.includes('新开办')) newOpeningMiddles.add(s.name);
  }
  function resolveMiddle(poiName: string): string | null {
    if (newOpeningMiddles.has(poiName)) return null;
    if (quotaMatrix.schools.some((s) => s.school === poiName)) return poiName;
    // 优先 school_id 外键（backfill 已回填；POI 名 → 实体 school_id → quota 行）
    const sid = resolveSchoolIdOf(poiName);
    if (sid) {
      const byId = quotaMatrix.schools.find((s) => s.school_id === sid);
      if (byId) return byId.school;
    }
    const nk = normSchoolName(poiName);
    if (nk && middleByNorm.has(nk)) return middleByNorm.get(nk)!;
    for (const s of quotaMatrix.schools) {
      const sk = normSchoolName(s.school);
      if (sk.length >= 3 && (sk.includes(nk) || nk.includes(sk))) return s.school;
    }
    return null;
  }

  /** 按初中名查升学通道汇总 */
  function linkageOf(schoolName: string): QuotaSchool | undefined {
    const canon = resolveMiddle(schoolName);
    return canon ? quotaMatrix.schools.find((s) => s.school === canon) : undefined;
  }

  /** 按初中名查特殊通道（special_matrix 键 = 初中名） */
  function specialOf(schoolName: string): Record<string, { sports?: number; arts?: number; autonomy?: number }> | undefined {
    const canon = resolveMiddle(schoolName);
    return canon ? specialMatrix.matrix[canon] : undefined;
  }

  /** 按初中名查第二批次录取分数（值 = 校区 → 记录） */
  function batch2Of(schoolName: string): Record<string, { admitted?: boolean; min_score?: number | null; last_score?: number | null }> {
    const out: Record<string, { admitted?: boolean; min_score?: number | null; last_score?: number | null }> = {};
    const canon = resolveMiddle(schoolName);
    if (!canon) return out;
    for (const [campus, rows] of Object.entries(batch2Scores.data)) {
      if (rows[canon]) out[campus] = rows[canon];
    }
    return out;
  }

  /** 按初中名查区属高中名额：{区属高中POI名: 名额} */
  function districtQuotaOf(schoolName: string): Record<string, number> {
    const canon = resolveMiddle(schoolName);
    if (!canon) return {};
    return districtQuota.data[canon] ?? {};
  }

  /** 反查：某区属高中名额分配覆盖的初中（按名额降序） */
  function districtCoverage(highName: string): { school: string; school_id: string | null; n: number }[] {
    const out: { school: string; school_id: string | null; n: number }[] = [];
    for (const [school, row] of Object.entries(districtQuota.data)) {
      const n = row[highName];
      if (n) out.push({ school, school_id: districtQuota.middle_school_ids?.[school] ?? null, n });
    }
    return out.sort((a, b) => b.n - a.n);
  }

  /** 反查：某校区 n_ji>0 的初中（名额分配覆盖，按 n_ji 降序）；campus = 官方原文校名 */
  function quotaCoverage(campus: string, top?: number): { school: string; school_id: string | null; n: number; district: string | null }[] {
    const arr = quotaMatrix.schools
      .filter((s) => (s.sz[campus] ?? 0) > 0)
      .map((s) => ({ school: s.school, school_id: s.school_id ?? null, n: s.sz[campus] as number, district: s.district }))
      .sort((a, b) => b.n - a.n);
    return top ? arr.slice(0, top) : arr;
  }

  /** 反查：某校区在 special_matrix 有记录的初中（自招/体育/艺术）；campus = 官方原文校名 */
  function specialCoverage(campus: string): { school: string; school_id: string | null; sports: number; arts: number; autonomy: number }[] {
    const spKey = CAMPUS_INFO[campus]?.special;
    if (!spKey) return [];
    const arr: { school: string; school_id: string | null; sports: number; arts: number; autonomy: number }[] = [];
    for (const [school, hs] of Object.entries(specialMatrix.matrix)) {
      const rec = hs[spKey];
      if (rec) arr.push({ school, school_id: specialMatrix.middle_school_ids?.[school] ?? null, sports: rec.sports ?? 0, arts: rec.arts ?? 0, autonomy: rec.autonomy ?? 0 });
    }
    return arr.sort((a, b) => b.autonomy + b.sports + b.arts - (a.autonomy + a.sports + a.arts));
  }

  /** 初中名 → 名额分配摘要（模糊匹配 quota_matrix，用于小学出口列表轻量展示） */
  function middleQuotaSummary(name: string): { kaosheng: number | null; sheng_quota: number | null; qu_quota: number | null } | null {
    const find = (s: QuotaSchool) => ({ kaosheng: s.kaosheng, sheng_quota: s.sheng_quota, qu_quota: s.qu_quota });
    const exact = quotaMatrix.schools.find((s) => s.school === name);
    if (exact) return find(exact);
    const nk = normSchoolName(name);
    const normHit = quotaMatrix.schools.find((s) => normSchoolName(s.school) === nk);
    if (normHit) return find(normHit);
    const core = nk || name;
    for (const s of quotaMatrix.schools) {
      const sk = normSchoolName(s.school);
      if (sk.length >= 4 && (sk.includes(core) || core.includes(sk))) return find(s);
    }
    return null;
  }

  /* ===== 小学升学路线（实体注册表 + 2026 事实表，school_id 外键，全等别名） ===== */
  interface SchoolEntityLite { school_id: string; name: string; stage: string; aliases: string[] }
  const entities = loaders.entities.entities as SchoolEntityLite[];
  const entityById = new Map(entities.map((e) => [e.school_id, e]));
  /** 从 group 文本解析区名（如「番禺区小升初对口（单校）」→「番禺区」），无区前缀返回 null */
  function districtOfGroup(group: string | null): string | null {
    if (!group) return null;
    const m = /(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区/.exec(group);
    return m ? `${m[1]}区` : null;
  }
  type FactRec = {
    school_id: string; group_id: number;
    feed_school_ids: string[]; feed_unresolved: string[];
    direct_feed_school_id: string | null;
    source_note?: string; data_gaps?: string | null;
  };
  const xsGroups = loaders.xiaoshengchu.groups;
  const groupsById = new Map(xsGroups.map((g) => [g.id, g]));
  const facts = loaders.xiaoshengchu.records as FactRec[];
  const factByPrimaryId = new Map<string, FactRec>();
  for (const r of facts) if (r.school_id) factByPrimaryId.set(r.school_id, r);

  /** 把事实 record 适配成页面在用的旧形状（feed_junior_highs: 字符串数组） */
  function shapeRecord(r: FactRec, displayName: string): XiaoshengchuRecord {
    const feedNames = (r.feed_school_ids || []).map((id) => entityById.get(id)?.name).filter(Boolean) as string[];
    const g = groupsById.get(r.group_id);
    return {
      name: displayName,
      group: g?.name ?? null,
      feed_junior_highs: [...feedNames, ...(r.feed_unresolved || [])],
      direct_feed: r.direct_feed_school_id ? entityById.get(r.direct_feed_school_id)?.name ?? null : null,
      source_url: g?.source_urls.join('; ') ?? '',
      source_note: r.source_note ?? '',
      data_gaps: r.data_gaps ?? g?.data_gaps ?? null,
    } as XiaoshengchuRecord;
  }
  /**
   * 按小学实体 id 查升学路线。事实表按 school_id 键控，零名字匹配；
   * 名字→id 的解析只存在于数据生产脚本（build_xiaoshengchu_all.py）。
   * 无 id（如旧链接不带 ?id=）返回 null，不做猜测。
   */
  function xiaoshengchuOf(schoolId: string | null | undefined): XiaoshengchuRecord | null {
    if (!schoolId) return null;
    const r = factByPrimaryId.get(schoolId);
    return r ? shapeRecord(r, entityById.get(schoolId)?.name ?? '(未知)') : null;
  }

  /**
   * 反查：某初中实体的生源小学。数据匹配只用 school_id（事实表 feed_school_ids /
   * direct_feed_school_id 均为 id），零名字匹配。
   * direct_feed 语义：仅当该小学的对口直升目标就是「当前查询的初中」时非空（值为该初中名），
   * 否则一律为 null——避免把「小学直升其它初中」误标成「直升本校」（派位组内可填报 ≠ 对口直升）。
   */
  function middlePrimaryFeed(middleId: string | null | undefined): { primary: string; group: string | null; direct_feed: string | null }[] {
    if (!middleId) return [];
    const out: { primary: string; group: string | null; direct_feed: string | null }[] = [];
    for (const r of facts) {
      const inGroup = (r.feed_school_ids || []).includes(middleId);
      const directHere = r.direct_feed_school_id === middleId;
      if (!inGroup && !directHere) continue;
      const pe = r.school_id ? entityById.get(r.school_id) : null;
      out.push({
        primary: pe ? pe.name : '(未知)',
        group: groupsById.get(r.group_id)?.name ?? null,
        direct_feed: directHere ? (entityById.get(r.direct_feed_school_id!)?.name ?? null) : null,
      });
    }
    return out;
  }

  return {
    linkageOf, specialOf, batch2Of, districtQuotaOf, districtCoverage,
    quotaCoverage, specialCoverage, middleQuotaSummary,
    xiaoshengchuOf, middlePrimaryFeed,
  };
}
