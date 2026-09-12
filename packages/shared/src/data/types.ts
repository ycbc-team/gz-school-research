/**
 * 业务数据层共享类型（原 apps/web/src/data/index.ts 定义，迁移到 @gz/shared）。
 * 真源结构由 scripts/ 保证，类型与真源字段对齐。
 */
import type { XiaoshengchuRecord } from '../types.js';

/** 名额分配：一所初中的行记录（quota_matrix.schools 元素） */
export interface QuotaSchool {
  page: number;
  row: number;
  school: string;
  /** 实体表外键（backfill_school_ids.py 回填；未命中实体则无此字段） */
  school_id?: string;
  kaosheng: number | null; // 名额考生数 m_j
  sheng_quota: number | null; // 省市属名额
  qu_quota: number | null; // 区属名额
  sz: Record<string, number | null>; // 21 省市属校区指标数 n_ji（稀疏化后缺失键 === null）
  sz_sum: number;
  is_district_head?: boolean;
  district: string | null;
}
export interface QuotaMatrix {
  schools: QuotaSchool[];
  districts: string[];
}

/** 特招通道：high_schools 校区列表 + matrix[初中名][高中全称] */
export interface SpecialMatrix {
  high_schools: string[];
  matrix: Record<string, Record<string, { sports?: number; arts?: number; autonomy?: number }>>;
  /** 初中名 → 实体 school_id（backfill 回填；官方名唯一外键） */
  middle_school_ids?: Record<string, string>;
}

/** 第二批次录取分数记录（值 = 校区 → 记录；无分数的 false 记录已在数据治理中删除） */
export interface Batch2Record {
  admitted?: boolean;
  min_score?: number | null;
  last_score?: number | null;
}
export interface Batch2Scores {
  data: Record<string, Record<string, Batch2Record>>;
  /** 初中名 → 实体 school_id（backfill 回填；官方名唯一外键） */
  middle_school_ids?: Record<string, string>;
}

/** 高中统招录取分数记录（data/high/scores_{year}.json，官方招考办发布；按 school_id 引用实体表） */
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

/** 学校身份注册表（site 粒度） */
export interface Site {
  id: string;
  poi_name: string;
  district: string;
  stage: string;
  gov_names?: string[];
  aliases?: string[];
}

/** 品牌关联 */
export interface BrandUnit {
  name: string;
  role: string;
  /** same=与品牌核心同法人（计入口碑）；independent=独立法人（借用品牌→挂牌） */
  legal: 'same' | 'independent';
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

/** 学校徽章 */
export interface SchoolBadge {
  text: string;
  cls: string;
}

/** 小学升学路线事实记录（页面消费形状，feed 已解析为校名数组） */
export type { XiaoshengchuRecord };
