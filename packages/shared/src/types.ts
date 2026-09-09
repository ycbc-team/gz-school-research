/**
 * 共享数据模型 —— 与 data/*.json 一一对应（JSON 为唯一数据真源）。
 * 任何字段变更必须同步更新 data/ 下对应 JSON 与 scripts/ 生成器。
 */

/** 学校点位（小学/初中/高中通用；high 额外有 school/supplement） */
export interface SchoolPoi {
  name: string;
  lng: number;
  lat: number;
  adcode: string;
  /** backfill 来源标记 */
  src?: string;
  /** backfill 匹配到的招生学校 */
  matched_to?: string;
  match_score?: number;
  /** high：规范校名（清洗后） */
  school?: string;
  /** high：levels 清单补点 */
  supplement?: boolean;
}

export interface DistrictBoundary {
  name: string;
  adcode: string;
  boundary: number[][][];
}

/** data/{primary,middle,high}/schools-gz.json */
export interface SchoolsSnapshot {
  updated: string;
  source: string;
  note?: string;
  districts: DistrictBoundary[];
  schools: SchoolPoi[];
}

/** 支撑度结论（民间口径，非官方评价） */
export type Verdict = '有支撑' | '部分支撑' | '不支撑';

export interface RumorSource {
  source: string;
  url: string;
  label: string;
}

export interface Tier1School {
  name: string;
  /** 所在区（由 sync_tier1_aliases.py 从产物回填，真源字段） */
  district?: string;
  rumor_tier: string;
  rumor_sources: RumorSource[];
  rumor_notes?: string;
  /** 小学：小升初出口信号 */
  xiaoshengchu?: {
    group: string;
    feed_junior_highs: string[];
    direct_feed?: string | null;
    source_url?: string;
    source_note?: string;
  };
  /** 初中：中考成绩信号（网传口径，非官方） */
  zhongkao?: {
    year: number;
    scope: string;
    data: string;
    official: boolean;
    source_url: string;
    note?: string;
  };
  /** 初中：示范性高中称号 */
  demonstration_high?: {
    level: string;
    year: number | null;
    source_url: string;
  } | null;
  /** 教育集团身份 */
  education_group?: {
    name: string;
    role: string;
    source_url: string;
  };
  /** 小学：2026 计划班数 */
  plan_classes_2026?: number | null;
  /** 小学：学位预警 */
  degree_warning?: string | null;
  /** 小学：省一级历史称号 */
  provincial_level_title?: { year: number; note: string } | null;
  /** 初中：建校年份 */
  founded?: { year: number; note?: string };
  /** 初中：名额分配（指标到校）记录 */
  quota_allocation?: { year: number; data: string; source_url: string };
  conclusion: Verdict;
  conclusion_basis?: string;
  data_gaps?: string[];
  entity_relation?: string | null;
  tier1_eligible?: boolean;
  legal_entity?: {
    name: string;
    credit_code: string | null;
    type: string;
  } | null;
  exclude_reason?: string | null;
  evidence?: string[];
  opened_year?: number | null;
  /** 点位匹配别名（由 sync_tier1_aliases.py 从产物回填，真源字段） */
  aliases?: string[];
  /** 手工坐标（无 POI 的学校补点） */
  coords?: { lng: number; lat: number };
  coord_addr?: string;
  coord_source?: string;
}

export interface Tier1District {
  xiaoshengchu_mechanism: string;
  group_table_note: string;
  schools: Tier1School[];
}

/** data/{primary,middle}/tier1_schools_all.json */
export interface Tier1Snapshot {
  title: string;
  verified_date: string;
  scope: string;
  methodology: {
    rumor_sources: string;
    verification_layers: string[];
    policy_note: string;
  };
  summary: {
    total_schools: number;
    by_district: Record<string, number>;
    by_conclusion: Partial<Record<Verdict, number>>;
  };
  districts: Record<string, Tier1District>;
  source_urls: string[];
}

/** 高中分类（levels.json 口径） */
export type HighSchoolCategory = '省市属示范' | '区属示范' | '普通' | string;

export interface HighLevelSchool {
  name: string;
  district: string;
  category: HighSchoolCategory;
  affiliation: string;
  demo?: string;
  /** 校区名（字符串，与旧版产物一致） */
  campuses: string[];
  aliases: string[];
  indicators: Record<string, string | number | null>;
}

/** data/high/levels.json */
export interface HighLevelsSnapshot {
  updated: string;
  title: string;
  note: string;
  sources_base?: string[];
  schools: HighLevelSchool[];
}

export interface EnrollmentRecord {
  school: string;
  district: string;
  nature: string;
  plan_classes?: number | null;
  zone?: string;
  note?: string;
  phone?: string;
  source: string;
  school_id?: string;
  lng?: number;
  lat?: number;
}

export interface EnrollmentAmbiguous {
  school: string;
  poi: string;
  compete_with: string;
}

/** data/primary/enrollments/2026-*.json */
export interface EnrollmentSnapshot {
  year: number;
  district: string;
  source: string;
  source_url: string;
  records: EnrollmentRecord[];
  unmatched: string[];
  ambiguous: EnrollmentAmbiguous[];
  poi_leftover: string[];
  map_fail: string[];
}

/** 学段标识 */
export type SchoolStage = 'primary' | 'middle' | 'high';
