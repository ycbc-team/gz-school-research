/**
 * 业务数据层共享类型（原 apps/web/src/data/index.ts 定义，迁移到 @gz/shared）。
 * 真源结构由 scripts/ 保证，类型与真源字段对齐。
 *
 * 2026-09-24 精简口径（用户拍板）：dist 只保留有前端引用的最精简字段，
 * 调试字段（page/row/sz_sum/districts/note 等）只进 canonical（快照覆盖）。
 * 行/键主键 id 优先：有 school_id 的键/行进 ids，仅无 id 匹配保留原文名进 schools，
 * 前端展示"id 实体名可点击跳转 + school 名不可点击跳转"。
 */
import type { XiaoshengchuRecord } from '../types.js';

/** 名额分配：初中行（dist quota_matrix.ids 元素；有 school_id，前端 join 实体表展示实体名） */
export interface QuotaRowId {
  district: string | null;
  kaosheng: number | null; // 名额考生数 m_j
  sheng_quota: number | null; // 省市属名额
  qu_quota: number | null; // 区属名额
  /** 21 省市属校区指标数 n_ji（id 键，只存非零；实体表缺口校区在 sz_schools 原文保底） */
  sz?: Record<string, number>;
  /** 实体表缺口的省市属校区指标（官方原文名 → 数，无实体不可跳转；2026 为广雅花都/六中从化/六中花都） */
  sz_schools?: Record<string, number>;
  school_id: string;
  /** 法人多校区（官方升学文件按法人单位公布，backfill 由实体表去括号校区推导生成）；
   *  仅法人行存在，含 school_id 本身；前端升学信息按法人聚合、各校区分别跳转 */
  school_ids?: string[];
}
/** 名额分配：初中行（dist quota_matrix.schools 元素；无实体 id，原文兜底展示、不可点击跳转） */
export interface QuotaRowName {
  district: string | null;
  kaosheng: number | null;
  sheng_quota: number | null;
  qu_quota: number | null;
  sz?: Record<string, number>;
  sz_schools?: Record<string, number>;
  school: string;
}
/** 配额行统一视图（查询域使用：两种行按 locator 分别命中） */
export type QuotaSchool = QuotaRowId | QuotaRowName;
export interface QuotaMatrix {
  ids: QuotaRowId[];
  schools: QuotaRowName[];
  /** 官方名单原文名 → 法人行 school_id（py 层 backfill 生成：法人聚合/主 id 归一等
   *  全部名称推断在数据层完成，运行时只做 id 精准匹配） */
  name_index: Record<string, string>;
  /** 21 省市属校区（官方汇总表顺序）：id=高中实体 school_id（18，前端 join 实体表展示名）；
   *  id=null 为实体表缺口校区（3），name 为官方原文保底展示；school=归属法人名（官方原文去括号） */
  campuses: Array<{ id: string | null; name: string; school: string }>;
}

/** 特招通道：计划数 + 名单外键（资格名单计数矩阵已于 2026-09 废弃） */
export interface SpecialMatrix {
  /** 官方第一批招生单位原文 → 高中实体外键；null=未收录实体，只保留原文展示，禁止名称兜底 */
  high_school_ids?: Record<string, string | null>;
  /** 2026 自主招生计划（官方汇总表，原文名 → 计划数）；计划数≠资格名单人数≠录取人数 */
  autonomy_plan?: Record<string, number>;
  /** autonomy_plan 的 normName 归一索引（前端查询兜底） */
  autonomy_plan_norm?: Record<string, number>;
  /** 2026 体育/艺术特长生计划（实体 school_id 外键 → 计划数/项目明细；值内 name 已删，实体名 join 实体表） */
  special_plan?: Record<string, {
    sports?: number;
    arts?: number;
    sports_projects?: Array<{ project: string; plan: number; note?: string }>;
    arts_projects?: Array<{ project: string; plan: number; note?: string }>;
  }>;
}

/** 第二批次录取分数记录（值 = 校区 → 记录；无分数的 false 记录已在数据治理中删除） */
export interface Batch2Record {
  admitted?: boolean;
  min_score?: number | null;
  last_score?: number | null;
}
/** 第二批次（dist）：外层键（高中校区）与内层键（初中）各自 id 优先 + 原文兜底 */
export interface Batch2Scores {
  ids: Record<string, { ids: Record<string, Batch2Record>; schools: Record<string, Batch2Record> }>;
  schools: Record<string, { ids: Record<string, Batch2Record>; schools: Record<string, Batch2Record> }>;
}
/** 区属指标到校（dist）：外层键（初中）与内层键（区属高中）各自 id 优先 + 原文兜底 */
export interface DistrictQuota {
  ids: Record<string, { ids: Record<string, number>; schools: Record<string, number> }>;
  schools: Record<string, { ids: Record<string, number>; schools: Record<string, number> }>;
}

