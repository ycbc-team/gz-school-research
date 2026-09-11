/**
 * 学校判定域：完中判定（初高中同法人同校区）。
 */
import type { DataLoaders } from './loader.js';

/** 完中判定：去括号 base 名同时出现在 middle 与 high POI 列表 → 初高中一体 */
function baseName(n: string): string {
  return n.replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').replace(/(初中部|高中部|小学部)$/, '').trim();
}

export function createSchoolsApi(loaders: DataLoaders) {
  const middleBases = new Set(loaders.middleSchools.schools.map((s) => baseName(s.name)));
  const highBases = new Set(loaders.highSchools.schools.map((s) => baseName(s.name)));
  /** 判断某 POI 名是否为完全中学（初高中同法人同校区） */
  function isComprehensive(name: string): boolean {
    const b = baseName(name);
    return middleBases.has(b) && highBases.has(b);
  }
  return { isComprehensive };
}
