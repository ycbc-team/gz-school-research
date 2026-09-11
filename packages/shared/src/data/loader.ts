/**
 * 数据加载抽象（loader 注入）：@gz/shared 不内嵌 JSON，各端注入同一结构的数据快照。
 * - Web：apps/web/src/data/loader.ts 从紧凑模块 hydrate 后组装
 * - 小程序：apps/miniprogram/utils/data.js 从 CJS 紧凑模块 hydrate 后组装
 * 真源唯一：data/ 目录 JSON（scripts/data/compact.mjs 编译为双端紧凑产物）
 */
import type {
  SchoolsSnapshot,
  Tier1Snapshot,
  HighLevelsSnapshot,
  EnrollmentSnapshot,
} from '../types.js';
import type { QuotaMatrix, SpecialMatrix, Batch2Scores, HighScores, Site, BrandGroups } from './types.js';

export interface DataLoaders {
  primarySchools: SchoolsSnapshot;
  primaryTier1: Tier1Snapshot;
  middleSchools: SchoolsSnapshot;
  middleTier1: Tier1Snapshot;
  highSchools: SchoolsSnapshot;
  highLevels: HighLevelsSnapshot;
  /** 小学 2026 招生计划（7 区） */
  enrollments: EnrollmentSnapshot[];
  quotaMatrix: QuotaMatrix;
  specialMatrix: SpecialMatrix;
  batch2Scores: Batch2Scores;
  /** 高中统招录取分数（官方招考办，2025/2026 两年；按 school_id 引用实体表） */
  highScores2025: HighScores;
  highScores2026: HighScores;
  /** 区属指标到校（另一 agent 数据） */
  districtQuota: { data: Record<string, Record<string, number>> };
  /** 实体注册表（school_id 外键 → 名称/别名） */
  entities: { entities: Array<{ school_id: string; name: string; stage: string; aliases: string[] }> };
  /** 小学 2026 升学路线事实表（group 提为顶层 groups，记录按 group_id 引用） */
  xiaoshengchu: {
    groups: Array<{ id: number; name: string; source_urls: string[]; data_gaps: string | null }>;
    records: Array<{
      school_id: string; group_id: number;
      feed_school_ids: string[]; feed_unresolved: string[];
      direct_feed_school_id: string | null;
      source_note?: string; data_gaps?: string | null;
    }>;
  };
  /** 学校身份注册表（site 粒度） */
  sites: { schools: Array<{ sites: Site[] }> };
  brandGroups: BrandGroups;
}
