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
  /** 新校核对补录标记（如「新开办（2026）·待首届成绩」） */
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

/** 派位/对口分组表（xiaoshengchu 顶层 groups，避免逐记录重复组名/source_url） */
export interface XiaoshengchuGroup {
  id: number;
  name: string;
  /** 组级来源（组内 85/88 一致；多区汇聚组含多个 url） */
  source_urls: string[];
  /** 组级数据缺口说明（记录级覆盖见 XiaoshengchuFactRecord.data_gaps） */
  data_gaps: string | null;
  /** 升学机制枚举（初中枚举，与 middle/enrollment mechanism 对齐；数据层固化） */
  mechanism: string[];
}

/** 真源事实记录（data/primary/transition/dist/xiaoshengchu_2026.json 的 records，school_id 引用实体） */
export interface XiaoshengchuFactRecord {
  school_id: string;
  group_id: number;
  direct_feed_school_id: string | null;
  source_note?: string;
  /** 记录级升学机制枚举（初中枚举，与 middle/enrollment mechanism 对齐；dist 五区以初中反推为准） */
  mechanism?: string[];
  /** 仅当与组级 data_gaps 不同时存在（记录级覆盖） */
  data_gaps?: string | null;
  /** 2026-10-08（天河双机制拆分）：feed 按机制分组（机制→[初中 id]；single_zone 划片 /
   * single_paidui 电脑派位池 / single_chouqian 电脑抽签池 / group_paidui 派位组各自成组），
   * 前端按机制块渲染对应 feed。
   * 2026-10-08（字段精简）：全量扁平 feed_school_ids/feed_unresolved 已删除，
   * 全量列表由消费方从本分组并集派生（单一真源，避免两套数据不一致）。 */
  feed_school_ids_by_mechanism?: Record<string, string[]>;
  /** 同上：未解析初中名按机制分组（显式缺口，可审计） */
  feed_unresolved_by_mechanism?: Record<string, string[]>;
}

/** 运行时展示形状（quota.ts shapeRecord 适配输出） */
export interface XiaoshengchuRecord {
  /** 学校名（与 POI 全称对齐） */
  name: string;
  /** 派位/对口分组描述（官方口径，由组表解析） */
  group: string | null;
  /** 升学机制枚举（初中枚举，与 middle/enrollment mechanism 对齐；数据层固化，运行时零文本匹配） */
  mechanisms: string[];
  /** 对口/派位初中名单 */
  feed_junior_highs: string[];
  /** 对口直升本校初中（直升场景，与派位名单互斥为主） */
  direct_feed: string | null;
  /** 2026-10-08（天河双机制拆分）：feed 按机制分组（机制→[初中名，含未解析名]），
   * 前端「升学路线」按机制块渲染各自 feed；无该字段/空 dict 时前端回退 feed_junior_highs 全量 */
  feed_by_mechanism?: Record<string, string[]>;
  source_url: string;
  source_note: string;
  /** 数据缺口说明（feed 为空时必填原因，如民办不参与公办派位） */
  data_gaps: string | null;
  /** 按招生机制拆分的升学路线分组（多机制小学一项一盒；单机制数组长为 1） */
  routeGroups: RouteGroup[];
}

/** 升学路线分组下的单所学校（含实体 id 用于跳转定位） */
export interface RouteSchool {
  id: string | null;
  name: string;
}

/** 按招生机制（mechanism）拆分的升学路线分组 */
export interface RouteGroup {
  /** 机制 key（zhi_sheng / single_zone / group_paidui / single_paidui / min_zi_zhu） */
  mechanism: string;
  /** 机制中文标签（XS_MECH_LABELS） */
  label: string;
  /** 该机制对应的对口 / 派位初中 */
  schools: RouteSchool[];
}

/** data/primary/transition/dist/xiaoshengchu_2026.json */
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

/** data/registry/affiliation/src/levels.json */
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
  /** 民办招生计划人数（民办无地段，仅班数/人数；公办无此列） */
  plan_count?: number | null;
  zone?: string;
  note?: string;
  phone?: string;
  source: string;
}

/** 民办小学招生计划记录（enrollment dist 产物 minban 段）：无招生地段，仅计划班数/人数 */
export interface EnrollmentMinbanRecord {
  school: string;
  district: string;
  plan_classes?: number | null;
  plan_count?: number | null;
  school_id?: string;
  poi_name?: string;
  lng?: number | null;
  lat?: number | null;
}

export interface EnrollmentAmbiguous {
  school: string;
  poi: string;
  compete_with: string;
}

/** data/primary/transition/parsed/2026-*.json */
export interface EnrollmentSnapshot {
  year: number;
  district: string;
  source: string;
  source_url: string;
  records: EnrollmentRecord[];
  /** 民办小学招生计划（独立段：无地段，仅计划班数/人数；当前仅番禺官方文件公布） */
  minban?: EnrollmentMinbanRecord[];
  unmatched: string[];
  ambiguous: EnrollmentAmbiguous[];
  poi_leftover: string[];
  map_fail: string[];
}

/** data/middle/enrollment/dist/middle_enrollment_2026_*.json —— 初中视角招生计划 */
export type MiddleMechanism = 'single_zone' | 'zhi_sheng' | 'group_paidui' | 'single_paidui' | 'single_chouqian' | 'min_zi_zhu' | 'no_plan';
export interface MiddleMechanismDef {
  label: string;
  can_lose: boolean;
  lose_text: string | null;
}
export interface MiddleEnrollmentRecord {
  /** 单一归属 school_id；合并招生（多校区共用一套计划）时为 null，改用 school_ids 列出全部校区 */
  school_id: string | null;
  /** 多校区共用同一招生计划时列出全部校区 id（如番禺铁英学校 28 班合并招生：东/西两校区） */
  school_ids?: string[];
  plan_classes: number | null;
  scope: string | null;
  /** 直升小学 scope 拆段 → 小学实体 id（2026-09-24：数据层 SchoolMatcher 匹配，
   * 仅「小学名形态」段命中；前端据此把对口直升小学聚合为可点击行，未命中段保留 scope 文本展示） */
  scope_school_ids?: Record<string, string[]>;
  mechanism: MiddleMechanism;
  mechanism_note: string | null;
  /** dist 合并结构（2026-09-23）：组表 group_id（派位/直升组）；2026-09-24 dist 不再存 school 名称（前端按 school_id 联查实体名，parsed 审计层保留） */
  group_id?: string | null;
}
export interface MiddleEnrollmentSnapshot {
  year: number;
  district: string;
  source: string;
  source_url: string | null;
  records: MiddleEnrollmentRecord[];
}
/** dist 合并结构：mechanisms 顶层一份 + groups 独立组表（包体优化） */
export type MiddleEnrollmentGroups = Record<
  string,
  {
    district: string;
    name?: string;
    /** 生源小学名 → school_id 列表（构建期实体匹配；多校区多个 id，key 即小学名列表，前端 Object.keys 遍历） */
    primaryIds?: Record<string, string[]>;
  }
>;

/** 学段标识 */
export type SchoolStage = 'primary' | 'middle' | 'high';
