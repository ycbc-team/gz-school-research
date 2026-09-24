/**
 * 数据加载层：Web 端统一加载紧凑数据模块（由 scripts/data/compact.mjs 从 data/ JSON 真源编译，
 * 经 @gz/shared hydrate 还原为原 JSON 结构），组装 DataLoaders 注入 createRepository。
 * 业务逻辑（查询/判定/匹配）已下沉 @gz/shared/src/data，本文件仅保留加载与导出。
 * 小程序端对应实现见 apps/miniprogram/utils/data.js（同一紧凑编译，CJS 产物）。
 */
import { hydrate, splitEnrollments, createRepository, buildPoints, type DataLoaders, type MapPointFull, type MergedEnrollments, type MiddleEnrollmentSnapshot, type MiddleEnrollmentGroups, type MiddleMechanism, type MiddleMechanismDef } from '@gz/shared';
import primarySchoolsCompact from './compact/poi/dist/primary_poi.js';
import primaryTier1Compact from './compact/primary/tier1_schools_all.js';
import entitiesCompact from './compact/registry/entity/dist/entities.js';
import xiaoshengchu2026Compact from './compact/primary/xiaoshengchu_2026.js';
import middleEnrollNotesCompact from './compact/primary/middle_enroll_notes.js';
import middleSchoolsCompact from './compact/poi/dist/middle_poi.js';
import middleTier1Compact from './compact/middle/tier1_schools_all.js';
import highSchoolsCompact from './compact/poi/dist/high_poi.js';
import highLevelsCompact from './compact/high/level/src/levels.js';
import enroll2026AllCompact from './compact/primary/enrollments/2026-all.js';
import middleEnrollment2026Compact from './compact/middle/enrollment/dist/middle_enrollment_2026.js';
import quotaMatrixCompact from './compact/linkage/quota_matrix.js';
import rankingMiddleCompact from './compact/linkage/ranking_middle.js';
import specialMatrixCompact from './compact/linkage/special_matrix.js';
import batch2ScoresCompact from './compact/linkage/batch2_scores.js';
import districtQuotaCompact from './compact/linkage/district_quota.js';
import brandGroupsCompact from './compact/registry/group/src/brand_groups.js';
import educationGroupsCompact from './compact/registry/group/dist/education_groups.js';
import nonGroupMultiCampusesCompact from './compact/registry/group/dist/non_group_multi_campuses.js';
import highScores2025Compact from './compact/high/cutoff_score/dist/scores_2025.js';
import highScores2026Compact from './compact/high/cutoff_score/dist/scores_2026.js';
import orgSortCompiledCompact from './compact/middle/org_sort/dist/compiled.js';
import innovationAwardsCompact from './compact/awards/innovation/dist/compiled.js';
import chuangkeAwardsCompact from './compact/awards/chuangke/dist/compiled.js';
import scienceLiteracyAwardsCompact from './compact/awards/science_literacy/dist/compiled.js';
import detailedRecordsCompact from './compact/awards/dist/detailed_records.js';
import specialtySchoolsCompact from './compact/specialty_schools/dist/specialty_schools.js';
import civilizedCampusSchoolIdsCompact from './compact/civilized_campuses/dist/civilized_campus_school_ids.js';

/** 紧凑结构经 hydrate 还原后的类型断言（字段为数据真源，结构由 scripts/ 保证） */
const cast = <T>(v: unknown): T => v as T;

/** 组装 DataLoaders（结构契约见 @gz/shared/src/data/loader.ts） */
const loaders: DataLoaders = {
  primarySchools: cast(hydrate(primarySchoolsCompact)),
  primaryTier1: cast(hydrate(primaryTier1Compact)),
  middleSchools: cast(hydrate(middleSchoolsCompact)),
  middleTier1: cast(hydrate(middleTier1Compact)),
  highSchools: cast(hydrate(highSchoolsCompact)),
  highLevels: cast(hydrate(highLevelsCompact)),
  enrollments: cast(splitEnrollments(hydrate(enroll2026AllCompact) as unknown as MergedEnrollments)),
  // dist 合并一份（2026-09-23）：{year, mechanisms, groups, districts}；loader 语义不变（数组 7 区）
  middleEnrollments: Object.values(cast<{ districts: Record<string, MiddleEnrollmentSnapshot> }>(hydrate(middleEnrollment2026Compact)).districts),
  middleEnrollmentMechanisms: cast<{ mechanisms: Record<MiddleMechanism, MiddleMechanismDef> }>(hydrate(middleEnrollment2026Compact)).mechanisms,
  middleEnrollmentGroups: cast<{ groups: MiddleEnrollmentGroups }>(hydrate(middleEnrollment2026Compact)).groups,
  quotaMatrix: cast(hydrate(quotaMatrixCompact)),
  rankingMiddle: cast(hydrate(rankingMiddleCompact)),
  specialMatrix: cast(hydrate(specialMatrixCompact)),
  batch2Scores: cast(hydrate(batch2ScoresCompact)),
  highScores2025: cast(hydrate(highScores2025Compact)),
  highScores2026: cast(hydrate(highScores2026Compact)),
  districtQuota: cast(hydrate(districtQuotaCompact)),
  entities: cast(hydrate(entitiesCompact)),
  xiaoshengchu: cast(hydrate(xiaoshengchu2026Compact)),
  middleEnrollNotes: cast(hydrate(middleEnrollNotesCompact)),
  brandGroups: cast(hydrate(brandGroupsCompact)),
  educationGroups: cast(hydrate(educationGroupsCompact)),
  nonGroupMultiCampuses: cast(hydrate(nonGroupMultiCampusesCompact)),
  innovationAwards: cast(hydrate(innovationAwardsCompact)),
  chuangkeAwards: cast(hydrate(chuangkeAwardsCompact)),
  scienceLiteracyAwards: cast(hydrate(scienceLiteracyAwardsCompact)),
  detailedRecords: cast(hydrate(detailedRecordsCompact)),
};

