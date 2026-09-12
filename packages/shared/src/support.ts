/**
 * 学校名归一化与 tier1 梯队匹配。
 * 匹配策略：仅全等匹配（归一化后 === 记录名/别名），不做前缀/包含/模糊匹配；
 * 校区与名称变体一律显式写入 aliases（数据驱动、可审计、可单测）。
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

/**
 * 归一 + 学部/校区后缀容错：normName 后再去掉尾部「初中部/高中部/小学部/校区/分校/学校/部」。
 * 用于官方名单原文（无学部后缀）与 POI 名（普遍带「(初中部)/(高中部)」）的跨源全等匹配。
 * 仅全等匹配（不模糊），不会误配；与 scripts/linkage/backfill_school_ids.py 的 loose 规则一致。
 */
export function looseNorm(s: string): string {
  return normName(s).replace(/(初中部|高中部|小学部|校区|分校|学校|部)$/, '');
}

/**
 * 构建 (归一化别名, 口碑记录) 表，长别名优先。
 * 别名唯一宿主为实体注册表 entities（POI name + aliases）；
 * 口碑记录通过 school_ids 关联实体，不再自存别名（孤儿记录除外，但不参与匹配）。
 */
export function buildAliasTable(
  schools: ReadonlyArray<Tier1School>,
  entities: ReadonlyArray<{ school_id: string; name: string; aliases?: string[] }>,
): Array<{ alias: string; school: Tier1School }> {
  const tierBySchoolId = new Map<string, Tier1School>();
  for (const sc of schools) {
    for (const sid of sc.school_ids || []) {
      if (!tierBySchoolId.has(sid)) tierBySchoolId.set(sid, sc);
    }
  }
  const table: Array<{ alias: string; school: Tier1School }> = [];
  const seen = new Set<string>();
  for (const e of entities) {
    const sc = tierBySchoolId.get(e.school_id);
    if (!sc) continue;
    for (const a of [e.name, ...(e.aliases || [])]) {
      const na = normName(a);
      if (!na || seen.has(na)) continue;
      seen.add(na);
      table.push({ alias: na, school: sc });
    }
  }
  table.sort((x, y) => y.alias.length - x.alias.length);
  return table;
}

/**
 * 用点位名匹配梯队学校；未命中返回 undefined。
 * 匹配策略：**仅全等匹配**（归一化后的点位名 === 记录名/别名），不做任何前缀/包含/模糊匹配。
 * 校区与名称变体一律显式写入记录的 aliases（数据驱动、可审计、可单测），
 * 避免「广东实验中学越秀学校」被「广东实验中学」前缀误配为本部口碑等历史 bug。
 */
export function matchTier1ByPoiName(
  poiName: string,
  schools: ReadonlyArray<Tier1School>,
  table?: ReadonlyArray<{ alias: string; school: Tier1School }>,
  entities?: ReadonlyArray<{ school_id: string; name: string; aliases?: string[] }>,
): Tier1School | undefined {
  const t = table ?? buildAliasTable(schools, entities ?? []);
  const pn = normName(poiName);
  if (!pn) return undefined;
  for (const { alias, school } of t) {
    if (pn === alias) return school;
  }
  return undefined;
}

/** 给一组点位批量打上匹配到的梯队结论（含 aliases 表，只需构建一次） */
export function attachTier1ToPois(
  pois: ReadonlyArray<{ name: string }>,
  tier1Schools: ReadonlyArray<Tier1School>,
  entities: ReadonlyArray<{ school_id: string; name: string; aliases?: string[] }>,
): Map<string, Tier1School> {
  const table = buildAliasTable(tier1Schools, entities);
  const hits = new Map<string, Tier1School>();
  for (const p of pois) {
    const hit = matchTier1ByPoiName(p.name, tier1Schools, table);
    if (hit) hits.set(p.name, hit);
  }
  return hits;
}

/** 品牌单位的最小形状（与 apps/web brandGroups 的 BrandUnit 兼容） */
export interface BrandUnitLite {
  name: string;
  poi_names?: string[];
}

/** 品牌组的最小形状 */
export interface BrandGroupLite {
  brand: string;
  units: BrandUnitLite[];
}

/**
 * 按 POI 名全等匹配所属品牌组；未收录返回 undefined。
 * 匹配策略：**仅全等匹配** —— POI 归一化名 === 单位 name 或单位 poi_names 之一，
 * 不做前缀/包含匹配，避免「一中双桥学校」被「第一中学」前缀误配进一中品牌组。
 */
export function matchBrandByPoiName(
  poiName: string,
  brands: ReadonlyArray<BrandGroupLite>,
): string | undefined {
  const pn = normName(poiName);
  if (!pn) return undefined;
  for (const g of brands) {
    for (const u of g.units) {
      if (normName(u.name) === pn) return g.brand;
      for (const p of u.poi_names || []) {
        if (normName(p) === pn) return g.brand;
      }
    }
  }
  return undefined;
}
