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

/** 不分组 / 按主管隶属 / 按点位所在区。 */
export type HighRankingGroupBy = 'none' | 'category' | 'district';
/** 录取线排序口径。average 会聚合当前及后续接入的所有年份分数。 */
export type HighRankingSortBy = 'score2025' | 'score2026' | 'average';
/** 高中明细筛选项：四类互斥招生学校类型，便于 UI 多选。 */
export type HighRankingFilterKey = 'province-municipal-demo' | 'normal-public' | 'private' | `district-demo:${string}`;

export interface HighRankingBuildOptions {
  groupBy: HighRankingGroupBy;
  /** 空数组代表不显示任何区；未传代表七区全选。 */
  districtAdcodes?: readonly string[];
  /** 筛选学校类型；未传代表不限制。 */
  filters?: readonly HighRankingFilterKey[];
  sortBy?: HighRankingSortBy;
}

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
  /** 用于列表的简称；全量去重后，存在歧义时保留原校名。 */
  displayName: string;
  schoolName: string;
  /** 点位 adcode，仅供筛选状态机使用。 */
  adcode: string;
  /** 点位所在行政区 */
  district: string;
  /** 招生政策标签：仅示范高中展示省属 / 市属 / XX区属；普通高中不展示行政隶属。 */
  affiliation: string | null;
  minban: boolean;
  /** 省市属示范 / 区属示范 / 普通高中；由 levels 分类直接决定分组 */
  category: string;
  demo: string | null;
  score2025: HighRankingScore[];
  score2026: HighRankingScore[];
  /** 2025 年第三批户籍生分数。 */
  sortScore2025: number | null;
  /** 2026 年第三批户籍生分数；无数据为 null，置于排序末尾 */
  sortScore2026: number | null;
  /** 已接入年份的第三批户籍生分数平均值。 */
  sortScoreAverage: number | null;
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

/** 未匹配 levels 分类的点位按普通高中归组，避免产生孤立的「未标注」模块。 */
function categoryGroupKey(category: string): string {
  return category === '未标注' ? '普通高中' : category;
}

/** 一行严格对应一个校区实体；不得回退或聚合同校其它校区的录取线。 */
function scoresForPoi(poi: SchoolPoi, yearScores: Record<string, HighScoreRecord[]>): HighRankingScore[] {
  return (poi.school_id ? (yearScores[poi.school_id] || []) : [])
    .map(formatHighRankingScore)
    .filter((score) => score.value != null);
}

/** 构建校区行；每组内按 2026 第三批户籍生分数降序，无分数置后。 */
export function buildHighRankingRows(loaders: Pick<DataLoaders, 'highSchools' | 'highLevels' | 'highScores2025' | 'highScores2026' | 'entities'>): HighRankingRow[] {
  // 快照可能含七区外补点；本页契约是「七区」，因此必须按点位 adcode 截断。
  const allPois = loaders.highSchools.schools;
  const minbanIds = new Set(loaders.entities.entities.filter((entity) => entity.stage === 'high' && entity.nature === '民办').map((entity) => entity.school_id));
  const rows = allPois.filter((poi) => poi.adcode in ADCODE_TO_DISTRICT).map((poi) => {
    const level = levelForPoi(poi, loaders.highLevels.schools);
    const schoolId = poi.school_id || null;
    const score2025 = scoresForPoi(poi, loaders.highScores2025.by_school_id);
    const score2026 = scoresForPoi(poi, loaders.highScores2026.by_school_id);
    const values2025 = score2025.map((score) => score.value).filter((v): v is number => v != null);
    const values2026 = score2026.map((score) => score.value).filter((v): v is number => v != null);
    const values = [...values2025, ...values2026];
    return {
      schoolId,
      name: poi.name,
      displayName: poi.name,
      schoolName: poi.school || level?.name || poi.name,
      adcode: poi.adcode,
      district: ADCODE_TO_DISTRICT[poi.adcode] || level?.district || '其他',
      affiliation: level?.category === '省市属示范' || level?.category === '区属示范'
        ? level.affiliation || null
        : null,
      minban: schoolId != null && minbanIds.has(schoolId),
      category: level?.category || '未标注',
      demo: level?.demo || null,
      score2025,
      score2026,
      sortScore2025: values2025.length ? Math.max(...values2025) : null,
      sortScore2026: values2026.length ? Math.max(...values2026) : null,
      sortScoreAverage: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null,
    };
  });
  // 先按现有规则尝试缩短；若任意两个校区缩写相同，则该缩写不安全，相关校名一律保留全称。
  const candidates = new Map<string, string[]>();
  for (const row of rows) {
    const short = highRankingShortName(row.name);
    candidates.set(short, [...(candidates.get(short) || []), row.name]);
  }
  const ambiguous = new Set([...candidates].filter(([, names]) => new Set(names).size > 1).map(([short]) => short));
  return rows.map((row) => ({ ...row, displayName: ambiguous.has(highRankingShortName(row.name)) ? row.name : highRankingShortName(row.name) }));
}

function highRankingShortName(name: string): string {
  const trimmed = name.trim();
  if (trimmed.startsWith('广州市')) return trimmed.slice(3);
  if (trimmed.startsWith('广东')) return trimmed.slice(2);
  if (trimmed.startsWith('广州')) {
    const rest = trimmed.slice(2);
    if (rest.length >= 3 && !rest.startsWith('大学')) return rest;
  }
  return trimmed;
}

export function buildHighRankingGroups(
  loaders: Pick<DataLoaders, 'highSchools' | 'highLevels' | 'highScores2025' | 'highScores2026' | 'entities'>,
  input: HighRankingGroupBy | HighRankingBuildOptions = 'category',
): HighRankingGroup[] {
  const options: HighRankingBuildOptions = typeof input === 'string' ? { groupBy: input } : input;
  const { groupBy, sortBy = 'score2026' } = options;
  const districts = options.districtAdcodes ? new Set(options.districtAdcodes) : null;
  const filters = options.filters ? new Set(options.filters) : null;
  const groups = new Map<string, HighRankingRow[]>();
  for (const row of buildHighRankingRows(loaders)) {
    if (districts && !districts.has(row.adcode)) continue;
    if (filters && ![...filters].some((filter) => matchesFilter(row, filter))) continue;
    const key = groupBy === 'none' ? 'all' : groupBy === 'district' ? row.district : categoryGroupKey(row.category);
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
    if (groupBy === 'none') return 0;
    return categoryOrder(a) - categoryOrder(b) || a.localeCompare(b, 'zh');
  });
  const scoreFor = (row: HighRankingRow) => sortBy === 'score2025'
    ? row.sortScore2025
    : sortBy === 'average' ? row.sortScoreAverage : row.sortScore2026;
  return keys.map((key) => ({
    key,
    title: groupBy === 'none' ? '全部高中' : key,
    items: groups.get(key)!.slice().sort((a, b) => {
      const av = scoreFor(a); const bv = scoreFor(b);
      if (av == null && bv == null) return a.name.localeCompare(b.name, 'zh');
      if (av == null) return 1;
      if (bv == null) return -1;
      return bv - av || a.name.localeCompare(b.name, 'zh');
    }),
  }));
}

function matchesFilter(row: HighRankingRow, filter: HighRankingFilterKey): boolean {
  if (filter === 'province-municipal-demo') return row.category === '省市属示范' && (row.affiliation === '省属' || row.affiliation === '市属');
  if (filter === 'normal-public') return row.category === '普通高中' && !row.minban;
  if (filter === 'private') return row.minban;
  return row.category === '区属示范' && row.affiliation === filter.slice('district-demo:'.length);
}
