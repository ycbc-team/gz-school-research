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
  /** 实体外键（= entities.json 的 school_id，POI 与实体 1:1） */
  school_id?: string;
  /** backfill 来源标记 */
  src?: string;
  /** backfill 匹配到的招生学校 */
  matched_to?: string;
  match_score?: number;
  /** high：规范校名（清洗后） */
  school?: string;
  /** high：levels 清单补点 */
  supplement?: boolean;
  /** 新校核对补录标记（如「新开办（2026）·待首届成绩」）；无成绩新校不进 tier1 名单但数据可见 */
  note?: string;
}

export interface DistrictBoundary {
  name: string;
  adcode: string;
  boundary: number[][][];
}

/** data/poi/dist/{primary,middle,high}_poi.json */
export interface SchoolsSnapshot {
  updated: string;
  source: string;
  note?: string;
  districts: DistrictBoundary[];
  schools: SchoolPoi[];
}

/** 证据条目（真源引用） */
export interface EvidenceItem {
  source: string;
  url: string;
  note?: string;
}

/** 历史称号（省/市一级等 2005 年停评的历史荣誉，仅作客观记录） */
export interface HistoricalTitle {
  level: string;
  year: number | null;
  note: string;
  source_url: string;
}

export interface Tier1School {
  name: string;
  /** 关联 POI 实体 id 列表（多校区 1:N；由 aliases 匹配 POI 回填；孤儿记录无此字段） */
  school_ids?: string[];
  /** 孤儿标记：aliases 未匹配到任何 POI（地图/详情不生效，仅数据保留） */
  orphan?: boolean;
  /** 所在区（孤儿记录保留自包含；匹配上的由 POI.adcode join，不存） */
  district?: string;
  /** 历史称号（省/市一级等停评荣誉，替代旧 provincial_level_title） */
  historical_titles: HistoricalTitle[];
  /** 小学：学位预警（对象化，替代旧 degree_warning 字符串） */
  degree_warning?: { status: string; year: number; source_url: string } | null;
  /** 小学：2026 计划班数（对象化，替代旧 plan_classes_2026 数值） */
  plan_classes?: { year: number; count: number; source_url: string } | null;
  /** 教育集团身份（含头部标记） */
  education_group?: {
    name: string;
    role: string;
    is_top_tier: boolean;
    group_level?: string;
    source_url: string;
  };
  /** 小学：对口直升初中 */
  direct_feed?: {
    middle_school: string;
    middle_school_id: string | null;
    is_reputable: boolean;
    source_url: string;
  };
  /** 初中：中考口碑喜报（网传口径，非官方；旧 zhongkao 改名 zhongkao_rumor） */
  zhongkao_rumor?: {
    year: number;
    scope: string;
    data: string;
    source_url: string;
    note?: string;
  };
  /** 初中：官方中考录取分数（户籍生，新增） */
  admission_scores?: Array<{
    year: number;
    huji: number;
    source_url: string | Array<{ batch?: number; title?: string; url: string }>;
  }>;
  /** 初中：自主招生/名额人数（新增） */
  autonomy_count?: { year: number; count: number; source_url: string } | null;
  /** 初中：示范性高中称号 */
  demonstration_high?: {
    level: string;
    year: number | null;
    source_url: string;
  } | null;
  /** 初中：建校年份 */
  founded?: { year: number; note?: string };
  /** 初中：名额分配（指标到校）记录 */
  quota_allocation?: { year: number; data: string; source_url: string };
  /** 数据缺口说明 */
  data_gaps: string[];
  /** 真源证据 */
  evidence: EvidenceItem[];
  entity_relation?: string | null;
  legal_entity?: {
    name: string;
    credit_code: string | null;
    type: string;
  } | null;
  opened_year?: number | null;
  /** 候选名变体（仅孤儿记录保留；匹配上的别名已收敛进 entities.json，本表不再冗余） */
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
    dimensions: string[];
    scoring: string;
    policy_note: string;
  };
  summary: {
    total_schools: number;
    by_district: Record<string, number>;
  };
  districts: Record<string, Tier1District>;
  source_urls: string[];
}

