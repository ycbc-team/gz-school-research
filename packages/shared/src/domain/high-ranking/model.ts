/**
 * 七区高中明细 ViewModel。
 *
 * 这个模型只做数据归并、展示文本和排序值，不含 Vue/微信小程序 API；两个端可以直接复用。
 * 一行对应一个高中校区点位，因此「按位置所在行政区」严格取 POI 的 adcode，而非学校的
 * 主管区。榜单录取线统一只取第三批公办户籍生分数；没有该口径即为空。
 */
import { ADCODE_TO_DISTRICT, GZ_DISTRICTS } from '../../const.js';
import type { DataLoaders } from '../../data/loader.js';
import type { HighScoreRecord } from '../../data/types.js';
import type { HighLevelSchool, SchoolPoi } from '../../types.js';

export type HighRankingGroupBy = 'category' | 'district';

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
  minban: boolean;
  /** 省市属示范 / 区属示范 / 普通高中；由 levels 分类直接决定分组 */
  category: string;
  demo: string | null;
  score2025: HighRankingScore[];
  score2026: HighRankingScore[];
  /** 2026 年第三批户籍生分数；无数据为 null，置于排序末尾 */
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

/** 高中明细唯一录取线口径：第三批公办户籍生。 */
export function highRankingScoreValue(record: HighScoreRecord): number | null {
  return record.batch === 3 && record.kind === 'public' ? record.huji ?? null : null;
}

export function formatHighRankingScore(record: HighScoreRecord): HighRankingScore {
  const value = highRankingScoreValue(record);
  return { name: record.official_name, text: value == null ? '—' : String(value), value };
}

function categoryOrder(value: string): number {
  if (value === '省市属示范') return 0;
  if (value === '区属示范') return 1;
  if (value === '普通高中') return 2;
  return 99;
}

function scoresForPoi(poi: SchoolPoi, yearScores: Record<string, HighScoreRecord[]>, allPois: SchoolPoi[]): HighRankingScore[] {
  const direct = poi.school_id ? (yearScores[poi.school_id] || []) : [];
  // 部分官方招生单位只挂在同校另一校区实体。例如广大附中官方分数挂黄华路校区，
  // 详情页按学校聚合可显示，大学城校区行则需回退到同一规范校名的录取记录。
  const records = direct.length ? direct : allPois
    .filter((other) => other.school === poi.school && other.school_id)
    .flatMap((other) => yearScores[other.school_id!] || []);
  return records
    .map(formatHighRankingScore)
    .filter((score) => score.value != null);
}

/** 构建校区行；每组内按 2026 第三批户籍生分数降序，无分数置后。 */
export function buildHighRankingRows(loaders: Pick<DataLoaders, 'highSchools' | 'highLevels' | 'highScores2025' | 'highScores2026' | 'entities'>): HighRankingRow[] {
  // 快照可能含七区外补点；本页契约是「七区」，因此必须按点位 adcode 截断。
  const allPois = loaders.highSchools.schools;
  const minbanIds = new Set(loaders.entities.entities.filter((entity) => entity.stage === 'high' && entity.nature === '民办').map((entity) => entity.school_id));
  return allPois.filter((poi) => poi.adcode in ADCODE_TO_DISTRICT).map((poi) => {
    const level = levelForPoi(poi, loaders.highLevels.schools);
    const schoolId = poi.school_id || null;
    const score2025 = scoresForPoi(poi, loaders.highScores2025.by_school_id, allPois);
    const score2026 = scoresForPoi(poi, loaders.highScores2026.by_school_id, allPois);
    const values = score2026.map((score) => score.value).filter((v): v is number => v != null);
    return {
      schoolId,
      name: poi.name,
      schoolName: poi.school || level?.name || poi.name,
      district: ADCODE_TO_DISTRICT[poi.adcode] || level?.district || '其他',
      minban: schoolId != null && minbanIds.has(schoolId),
      category: level?.category || '未标注',
      demo: level?.demo || null,
      score2025,
      score2026,
      sortScore2026: values.length ? Math.max(...values) : null,
    };
  });
}

export function buildHighRankingGroups(
  loaders: Pick<DataLoaders, 'highSchools' | 'highLevels' | 'highScores2025' | 'highScores2026' | 'entities'>,
  groupBy: HighRankingGroupBy,
): HighRankingGroup[] {
  const groups = new Map<string, HighRankingRow[]>();
  for (const row of buildHighRankingRows(loaders)) {
    const key = groupBy === 'district' ? row.district : row.category;
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
    return categoryOrder(a) - categoryOrder(b) || a.localeCompare(b, 'zh');
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
