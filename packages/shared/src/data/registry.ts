/**
 * 身份与品牌域：学校身份注册表（resolveSite）+ 品牌关联（brandGroupOf）。
 */
import { matchBrandByPoiName } from '../support.js';
import type { BrandGroupLite } from '../support.js';
import type { DataLoaders } from './loader.js';
import type { BrandGroup, Site } from './types.js';

export function createRegistryApi(loaders: DataLoaders) {
  const registrySites: Site[] = loaders.sites.schools.flatMap((s) => s.sites);
  /** 任意来源名 → site（poi_name / gov_names / aliases 全量精确匹配） */
  function resolveSite(anyName: string): Site | null {
    if (!anyName) return null;
    for (const s of registrySites) {
      if (s.poi_name === anyName) return s;
      if ((s.gov_names || []).includes(anyName)) return s;
      if ((s.aliases || []).includes(anyName)) return s;
    }
    return null;
  }

  /** 按任意校名（详情页当前学校名）匹配所属品牌组；未收录返回 null（仅全等匹配，POI 变体见 unit.poi_names） */
  function brandGroupOf(name: string): BrandGroup | null {
    if (!name) return null;
    const brand = matchBrandByPoiName(name, loaders.brandGroups.brands as unknown as BrandGroupLite[]);
    if (!brand) return null;
    return loaders.brandGroups.brands.find((g) => g.brand === brand) || null;
  }

  return { resolveSite, brandGroupOf, brandGroups: loaders.brandGroups };
}
