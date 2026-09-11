/**
 * 升学通道查询域：名额分配（quota_matrix）/ 特招（special_matrix）/ 第二批次（batch2_scores）/
 * 区属指标到校（district_quota）/ 小学升学路线（xiaoshengchu）+ 生源反查。
 */
import { ADCODE_TO_DISTRICT } from '../const.js';
import { normName } from '../support.js';
import type { XiaoshengchuRecord } from '../types.js';
import type { DataLoaders } from './loader.js';
import { normSchoolName } from './enrollment.js';
import { CAMPUS_TO_SPECIAL } from './campuses.js';
import type { QuotaSchool } from './types.js';

export function createQuotaApi(loaders: DataLoaders) {
  const { quotaMatrix, specialMatrix, batch2Scores, districtQuota, middleSchools } = loaders;

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
  function districtCoverage(highName: string): { school: string; n: number }[] {
    const out: { school: string; n: number }[] = [];
    for (const [school, row] of Object.entries(districtQuota.data)) {
      const n = row[highName];
      if (n) out.push({ school, n });
    }
    return out.sort((a, b) => b.n - a.n);
  }

  /** 反查：某校区 n_ji>0 的初中（名额分配覆盖，按 n_ji 降序） */
  function quotaCoverage(campusShort: string, top?: number): { school: string; n: number; district: string | null }[] {
    const arr = quotaMatrix.schools
      .filter((s) => (s.sz[campusShort] ?? 0) > 0)
      .map((s) => ({ school: s.school, n: s.sz[campusShort] as number, district: s.district }))
      .sort((a, b) => b.n - a.n);
    return top ? arr.slice(0, top) : arr;
  }

  /** 反查：某校区在 special_matrix 有记录的初中（自招/体育/艺术） */
  function specialCoverage(campusShort: string): { school: string; sports: number; arts: number; autonomy: number }[] {
    const spKey = CAMPUS_TO_SPECIAL[campusShort];
    if (!spKey) return [];
    const arr: { school: string; sports: number; arts: number; autonomy: number }[] = [];
    for (const [school, hs] of Object.entries(specialMatrix.matrix)) {
      const rec = hs[spKey];
      if (rec) arr.push({ school, sports: rec.sports ?? 0, arts: rec.arts ?? 0, autonomy: rec.autonomy ?? 0 });
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
  // POI 表：school_id -> adcode（district 从点位 join，entity 不存）
  const poiAdcodeBySchool = new Map<string, string>();
  for (const p of [...loaders.primarySchools.schools, ...loaders.middleSchools.schools, ...(loaders.highSchools.schools || [])]) {
    if (p.school_id) poiAdcodeBySchool.set(p.school_id, p.adcode as string);
  }
  function districtOfSchool(schoolId: string): string {
    const ad = poiAdcodeBySchool.get(schoolId);
    return ad ? (ADCODE_TO_DISTRICT[ad] || '') : '';
  }
  /** 从 group 文本解析区名（如「番禺区小升初对口（单校）」→「番禺区」），无区前缀返回 null */
  function districtOfGroup(group: string | null): string | null {
    if (!group) return null;
    const m = /(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区/.exec(group);
    return m ? `${m[1]}区` : null;
  }
  function buildAliasIndex(stage: string): Map<string, SchoolEntityLite[]> {
    const m = new Map<string, SchoolEntityLite[]>();
    for (const e of entities) {
      if (e.stage !== stage) continue;
      for (const a of e.aliases) {
        const k = normName(a); if (!k) continue;
        if (!m.has(k)) m.set(k, []);
        m.get(k)!.push(e);
      }
    }
    return m;
  }
  const primaryAlias = buildAliasIndex('primary');
  const middleAlias = buildAliasIndex('middle');
  function resolveEntity(idx: Map<string, SchoolEntityLite[]>, name: string, district?: string | null): SchoolEntityLite | null {
    const list = idx.get(normName(name));
    if (!list || !list.length) return null;
    if (list.length === 1) return list[0]!;
    const want = district && /^\d{6}$/.test(district) ? ADCODE_TO_DISTRICT[district] : district;
    return (want && list.find((e) => districtOfSchool(e.school_id) === want)) || list[0]!;
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
   * 按 POI 名查小学升学路线：POI 名经实体注册表别名全等解析为 school_id，再查事实表。
   * district 仅在跨区同名时精确消歧，不传/不中回退首条（确定性，不猜测）。
   */
  function xiaoshengchuOf(poiName: string, district?: string | null): XiaoshengchuRecord | null {
    const ent = resolveEntity(primaryAlias, poiName, district);
    if (!ent) return null;
    const r = factByPrimaryId.get(ent.school_id);
    return r ? shapeRecord(r, ent.name) : null;
  }

  /**
   * 反查：某初中 POI 的生源小学。POI 名→初中实体 school_id→遍历事实表 feed 命中。
   * 全等别名，不做包含匹配。
   */
  function middlePrimaryFeed(middleName: string): { primary: string; group: string | null; direct_feed: string | null }[] {
    const ent = resolveEntity(middleAlias, middleName);
    if (!ent) return [];
    const out: { primary: string; group: string | null; direct_feed: string | null }[] = [];
    for (const r of facts) {
      const hit = (r.feed_school_ids || []).includes(ent.school_id) ||
        r.direct_feed_school_id === ent.school_id;
      if (hit) {
        const pe = r.school_id ? entityById.get(r.school_id) : null;
        out.push({
          primary: pe ? pe.name : '(未知)', group: groupsById.get(r.group_id)?.name ?? null,
          direct_feed: r.direct_feed_school_id ? entityById.get(r.direct_feed_school_id)?.name ?? null : null,
        });
      }
    }
    return out;
  }

  return {
    linkageOf, specialOf, batch2Of, districtQuotaOf, districtCoverage,
    quotaCoverage, specialCoverage, middleQuotaSummary,
    xiaoshengchuOf, middlePrimaryFeed,
  };
}