/** 共享数据仓库（查询/判定/匹配业务逻辑全部来自 @gz/shared，双端单点维护） */
export const repository = createRepository(loaders);
/** 派位组表（dist 合并 groups：district/name/primaryIds，2026-09-24 精简），详情页组名 Badge/生源小学用 */
export const middleEnrollmentGroups = loaders.middleEnrollmentGroups;

/** 地图点位集（三学段合并/去重/分类，构建一次；小程序同构导出） */
export const mapPoints: MapPointFull[] = buildPoints(loaders);
export type { MapPointFull };

/* ================= 数据快照导出（页面/组件直接消费，名称保持迁移前一致） ================= */
export const primarySchools = loaders.primarySchools;
export const primaryTier1 = loaders.primaryTier1;
export const middleSchools = loaders.middleSchools;
export const middleTier1 = loaders.middleTier1;
export const highSchools = loaders.highSchools;
export const highLevels = loaders.highLevels;
export const highScores2025 = loaders.highScores2025;
export const highScores2026 = loaders.highScores2026;
export const quotaMatrix = loaders.quotaMatrix;
export const rankingMiddle = loaders.rankingMiddle;
export const specialMatrix = loaders.specialMatrix;
export const batch2Scores = loaders.batch2Scores;
export const enrollments = loaders.enrollments;
export const brandGroups = loaders.brandGroups;
export const entities = loaders.entities;
export const innovationAwards = loaders.innovationAwards || {};
export const chuangkeAwards = loaders.chuangkeAwards || {};
export const scienceLiteracyAwards = loaders.scienceLiteracyAwards || {};
export const detailedRecords = loaders.detailedRecords || [];
export const specialtySchools = cast(hydrate(specialtySchoolsCompact)) as {
  updated: string;
  metric: string;
  summary: {
    total_records: number;
    total_schools: number;
    matched_schools: number;
    unmatched_schools: number;
    recognition_pool: number;
  };
  recognition: Array<{
    category: string;
    level: string;
    batch: string;
    year: number | string;
    project: string;
    issuer: string;
    url: string;
    stage?: string;
  }>;
  schools: Array<{
    school: string;
    ids: string[];
    stage: string[];
    rec: number[];
    notes?: Array<{ i: number; g?: string; t?: string }>;
  }>;
};
/** 全国文明校园运行时索引：dist 只保留 school_id，称号证据保留在 data/civilized_campuses/parsed。 */
export const civilizedCampusSchoolIds = cast(hydrate(civilizedCampusSchoolIdsCompact)) as Record<string, string[]>;
export const nationalCivilizedCampusSchoolIds = civilizedCampusSchoolIds.national ?? [];

/** 七区初中机构整理档位整合版（data/middle/org_sort/dist/compiled.json，由 data/middle/org_sort/scripts/build_org_sort.py 经
 * SchoolMatcher 匹配生成；仅 school_id→档位，无展示字段；仅供内部默认排序，对外不展示档位信息） */
export const middleOrgSort = cast(hydrate(orgSortCompiledCompact)) as Array<{
  district: string;
  level: number;
  school_id: string;
}>;

/* ================= 查询/常量（来自 repository，名称保持迁移前一致） ================= */
export const {
  isComprehensive,
  matchEnrollment,
  middleQuotaSummary,
  linkageOf,
  batch2Of,
  districtQuotaOf,
  districtCoverage,
  quotaCoverage,
  xiaoshengchuOf,
  middlePrimaryFeed,
  middleEnrollmentOf,
  middleEnrollmentsOf,
  schoolBadges,
  scoresOfSchool,
  scoresBySchoolId,
  resolveSchoolId,
  resolveSchoolIdOf,
  resolvePoiName,
  groupOfSchool,
  tier1Schools,
  middleTier1Schools,
  campuses,
} = repository;

/* ================= 类型重导出（页面 import 来源不变） ================= */
export type {
  QuotaSchool,
  QuotaMatrix,
  SpecialMatrix,
  Batch2Record,
  Batch2Scores,
  HighScoreRecord,
  HighScores,
  BrandUnit,
  BrandGroup,
  SchoolBadge,
} from '@gz/shared';
