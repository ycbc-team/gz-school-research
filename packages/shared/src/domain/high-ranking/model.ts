/**
 * 七区高中明细 ViewModel。
 *
 * 这个模型只做数据归并、展示文本和排序值，不含 Vue/微信小程序 API；两个端可以直接复用。
 * 一行对应一个高中校区点位，因此「按位置所在行政区」严格取 POI 的 adcode，而非学校的
 * 主管区。录取线保留官方记录的全部口径，排序则使用该校区 2026 年记录中的最高主分数。
 */
import { ADCODE_TO_DISTRICT, GZ_DISTRICTS } from '../../const.js';
import type { DataLoaders } from '../../data/loader.js';
import type { HighScoreRecord } from '../../data/types.js';
import type { HighLevelSchool, SchoolPoi } from '../../types.js';

export type HighRankingGroupBy = 'affiliation' | 'district';

export interface HighRankingScore {
  /** 官网招生单位原文 */
  name: string;
  /** 用于列表显示的完整官方口径 */
  text: string;
  /** 该条记录用于排序的主分数 */
  value: number | null;
}

export interface HighRankingRow {
  schoolId: string | null;
  name: string;
  schoolName: string;
  /** 点位所在行政区 */
  district: string;
  affiliation: string;
  category: string;
  demo: string | null;
  score2025: HighRankingScore[];
  score2026: HighRankingScore[];
  /** 2026 年全部官方录取记录中的最高主分数；无数据为 null，置于排序末尾 */
  sortScore2026: number | null;
}

export interface HighRankingGroup {
  key: string;
  title: string;
  items: HighRankingRow[];
}

function norm(s: string): string {
  return (s || '')
    .replace(/（/g, '(').replace(/）/g, ')')
    .replace(/^广州市/, '').replace(/[()\s]/g, '');
}

function levelForPoi(poi: SchoolPoi, levels: HighLevelSchool[]): HighLevelSchool | null {
  const candidates = [poi.name, poi.school || ''].filter(Boolean).map(norm);
  return levels.find((level) => {
    const names = [level.name, ...level.aliases, ...level.campuses].map(norm);
    return candidates.some((candidate) => names.includes(candidate));
  }) || null;
}

/** 公办优先户籍生；民办/中外合作使用最低分；外语艺术类使用末位户籍生。 */
export function highRankingScoreValue(record: HighScoreRecord): number | null {
  if (record.kind === 'public') return record.huji ?? record.feihuji ?? record.waiqu ?? null;
  if (record.kind === 'lang_art') return record.huji_last ?? record.feihuji_last ?? null;
  return record.min_score ?? null;
}

export function formatHighRankingScore(record: HighScoreRecord): HighRankingScore {
  const value = highRankingScoreValue(record);
  const batch = `第${record.batch}批`;
  let text: string;
  if (record.kind === 'public') {
    const fields = [
      record.huji != null ? `户籍 ${record.huji}` : null,
      record.feihuji != null ? `非户籍 ${record.feihuji}` : null,
      record.waiqu != null ? `外区 ${record.waiqu}` : null,
    ].filter(Boolean);
    text = `${batch} · ${fields.join(' / ') || '—'}`;
  } else if (record.kind === 'lang_art') {
    const fields = [
      record.huji_last != null ? `户籍末位 ${record.huji_last}` : null,
      record.feihuji_last != null ? `非户籍末位 ${record.feihuji_last}` : null,
    ].filter(Boolean);
    text = `${batch} · 外语艺术 · ${fields.join(' / ') || '—'}`;
  } else {
    text = `${batch}${record.gongfei ? ' · 公费班' : ''} · 最低 ${record.min_score ?? '—'}`;
  }
  return { name: record.official_name, text, value };
}

function affiliationOrder(value: string): number {
  if (value === '省属') return 0;
  if (value === '市属') return 1;
  if (value.endsWith('区属')) return 2 + GZ_DISTRICTS.findIndex((d) => value === `${d.name}属`);
  if (value === '民办') return 20;
  return 99;
}

/** 构建校区行；每组内按 2026 主分数降序，无分数置后。 */
export function buildHighRankingRows(loaders: Pick<DataLoaders, 'highSchools' | 'highLevels' | 'highScores2025' | 'highScores2026'>): HighRankingRow[] {
  // 快照可能含七区外补点；本页契约是「七区」，因此必须按点位 adcode 截断。
  return loaders.highSchools.schools.filter((poi) => poi.adcode in ADCODE_TO_DISTRICT).map((poi) => {
    const level = levelForPoi(poi, loaders.highLevels.schools);
    const schoolId = poi.school_id || null;
    const score2025 = schoolId ? (loaders.highScores2025.by_school_id[schoolId] || []).map(formatHighRankingScore) : [];
    const score2026 = schoolId ? (loaders.highScores2026.by_school_id[schoolId] || []).map(formatHighRankingScore) : [];
    const values = score2026.map((score) => score.value).filter((v): v is number => v != null);
    return {
      schoolId,
      name: poi.name,
      schoolName: poi.school || level?.name || poi.name,
      district: ADCODE_TO_DISTRICT[poi.adcode] || level?.district || '其他',
      affiliation: level?.affiliation || '未标注',
      category: level?.category || '未标注',
      demo: level?.demo || null,
      score2025,
      score2026,
      sortScore2026: values.length ? Math.max(...values) : null,
    };
  });
}

export function buildHighRankingGroups(
  loaders: Pick<DataLoaders, 'highSchools' | 'highLevels' | 'highScores2025' | 'highScores2026'>,
  groupBy: HighRankingGroupBy,
): HighRankingGroup[] {
  const groups = new Map<string, HighRankingRow[]>();
  for (const row of buildHighRankingRows(loaders)) {
    const key = groupBy === 'district' ? row.district : row.affiliation;
    const list = groups.get(key) || [];
    list.push(row);
    groups.set(key, list);
  }
  const keys = [...groups.keys()].sort((a, b) => {
    if (groupBy === 'district') {
      const ia = GZ_DISTRICTS.findIndex((d) => d.name === a);
      const ib = GZ_DISTRICTS.findIndex((d) => d.name === b);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    }
    return affiliationOrder(a) - affiliationOrder(b) || a.localeCompare(b, 'zh');
  });
  return keys.map((key) => ({
    key,
    title: key,
    items: groups.get(key)!.slice().sort((a, b) => {
      if (a.sortScore2026 == null && b.sortScore2026 == null) return a.name.localeCompare(b.name, 'zh');
      if (a.sortScore2026 == null) return 1;
      if (b.sortScore2026 == null) return -1;
      return b.sortScore2026 - a.sortScore2026 || a.name.localeCompare(b.name, 'zh');
    }),
  }));
}
