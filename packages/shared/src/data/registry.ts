/**
 * 身份与品牌域：实体解析（resolvePoiName）+ 品牌关联（groupOfSchool）。
 * 品牌关联 = 查 educationGroups 内的 school_id，初始化后纯 id 匹配。
 */
import { normName, looseNorm } from '../support.js';
import type { DataLoaders } from './loader.js';
import type { BrandGroup, EducationGroup } from './types.js';

export function createRegistryApi(loaders: DataLoaders) {
  const entities = loaders.entities.entities;

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

  /** educationGroups 是唯一集团运行时产物；按其顺序保留首个归属。 */
  const schoolGroupMap: Record<string, { brand: string; source: 'education' | 'brand' }> = {};
  for (const group of loaders.educationGroups?.groups || []) {
    for (const member of group.members || []) {
      if (member.school_id && !schoolGroupMap[member.school_id]) {
        schoolGroupMap[member.school_id] = { brand: group.brand, source: 'education' };
      }
    }
  }
  // 品牌源 units（school_ids 数组）同样入索引：省市属品牌（华附/广雅/铁一等）走 brand_groups，
  // 漏收会丢品牌卡（如黄埔铁英 = c80ac6ac + adb9c303 两个实体）。
  for (const bg of loaders.brandGroups?.brands || []) {
    for (const unit of bg.units || []) {
      for (const id of unit.school_ids || []) {
        if (!schoolGroupMap[id]) schoolGroupMap[id] = { brand: bg.brand, source: 'brand' };
      }
    }
  }
  const nonGroupMultiCampuses = loaders.nonGroupMultiCampuses;
  const multiCampusFamilyOfSchool: Record<string, string> = {};
  for (const [familyKey, schoolIds] of Object.entries(nonGroupMultiCampuses || {})) {
    for (const schoolId of schoolIds) multiCampusFamilyOfSchool[schoolId] = familyKey;
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
   * - 命中公共映射后按 source 分支展开（education / brand），未命中返回 null（未关联任何集团）
   * - 运行时不做任何按名匹配：品牌归属的唯一权威是 schoolGroups 产物
   */
  function groupOfSchool(name: string, schoolId?: string | null): {
    source: 'brand' | 'education';
    brand: string;
    note?: string;
    core: string[];
    members: Array<{ name: string; role: string; school_ids?: string[]; poi_names?: string[]; poi_name?: string; school_id?: string; campuses?: Array<{ poi_name: string; school_id: string }>; legal?: 'same' | 'independent'; relation_type?: 'same' | 'entrusted' | 'cooperation' | 'brand' }>;
    source_urls: string[];
  } | null {
    if (!name && !schoolId) return null;

    // 0. 没传 school_id 时，用校名去 entities 表反查 school_id（别名桥接；仍是 id 路径）
    if (!schoolId && name) {
      schoolId = resolveSchoolIdOf(name);
    }
    if (!schoolId) return null;

    // 1. 查公共映射（唯一权威）
    const entry = schoolGroupMap[schoolId];
    if (!entry) return null;

    // 2. education 分支：从教育集团原文展开 core/members
    if (entry.source === 'education') {
      const g = (loaders.educationGroups?.groups || []).find((x) => x.brand === entry.brand);
      if (!g) return null;
      return {
        source: 'education',
        brand: g.brand,
        note: g.note || inferSourceNote(g.source_urls || []),
        core: [],
        members: g.members.map((m) => ({
          name: m.school_id ? entities.find((entity) => entity.school_id === m.school_id)?.name || m.name : m.name,
          role: m.role || '成员校',
          school_id: m.school_id,
          legal: m.relation_type === 'same' ? 'same' : m.relation_type ? 'independent' : undefined,
          relation_type: m.relation_type,
        })),
        source_urls: g.source_urls || [],
      };
    }

    // 3. brand 分支：从品牌原文展开（units 外键由数据层写回保证）
    const bg = (loaders.brandGroups.brands || []).find((x) => x.brand === entry.brand);
    if (!bg) return null;
    return brandGroupResult(bg);
  }

  /** 教育集团缺省时可用的同法人多校区索引；同样只接受 school_id 外键。 */
  function multiCampusOfSchool(name: string, schoolId?: string | null) {
    const id = schoolId || resolveSchoolIdOf(name);
    if (!id || schoolGroupMap[id]) return null;
    const familyKey = multiCampusFamilyOfSchool[id];
    if (!familyKey) return null;
    return { family_key: familyKey, school_ids: nonGroupMultiCampuses?.[familyKey] || [] };
  }

  return { resolvePoiName, resolveSchoolIdOf, groupOfSchool, multiCampusOfSchool, brandGroups: loaders.brandGroups };
}
