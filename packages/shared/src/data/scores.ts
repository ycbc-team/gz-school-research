/**
 * 高中统招录取分数查询（data/high/scores_{year}.json 官方真源，按 school_id 引用实体表）。
 *
 * 查询入口：
 * - scoresBySchoolId(school_id)        —— 单校区实体 → 两年记录（地图信息卡：POI 点位自带 school_id）
 * - scoresOfSchool(schoolName)         —— levels 学校（多校区）→ 两年按校区聚合（高中详情页）
 *
 * 口径（与官方录取表一致）：
 * - 公办：户籍生最低分（huji）为主；第三批另有非户籍生/外区生
 * - 民办/中外合作：最低分数（min_score）；公费班为独立条目（gongfei）
 * - 外语艺术类（第一批）：末位考生分数（huji_last），无普通批次时兜底展示
 * - 民办公费班与自费分属不同批次（公费班=第三批，自费=第四批），均展示
 */
import type { DataLoaders } from './loader.js';
import type { HighScoreRecord, HighScores } from './types.js';

export interface YearScore {
  year: number;
  records: HighScoreRecord[];
}

export interface SchoolScore {
  /** 校区官方招生单位原文名（如「华南师范大学附属中学（石牌校区）」） */
  officialName: string;
  /** 校区实体 school_id */
  schoolId: string;
  /** 2025/2026 两年记录 */
  years: YearScore[];
}

export function createScoresApi(loaders: DataLoaders) {
  const byYear: Array<{ year: number; data: HighScores }> = [
    { year: 2025, data: loaders.highScores2025 },
    { year: 2026, data: loaders.highScores2026 },
  ];

  /** 单校区实体（school_id）两年录取记录 */
  function scoresBySchoolId(schoolId: string | null | undefined): YearScore[] {
    if (!schoolId) return [];
    return byYear
      .map(({ year, data }) => ({ year, records: data.by_school_id[schoolId] || [] }))
      .filter((y) => y.records.length > 0);
  }

  /** levels 学校（多校区）→ 各校区两年分数；campuses 未命中实体的校区不返回 */
  function scoresOfSchool(schoolName: string, campuses: string[]): SchoolScore[] {
    const out: SchoolScore[] = [];
    for (const campus of campuses.length ? campuses : [schoolName]) {
      const sid = resolveSchoolId(campus);
      if (!sid) continue;
      const years = scoresBySchoolId(sid);
      if (!years.length) continue;
      const first = years[0]?.records[0];
      if (!first) continue;
      out.push({
        officialName: first.official_name,
        schoolId: sid,
        years,
      });
    }
    return out;
  }

  /** POI/校区名（norm 全等）→ school_id（实体表 name/aliases，与 build_entities.mjs 同规则） */
  function resolveSchoolId(name: string): string | null {
    const n = normName(name);
    for (const e of loaders.entities.entities) {
      if (e.stage !== 'high') continue;
      if (normName(e.name) === n) return e.school_id;
      for (const a of e.aliases || []) {
        if (normName(a) === n) return e.school_id;
      }
    }
    return null;
  }

  return { scoresBySchoolId, scoresOfSchool, resolveSchoolId };
}

/** 与 scripts/registry/build_entities.mjs 一致的 norm（全角括号→半角→去「广州市」前缀→去括号→去空白） */
export function normName(s: string): string {
  return (s || '')
    .replace(/（/g, '(')
    .replace(/）/g, ')')
    .replace(/^广州市/, '')
    .replace(/[()]/g, '')
    .replace(/\s+/g, '');
}
