/**
 * 身份与品牌域：学校身份注册表（resolveSite）+ 实体解析（resolvePoiName）+ 品牌关联（brandGroupOf）。
 */
import { matchBrandByPoiName, normName, looseNorm } from '../support.js';
import type { BrandGroupLite } from '../support.js';
import type { DataLoaders } from './loader.js';
import type { BrandGroup, Site } from './types.js';

export function createRegistryApi(loaders: DataLoaders) {
  const registrySites: Site[] = loaders.sites.schools.flatMap((s) => s.sites);
  const entities = loaders.entities.entities;
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

  /**
   * 任意校名（官方名单/口碑/POI 变体）→ 实体 POI 名（entities.name）。
   * 匹配顺序：norm 精确（name/aliases）→ loose（去学部/校区后缀）容错。
   * 用于跳转目标归一：只有能解析到实体（POI 存在）的名字才可跳详情页。
   * 官方名 → school_id 的外键已由 scripts/linkage/backfill_school_ids.py 回填各表，
   * 此处兜底解析未回填场景（如 CAMPUS_INFO 学校名 → 校区实体）。
   */
  function resolvePoiName(anyName: string): string | null {
    if (!anyName) return null;
    const n = normName(anyName);
    const ln = looseNorm(anyName);
    for (const e of entities) {
      if (normName(e.name) === n) return e.name;
      for (const a of e.aliases || []) {
        if (normName(a) === n) return e.name;
      }
    }
    for (const e of entities) {
      if (looseNorm(e.name) === ln) return e.name;
      for (const a of e.aliases || []) {
        if (looseNorm(a) === ln) return e.name;
      }
    }
    return null;
  }

  /** 任意校名 → school_id（实体表外键；解析不到返回 null）。scores.ts 的 resolveSchoolId 限高中，本函数不限学段 */
  function resolveSchoolIdOf(anyName: string): string | null {
    if (!anyName) return null;
    const n = normName(anyName);
    const ln = looseNorm(anyName);
    for (const e of entities) {
      if (normName(e.name) === n) return e.school_id;
      for (const a of e.aliases || []) {
        if (normName(a) === n) return e.school_id;
      }
    }
    for (const e of entities) {
      if (looseNorm(e.name) === ln) return e.school_id;
      for (const a of e.aliases || []) {
        if (looseNorm(a) === ln) return e.school_id;
      }
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

  return { resolveSite, resolvePoiName, resolveSchoolIdOf, brandGroupOf, brandGroups: loaders.brandGroups };
}