/** 高中统招录取分数记录（data/high/cutoff_score/dist/scores_{year}.json，官方招考办发布；按 school_id 引用实体表） */
export interface HighScoreRecord {
  /** 官方招生单位原文名（含校区/班型，如「华南师范大学附属中学（石牌校区）」「广州市为明学校（盛景校区）」） */
  official_name: string;
  /** 学校性质：公办 / 民办 / 中外合作（官方「学校性质」列） */
  nature: string;
  /** 批次：1=第一批次（外语艺术类） 3=第三批次 4=第四批次 */
  batch: number;
  /** 记录类型：public=公办（户籍/非户籍/外区生三口径） private=民办/中外合作（最低分数口径） lang_art=外语艺术类（末位考生分数口径） */
  kind: 'public' | 'private' | 'lang_art';
  scope?: string;
  /** 公办：户籍生最低分数 */
  huji?: number | null;
  /** 公办：非户籍生最低分数 */
  feihuji?: number | null;
  /** 公办：外区生最低分数（仅第三批） */
  waiqu?: number | null;
  /** 民办/中外合作：最低分数 */
  min_score?: number | null;
  /** 外语艺术类：户籍生末位考生分数 */
  huji_last?: number | null;
  /** 外语艺术类：非户籍生末位考生分数 */
  feihuji_last?: number | null;
  /** 民办公费班条目（官方独立条目，名含「（公费班）」） */
  gongfei?: boolean;
}
export interface HighScores {
  year: number;
  title: string;
  updated: string;
  source: Array<{ batch: number; title: string; url: string }>;
  /** 校区实体（school_id）→ 该校区录取记录（可多批次/多条目） */
  by_school_id: Record<string, HighScoreRecord[]>;
  /** 未收录实体（远郊 7 区外 / 中外合作办学项目 / 新校）的官方原文，保留数据供扩展 */
  unmapped: Array<Record<string, unknown>>;
}

/** 品牌关联 */
export interface BrandUnit {
  name: string;
  role: string;
  /** same=与品牌核心同法人；independent=独立法人（借用品牌） */
  legal: 'same' | 'independent';
  /** 实体外键；品牌当前态、详情跳转优先使用，禁止以名称猜测校区 */
  school_ids?: string[];
  /** 该单位的 POI 名覆盖（tier1 aliases 未覆盖其点位名时使用） */
  poi_names?: string[];
}
export interface BrandGroup {
  brand: string;
  brand_note?: string;
  units: BrandUnit[];
}
export interface BrandGroups {
  title: string;
  verified_date: string;
  scope?: string;
  brands: BrandGroup[];
}

/** 全量教育集团（区教育局官方口径，data/registry/education_groups.json） */
export interface EducationGroupMember {
  name: string;
  stage: string;
  verified?: string;
  poi_match?: string;
  poi_name?: string;
  school_id?: string;
  /** 品牌组合并入 education 时保留的完整实体外键（如「黄埔铁英」= 中学+小学两个实体）；
   * 运行时学段兜底与跳转判定使用，避免只保留首 id 导致学部 Badge 丢失 */
  school_ids?: string[];
  /** 多校区索引：成员校在 POI 里有多个校区时，列出所有校区（poi_match="多校区索引"时使用） */
  campuses?: Array<{ poi_name: string; school_id: string }>;
}
export interface EducationGroup {
  brand: string;
  district: string;
  core: string[];
  core_poi?: Array<{ name: string; poi_match?: string; poi_name?: string; school_id?: string }>;
  level?: string;
  type?: string;
  members: EducationGroupMember[];
  source_urls: string[];
  note?: string;
}
export interface EducationGroups {
  title: string;
  updated: string;
  source_scope?: string;
  note?: string;
  groups: EducationGroup[];
}

/** 学校徽章 */
export interface SchoolBadge {
  text: string;
  cls: string;
}

/** 小学升学路线事实记录（页面消费形状，feed 已解析为校名数组） */
export type { XiaoshengchuRecord };