/** 派位/对口分组表（xiaoshengchu 顶层 groups，避免逐记录重复组名/source_url） */
export interface XiaoshengchuGroup {
  id: number;
  name: string;
  /** 组级来源（组内 85/88 一致；多区汇聚组含多个 url） */
  source_urls: string[];
  /** 组级数据缺口说明（记录级覆盖见 XiaoshengchuFactRecord.data_gaps） */
  data_gaps: string | null;
}

/** 真源事实记录（data/primary/xiaoshengchu_2026.json 的 records，school_id 引用实体） */
export interface XiaoshengchuFactRecord {
  school_id: string;
  group_id: number;
  feed_school_ids: string[];
  feed_unresolved: string[];
  direct_feed_school_id: string | null;
  source_note?: string;
  /** 仅当与组级 data_gaps 不同时存在（记录级覆盖） */
  data_gaps?: string | null;
}

/** 运行时展示形状（quota.ts shapeRecord 适配输出） */
export interface XiaoshengchuRecord {
  /** 学校名（与 POI 全称对齐） */
  name: string;
  /** 派位/对口分组描述（官方口径，由组表解析） */
  group: string | null;
  /** 对口/派位初中名单 */
  feed_junior_highs: string[];
  /** 对口直升本校初中（直升场景，与派位名单互斥为主） */
  direct_feed: string | null;
  source_url: string;
  source_note: string;
  /** 数据缺口说明（feed 为空时必填原因，如民办不参与公办派位） */
  data_gaps: string | null;
}

/** data/primary/xiaoshengchu_2026.json */
export interface XiaoshengchuSnapshot {
  year: number;
  note: string;
  groups: XiaoshengchuGroup[];
  records: XiaoshengchuFactRecord[];
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

/** data/high/level/src/levels.json */
export interface HighLevelsSnapshot {
  updated: string;
  title: string;
  note: string;
  sources_base?: string[];
  schools: HighLevelSchool[];
}

export interface EnrollmentRecord {
  /** 官方招生原文名（含区名/校区括号，作为匹配锚点与审计原文） */
  school: string;
  /** 真实体 id（= entities.json 主键，由 poi_name 匹配 POI 回填，1:1） */
  school_id: string;
  /** 匹配用 POI 名变体（norm 后与 POI name 全等；原字段名曾误作 school_id） */
  poi_name: string;
  plan_classes?: number | null;
  zone?: string;
  note?: string;
  phone?: string;
  source: string;
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

/** data/primary/enrollments/middle_enrollment_2026_*.json —— 初中视角招生计划 */
export type MiddleMechanism = 'single_zone' | 'group_paidui' | 'single_lottery';
export interface MiddleMechanismDef {
  label: string;
  can_lose: boolean;
  lose_text: string | null;
}
export interface MiddleEnrollmentRecord {
  school: string;
  /** 单一归属 school_id；合并招生（多校区共用一套计划）时为 null，改用 school_ids 列出全部校区 */
  school_id: string | null;
  /** 多校区共用同一招生计划时列出全部校区 id（如番禺铁英学校 28 班合并招生：东/西两校区） */
  school_ids?: string[];
  plan_classes: number | null;
  scope: string | null;
  mechanism: MiddleMechanism;
  mechanism_note: string | null;
  group_members: string[] | null;
}
export interface MiddleEnrollmentSnapshot {
  year: number;
  district: string;
  source: string;
  source_url: string | null;
  mechanisms: Record<MiddleMechanism, MiddleMechanismDef>;
  records: MiddleEnrollmentRecord[];
}

/** 学段标识 */
export type SchoolStage = 'primary' | 'middle' | 'high';
