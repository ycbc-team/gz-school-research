/**
 * 身份与品牌域：学校身份注册表（resolveSite）+ 实体解析（resolvePoiName）+ 品牌关联（brandGroupOf）。
 */
import { matchBrandByPoiName, normName, looseNorm } from '../support.js';
import type { BrandGroupLite } from '../support.js';
import type { DataLoaders } from './loader.js';
import type { BrandGroup, Site, EducationGroup } from './types.js';

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

  /** 根据 source_urls 域名自动推断来源说明文案 */
  function inferSourceNote(urls: string[]): string {
    if (!urls.length) return '区教育局官方教育集团化办学文件口径';
    const u = urls[0]!;
    if (u.includes('yuexiu.gov.cn') && u.includes('xqhjthbx')) return '越秀区教育局"669"学区化集团化办学一览表';
    if (u.includes('haizhu.gov.cn')) return '海珠区教育局集团化办学通知';
    if (u.includes('lw.gov.cn') && u.includes('gzlwjy')) return '荔湾区教育局公开文件';
    if (u.includes('hp.gov.cn')) return '黄埔区教育局官方发布';
    if (u.includes('thnet.gov.cn')) return '天河区政府官网（含成员校名单）';
    if (u.includes('panyu.gov.cn')) return '番禺区教育局官方发布';
    if (u.includes('baiyun')) return '白云区教育局官方发布';
    return '区教育局官方教育集团化办学文件口径';
  }

  /**
   * school_id → 所属集团索引（离线构建，运行时 O(1) 精确查）。
   * 覆盖 education_groups.json 里 core_poi.school_id + members[].school_id。
   * brandGroups 的 unit 无 school_id（按 POI 名匹配），不在此索引。
   */
  const schoolIdToGroup = new Map<string, EducationGroup>();
  {
    const eg = loaders.educationGroups;
    if (eg?.groups?.length) {
      for (const g of eg.groups) {
        for (const p of g.core_poi || []) {
          if (p.school_id) schoolIdToGroup.set(p.school_id, g);
        }
        for (const m of g.members || []) {
          if (m.school_id) schoolIdToGroup.set(m.school_id, g);
          // 多校区索引：campuses 里所有校区 school_id 都能查到所属集团
          for (const c of m.campuses || []) {
            if (c.school_id) schoolIdToGroup.set(c.school_id, g);
          }
        }
      }
    }
  }

  /**
   * school_id → 品牌组索引（brandGroups 单位显式 school_ids 外键，离线构建 O(1) 查）。
   * 品牌关联以实体外键为主（与 education 分支同机制），名字匹配仅作无外键时的兜底；
   * 同一 school_id 同时命中 education 与 brand 时，education 优先（groupOfSchool 先查 education 索引）。
   */
  const brandSchoolIdToGroup = new Map<string, BrandGroup>();
  {
    for (const g of loaders.brandGroups.brands || []) {
      for (const u of g.units || []) {
        for (const sid of u.school_ids || []) {
          if (!brandSchoolIdToGroup.has(sid)) brandSchoolIdToGroup.set(sid, g);
        }
      }
    }
  }

  /** brand 来源的 groupOfSchool 结果结构（school_id 外键命中与按名匹配共用） */
  function brandGroupResult(bg: BrandGroup): {
    source: 'brand';
    brand: string;
    note?: string;
    core: string[];
    members: Array<{ name: string; role: string; school_ids?: string[]; poi_names?: string[]; legal?: 'same' | 'independent' }>;
    source_urls: string[];
  } {
    return {
      source: 'brand',
      brand: bg.brand,
      note: bg.brand_note,
      core: bg.units.filter((u) => u.legal === 'same').map((u) => u.name),
      members: bg.units.map((u) => ({
        name: u.name,
        role: u.role,
        legal: u.legal,
        school_ids: u.school_ids,
        poi_names: u.poi_names,
      })),
      source_urls: [],
    };
  }

  /**
   * 按 school_id（首选）或校名（经 entities 表反查 school_id）匹配所属教育集团。
   * - 没传 school_id 时，用校名在 entities 表反查 school_id（含别名桥接），查到了走同一条精确路径
   * - 其次 brandGroups（8 个重点品牌，带法人关系/口碑标注，按 POI 名匹配）
   * - 都未命中：返回 null（未关联任何集团，不当作正常分支）
   */
  function groupOfSchool(name: string, schoolId?: string | null): {
    source: 'brand' | 'education';
    brand: string;
    note?: string;
    core: string[];
    members: Array<{ name: string; stage?: string; role: string; school_ids?: string[]; poi_names?: string[]; poi_name?: string; school_id?: string; campuses?: Array<{ poi_name: string; school_id: string }>; legal?: 'same' | 'independent' }>;
    source_urls: string[];
  } | null {
    if (!name && !schoolId) return null;

    // 0. 没传 school_id 时，用校名去 entities 表反查 school_id（别名桥接）
    if (!schoolId && name) {
      schoolId = resolveSchoolIdOf(name);
    }

    // 1. school_id 精确查离线索引
    if (schoolId && schoolIdToGroup.has(schoolId)) {
      const g = schoolIdToGroup.get(schoolId)!;
      // 核心校：优先展开 core_poi 的多校区 POI，fallback 到 core 官方名
      const corePoiRows = (g.core_poi || []).map((p) => ({
        name: p.poi_name || p.name,
        role: '核心校',
        poi_name: p.poi_name,
        school_id: p.school_id,
      }));
      const coreRows = corePoiRows.length
        ? corePoiRows
        : g.core.map((c) => ({ name: c, role: '核心校' }));
      return {
        source: 'education',
        brand: g.brand,
        note: g.note || inferSourceNote(g.source_urls || []),
        core: g.core,
        members: [
          ...coreRows,
          ...g.members.map((m) => ({
            name: m.name,
            stage: m.stage,
            role: '成员校',
            poi_names: m.campuses?.length ? m.campuses.map((c: { poi_name: string }) => c.poi_name) : m.poi_name ? [m.poi_name] : undefined,
            poi_name: m.poi_name,
            school_id: m.school_id,
            campuses: m.campuses,
          })),
        ],
        source_urls: g.source_urls || [],
      };
    }

    // 2. 8 个重点品牌：优先 school_id 外键精确查（与 education 同机制），未命中再按 POI 名匹配
    const bg = (schoolId && brandSchoolIdToGroup.get(schoolId)) || brandGroupOf(name || '');
    if (bg) return brandGroupResult(bg);

    // 3. 未关联任何集团：异常/未收录，返回 null
    return null;
  }

  return { resolveSite, resolvePoiName, resolveSchoolIdOf, brandGroupOf, groupOfSchool, brandGroups: loaders.brandGroups };
}
