/**
 * 学校筛选与统计聚合 —— 纯函数，双端共用。
 */
import type { SchoolPoi } from './types.js';
import { ADCODE_TO_DISTRICT } from './const.js';

export interface SchoolSummary {
  total: number;
  byDistrict: Array<{ name: string; count: number }>;
}

/** 汇总点位总数与按区分布（区名按 adcode 映射，未知区归入"其他"） */
export function summarizeSchools(
  schools: ReadonlyArray<SchoolPoi>,
): SchoolSummary {
  const counts: Record<string, number> = {};
  for (const s of schools) {
    const name = ADCODE_TO_DISTRICT[s.adcode] ?? '其他';
    counts[name] = (counts[name] ?? 0) + 1;
  }
  const byDistrict = Object.entries(counts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
  return { total: schools.length, byDistrict };
}

export interface SchoolFilter {
  /** 空数组/缺省 = 全部区 */
  adcodes?: string[];
  /** 关键字模糊匹配校名（含匹配） */
  keyword?: string;
}

/** 按区 + 关键字筛选点位 */
export function filterSchools(
  schools: ReadonlyArray<SchoolPoi>,
  filter: SchoolFilter = {},
): SchoolPoi[] {
  const adcodes = new Set(filter.adcodes ?? []);
  const kw = (filter.keyword ?? '').trim();
  return schools.filter((s) => {
    if (adcodes.size > 0 && !adcodes.has(s.adcode)) return false;
    if (kw && !s.name.includes(kw)) return false;
    return true;
  });
}

/** 招生记录按学校名去重（同名多校区取第一条），供列表展示 */
export function uniqueByName<T extends { name: string }>(items: ReadonlyArray<T>): T[] {
  const seen = new Set<string>();
  const out: T[] = [];
  for (const it of items) {
    if (seen.has(it.name)) continue;
    seen.add(it.name);
    out.push(it);
  }
  return out;
}
