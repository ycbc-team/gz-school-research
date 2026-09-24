/**
 * 升学通道查询域：名额分配（quota_matrix）/ 特招（special_matrix）/ 第二批次（batch2_scores）/
 * 区属指标到校（district_quota）/ 小学升学路线（xiaoshengchu）+ 生源反查。
 */
import { normName, looseNorm } from '../support.js';
import type { XiaoshengchuRecord } from '../types.js';
import type { DataLoaders } from './loader.js';
import { normSchoolName } from './enrollment.js';
import type { QuotaSchool, QuotaRowId, QuotaRowName, Batch2Record } from './types.js';

export function createQuotaApi(loaders: DataLoaders) {
  const { quotaMatrix, specialMatrix, batch2Scores, districtQuota, middleSchools } = loaders;

  /** 实体注册表（id → 实体）：dist 精简后 ids 行无 school 名，展示名由实体表 join；
   *  提前到顶部（districtCoverage/quotaCoverage 反查转名用） */
  interface SchoolEntityLite { school_id: string; name: string; stage: string; aliases: string[] }
  const entityById = new Map<string, SchoolEntityLite>(
    (loaders.entities.entities as SchoolEntityLite[]).map((e) => [e.school_id, e]),
  );

  /** 配额行定位器：ids 行按 school_id（实体表外键），schools 行按官方原文名 */
  type QuotaLocator = { school_id: string } | { school: string };
  const quotaById = new Map<string, QuotaRowId>(quotaMatrix.ids.map((r) => [r.school_id, r]));
  const quotaByName = new Map<string, QuotaRowName>(quotaMatrix.schools.map((r) => [r.school, r]));

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

  /** 初中名归一查找：POI 简称/变体 → 配额行 locator。
   *  ids 行（7 区内有实体）走实体匹配（school_id 归并，法人行 school_ids 任一校区命中）；
   *  schools 行（7 区外无实体）走原文精确 → norm → 包含兜底。 */
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
  function resolveMiddle(poiName: string): QuotaLocator | null {
    if (newOpeningMiddles.has(poiName)) return null;
    // ① 官方名单原文名精确索引：py 层 backfill 已把法人聚合/主 id 归一结果固化进
    //    name_index，运行时直接 id 精准匹配，不做任何名称推断
    const oid = quotaMatrix.name_index[poiName];
    if (oid && quotaById.has(oid)) return { school_id: oid };
    // ② schools 行（7 区外无实体）官方原文名
    if (quotaByName.has(poiName)) return { school: poiName };
    // ③ 实体表 name/aliases 归一全等索引（POI/校区名 → school_id）
    //    法人行 school_ids 数组：任一校区实体都归并到法人行（官方配额按法人单位公布）
    const sid = resolveSchoolIdOf(poiName);
    if (sid) {
      if (quotaById.has(sid)) return { school_id: sid };
      for (const r of quotaMatrix.ids) {
        if ((r.school_ids || []).includes(sid)) return { school_id: r.school_id };
      }
    }
    // ④ schools 行归一全等（确定性归一，与 backfill SchoolMatcher 同规则）
    const nk = normSchoolName(poiName);
    if (nk && middleByNorm.has(nk)) return { school: middleByNorm.get(nk)! };
    return null;
  }

  /** locator → 配额行（ids 行按 school_id / schools 行按原文名） */
  function quotaRowOf(loc: QuotaLocator | null): QuotaSchool | undefined {
    if (!loc) return undefined;
    return 'school_id' in loc ? quotaById.get(loc.school_id) : quotaByName.get(loc.school);
  }

  /** 按初中名查升学通道汇总 */
  function linkageOf(schoolName: string): QuotaSchool | undefined {
    return quotaRowOf(resolveMiddle(schoolName));
  }

  /** 高中实体 school_id → 2026 自主招生计划数（autonomy_plan 键全为构建期 resolve 的 id；
   *  实体表缺口无详情页不参与查询）；计划数≠资格名单人数≠录取人数 */
  function autonomyPlanOf(schoolId: string | null | undefined): number | null {
    if (!schoolId) return null;
    return specialMatrix.autonomy_plan?.[schoolId] ?? null;
  }

  /** 高中实体 school_id → 2026 体育/艺术特长生计划数（special_matrix.special_plan，构建期已映射实体外键） */
  function specialPlanOf(schoolId: string | null | undefined): {
    sports: number;
    arts: number;
    sportsProjects: { project: string; plan: number; note?: string }[];
    artsProjects: { project: string; plan: number; note?: string }[];
  } | null {
    if (!schoolId) return null;
    const p = (specialMatrix as Record<string, any>).special_plan?.[schoolId] as
      | {
          sports?: number;
          arts?: number;
          sports_projects?: { project: string; plan: number; note?: string }[];
          arts_projects?: { project: string; plan: number; note?: string }[];
        }
      | undefined;
    if (!p) return null;
    return {
      sports: p.sports ?? 0,
      arts: p.arts ?? 0,
      sportsProjects: p.sports_projects ?? [],
      artsProjects: p.arts_projects ?? [],
    };
  }

  /** dist 双层表按 locator 取行：ids 行走 school_id **及 school_ids 全部校区**
   *  （backfill 的 dist 键是官方名单名直接 resolve 的 school_id，如「广州市第一中学」→ 初中部
   *  2dc142ec；quota 行主 id 是法人聚合归一后的 2653da64——两者必须并查）。
   *  schools 行按原文名；返回内层 ids/schools 合并（重复键保留首个）。 */
  function locatorRows(
    loc: QuotaLocator,
    table: { ids: Record<string, { ids: Record<string, any>; schools: Record<string, any> }>; schools: Record<string, { ids: Record<string, any>; schools: Record<string, any> }> },
  ): Record<string, any> {
    const out: Record<string, any> = {};
    const merge = (rows: { ids: Record<string, any>; schools: Record<string, any> } | undefined) => {
      if (!rows) return;
      for (const [k, v] of Object.entries({ ...rows.ids, ...rows.schools })) {
        if (!(k in out)) out[k] = v;
      }
    };
    if ('school_id' in loc) {
      const r = quotaById.get(loc.school_id);
      const sids = r ? [loc.school_id, ...(r.school_ids || [])] : [loc.school_id];
      for (const sid of sids) merge(table.ids[sid]);
    } else {
      merge(table.schools[loc.school]);
    }
    return out;
  }

  /** 按初中名查第二批次录取分数：batch2 外层键=高中校区 id/原文名、内层=初中（与 district 反向），
   *  须反向扫描外层，收集内层 ids/schools 命中目标初中（含 school_ids 全部校区）的行。 */
  function batch2Of(schoolName: string): Record<string, Batch2Record> {
    const out: Record<string, Batch2Record> = {};
    const loc = resolveMiddle(schoolName);
    if (!loc) return out;
    const sids = 'school_id' in loc
      ? (() => { const r = quotaById.get(loc.school_id); return r ? [loc.school_id, ...(r.school_ids || [])] : [loc.school_id]; })()
      : [];
    const entries = Object.entries({ ...batch2Scores.ids, ...batch2Scores.schools }) as [string, { ids: Record<string, Batch2Record>; schools: Record<string, Batch2Record> }][];
    for (const [hk, rows] of entries) {
      if ('school_id' in loc) {
        for (const sid of sids) {
          const v = rows.ids[sid];
          if (v) { if (!(hk in out)) out[hk] = v; break; }
        }
      } else {
        const v = rows.schools[loc.school];
        if (v && !(hk in out)) out[hk] = v;
      }
    }
    return out;
  }

  /** 按初中名查区属高中名额（键=区属高中 id 或原文名） */
  function districtQuotaOf(schoolName: string): Record<string, number> {
    return locatorRows(resolveMiddle(schoolName) as QuotaLocator, districtQuota as never) as Record<string, number>;
  }

  /** 反查：某区属高中名额分配覆盖的初中（按名额降序）。
   *  高中名 → 实体 id 反查 ids 行；schools 行（无实体高中）按原文名匹配。
   *  初中展示名：ids 行走实体表 join，schools 行原文。 */
  function districtCoverage(highName: string): { school: string; school_id: string | null; n: number }[] {
    const out: { school: string; school_id: string | null; n: number }[] = [];
    const hid = resolveSchoolIdOf(highName);
    for (const [sid, row] of Object.entries(districtQuota.ids)) {
      const n = hid ? (row.ids[hid] ?? 0) : 0;
      const n2 = row.schools[highName] ?? 0;
      if (n || n2) out.push({ school: entityById.get(sid)?.name ?? sid, school_id: sid, n: n || n2 });
    }
    for (const [name, row] of Object.entries(districtQuota.schools)) {
      const n = hid ? (row.ids[hid] ?? 0) : 0;
      const n2 = row.schools[highName] ?? 0;
      if (n || n2) out.push({ school: name, school_id: null, n: n || n2 });
    }
    return out.sort((a, b) => b.n - a.n);
  }

  /** 反查：某校区 n_ji>0 的初中（名额分配覆盖，按 n_ji 降序）；sid = 校区实体 id
   *  （实体表缺口校区无详情页，不参与反查；sz 键全为 id） */
  function quotaCoverage(sid: string, top?: number): { school: string; school_id: string | null; n: number; district: string | null }[] {
    const arr = [
      ...quotaMatrix.ids
        .filter((s) => (s.sz?.[sid] ?? 0) > 0)
        .map((s) => ({
          school: entityById.get(s.school_id)?.name ?? s.school_id,
          school_id: s.school_id,
          n: s.sz![sid] as number,
          district: s.district,
        })),
      ...quotaMatrix.schools
        .filter((s) => (s.sz?.[sid] ?? 0) > 0)
        .map((s) => ({ school: s.school, school_id: null, n: s.sz![sid] as number, district: s.district })),
    ].sort((a, b) => b.n - a.n);
    return top ? arr.slice(0, top) : arr;
  }



  /** 初中名 → 名额分配摘要（复用 resolveMiddle 定位，ids/schools 行统一） */
  function middleQuotaSummary(name: string): { kaosheng: number | null; sheng_quota: number | null; qu_quota: number | null } | null {
    const q = quotaRowOf(resolveMiddle(name));
    if (!q) return null;
    return { kaosheng: q.kaosheng, sheng_quota: q.sheng_quota, qu_quota: q.qu_quota };
  }

  /* ===== 小学升学路线（实体注册表 + 2026 事实表，school_id 外键，全等别名） ===== */
  const entities = loaders.entities.entities as SchoolEntityLite[];
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
    linkageOf, autonomyPlanOf, specialPlanOf, batch2Of, districtQuotaOf, districtCoverage,
    quotaCoverage, middleQuotaSummary,
    xiaoshengchuOf, middlePrimaryFeed,
  };
}
