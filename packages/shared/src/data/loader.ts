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
  MiddleEnrollmentSnapshot,
  MiddleMechanism,
  MiddleMechanismDef,
  MiddleEnrollmentGroups,
} from '../types.js';
import type { QuotaMatrix, SpecialMatrix, Batch2Scores, HighScores, BrandGroups, EducationGroups } from './types.js';

export interface DataLoaders {
  primarySchools: SchoolsSnapshot;
  primaryTier1: Tier1Snapshot;
  middleSchools: SchoolsSnapshot;
  middleTier1: Tier1Snapshot;
  highSchools: SchoolsSnapshot;
  highLevels: HighLevelsSnapshot;
  /** 小学 2026 招生计划（7 区） */
  enrollments: EnrollmentSnapshot[];
  /** 初中 2026 招生计划（7 区，初中视角：班数/招生范围/机制/派位组成员） */
  middleEnrollments: MiddleEnrollmentSnapshot[];
  /** dist 合并结构（2026-09-23）：mechanisms 顶层一份、派位/直升组独立组表（record.group_id 引用） */
  middleEnrollmentMechanisms: Record<MiddleMechanism, MiddleMechanismDef>;
  middleEnrollmentGroups: MiddleEnrollmentGroups;
  /** 极少数校区的招生计划特殊备注（school_id → 说明，如执信水荫路仅初三就读）；无备注的学校不写 */
  middleEnrollNotes?: Record<string, string>;
  quotaMatrix: QuotaMatrix;
  specialMatrix: SpecialMatrix;
  batch2Scores: Batch2Scores;
  /** 高中统招录取分数（官方招考办，2025/2026 两年；按 school_id 引用实体表） */
  highScores2025: HighScores;
  highScores2026: HighScores;
  /** 区属指标到校（另一 agent 数据）；初中名 → 实体 school_id 由 backfill 回填 */
  districtQuota: { data: Record<string, Record<string, number>>; middle_school_ids?: Record<string, string> };
  /** 实体注册表（school_id 外键 → 名称/别名/办学性质）；nature=民办 为办学性质唯一真源（公办不写字段） */
  entities: { entities: Array<{ school_id: string; name: string; stage: string; aliases: string[]; nature?: string }> };
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
  brandGroups: BrandGroups;
  /** 全量教育集团（区教育局官方口径，85 集团/334 成员；brandGroups 未命中时回退查询） */
  educationGroups?: EducationGroups;
  /** 公共 school_id → 集团映射（scripts/registry/build_school_groups.py 构建，纯 id 产物；
   * 详情页品牌卡与初中明细分组共用同一份，运行时不再做任何按名匹配） */
  schoolGroups: { schoolGroups: Record<string, { brand: string; source: 'education' | 'brand' }> };
  /** 初中升学信号排行榜基础表（自招/指标到校/特控率聚合，见 scripts/linkage/build_ranking_middle.py） */
  rankingMiddle: {
    schools: Array<{
      name: string; school_id?: string | null; district: string;
      group?: { brand: string; source: 'brand' | 'education' } | null;
      kaosheng?: number | null; sheng_quota?: number | null; qu_quota?: number | null;
      autonomy_count: number; sz: Array<{ high: string; count: number; tekong?: number | null }>;
      tekong_quota_rate?: number | null;
    }>;
  };
  /** 创新大赛获奖（school_id → stages → years → 金/银/铜） */
  innovationAwards?: Record<string, { innovation_awards: { stages: Record<string, Record<string, { gold: number; silver: number; bronze: number }>> } }>;
  /** 科技创客电视大赛获奖（school_id → stages → years → 金/银/铜） */
  chuangkeAwards?: Record<string, { chuangke_awards: { stages: Record<string, Record<string, { gold: number; silver: number; bronze: number }>> } }>;
  /** 科学素养大赛获奖（school_id → stages → years → 金/银/铜） */
  scienceLiteracyAwards?: Record<string, { science_literacy_awards: { stages: Record<string, Record<string, { gold: number; silver: number; bronze: number }>> } }>;
  /** 竞赛获奖明细，供获奖页展示年份、项目与获奖学生 */
  detailedRecords?: Array<Record<string, unknown>>;
}
