/**
 * 学校名归一化与 tier1 梯队匹配 —— 与 scripts/build_tier1_js.py 的匹配验证算法保持一致：
 * 长别名优先；poi_norm == alias 或（alias 长度 >= 4 且 poi_norm 以 alias 开头）视为命中。
 */
import type { Tier1School } from './types.js';

/** 归一化校名：去「广州市」前缀、全半角括号统一后去括号、去空白 */
export function normName(s: string): string {
  return s
    .replace(/广州市/g, '')
    .replace(/（/g, '(')
    .replace(/）/g, ')')
    .replace(/[()]/g, '')
    .replace(/\s+/g, '');
}

/** 构建 (归一化别名, 学校) 表，长别名优先 */
export function buildAliasTable(
  schools: ReadonlyArray<Tier1School>,
): Array<{ alias: string; school: Tier1School }> {
  const table: Array<{ alias: string; school: Tier1School }> = [];
  const seen = new Set<string>();
  for (const sc of schools) {
    const aliases = sc.aliases && sc.aliases.length > 0 ? sc.aliases : [sc.name];
    for (const a of aliases) {
      const na = normName(a);
      if (!na || seen.has(na)) continue;
      seen.add(na);
      table.push({ alias: na, school: sc });
    }
  }
  table.sort((x, y) => y.alias.length - x.alias.length);
  return table;
}

/** 用点位名匹配梯队学校；未命中返回 undefined */
export function matchTier1ByPoiName(
  poiName: string,
  schools: ReadonlyArray<Tier1School>,
  table: ReadonlyArray<{ alias: string; school: Tier1School }> = buildAliasTable(schools),
): Tier1School | undefined {
  const pn = normName(poiName);
  if (!pn) return undefined;
  for (const { alias, school } of table) {
    if (pn === alias || (alias.length >= 4 && pn.startsWith(alias))) return school;
  }
  return undefined;
}

/** 给一组点位批量打上匹配到的梯队结论（含 aliases 表，只需构建一次） */
export function attachTier1ToPois(
  pois: ReadonlyArray<{ name: string }>,
  tier1Schools: ReadonlyArray<Tier1School>,
): Map<string, Tier1School> {
  const table = buildAliasTable(tier1Schools);
  const hits = new Map<string, Tier1School>();
  for (const p of pois) {
    const hit = matchTier1ByPoiName(p.name, tier1Schools, table);
    if (hit) hits.set(p.name, hit);
  }
  return hits;
}
