/**
 * 学校名归一化与品牌归属匹配。
 * 匹配策略：仅全等匹配（归一化后 === 记录名/别名），不做前缀/包含/模糊匹配。
 */

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
 * 仅全等匹配（不模糊），不会误配；与 data/linkage/scripts/backfill_school_ids.py 的 loose 规则一致。
 */
export function looseNorm(s: string): string {
  return normName(s).replace(/(初中部|高中部|小学部|校区|分校|学校|部)$/, '');
}

/** 品牌单位的最小形状（与 apps/web brandGroups 的 BrandUnit 兼容） */
export interface BrandUnitLite {
  name: string;
  school_ids?: string[];
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
