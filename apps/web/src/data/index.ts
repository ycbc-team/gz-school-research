/**
 * 数据加载层：Web 端统一加载紧凑数据模块（由 scripts/data/compact.mjs 从 data/ JSON 真源编译，
 * 经 @gz/shared hydrate 还原为原 JSON 结构），组装 DataLoaders 注入 createRepository。
 * 业务逻辑（查询/判定/匹配）已下沉 @gz/shared/src/data，本文件仅保留加载与导出。
 * 小程序端对应实现见 apps/miniprogram/utils/data.js（同一紧凑编译，CJS 产物）。
 */
import { hydrate, createRepository, buildPoints, type DataLoaders, type MapPointFull } from '@gz/shared';
import primarySchoolsCompact from './compact/primary/schools-gz.js';
import primaryTier1Compact from './compact/primary/tier1_schools_all.js';
import entitiesCompact from './compact/registry/entities.js';
import xiaoshengchu2026Compact from './compact/primary/xiaoshengchu_2026.js';
import middleSchoolsCompact from './compact/middle/schools-gz.js';
import middleTier1Compact from './compact/middle/tier1_schools_all.js';
import highSchoolsCompact from './compact/high/schools-gz.js';
import highLevelsCompact from './compact/high/levels.js';
import enrollTianheCompact from './compact/primary/enrollments/2026-tianhe.js';
import enrollYuexiuCompact from './compact/primary/enrollments/2026-yuexiu.js';
import enrollHaizhuCompact from './compact/primary/enrollments/2026-haizhu.js';
import enrollLiwanCompact from './compact/primary/enrollments/2026-liwan.js';
import enrollPanyuCompact from './compact/primary/enrollments/2026-panyu.js';
import enrollBaiyunCompact from './compact/primary/enrollments/2026-baiyun.js';
import enrollHuangpuCompact from './compact/primary/enrollments/2026-huangpu.js';
import quotaMatrixCompact from './compact/linkage/quota_matrix.js';
import specialMatrixCompact from './compact/linkage/special_matrix.js';
import batch2ScoresCompact from './compact/linkage/batch2_scores.js';
import districtQuotaCompact from './compact/linkage/district_quota.js';
import sitesRegistryCompact from './compact/registry/sites.js';
import brandGroupsCompact from './compact/registry/brand_groups.js';
import highScores2025Compact from './compact/high/scores_2025.js';
import highScores2026Compact from './compact/high/scores_2026.js';

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
  enrollments: [
    cast(hydrate(enrollTianheCompact)),
    cast(hydrate(enrollYuexiuCompact)),
    cast(hydrate(enrollHaizhuCompact)),
    cast(hydrate(enrollLiwanCompact)),
    cast(hydrate(enrollPanyuCompact)),
    cast(hydrate(enrollBaiyunCompact)),
    cast(hydrate(enrollHuangpuCompact)),
  ],
  quotaMatrix: cast(hydrate(quotaMatrixCompact)),
  specialMatrix: cast(hydrate(specialMatrixCompact)),
  batch2Scores: cast(hydrate(batch2ScoresCompact)),
  highScores2025: cast(hydrate(highScores2025Compact)),
  highScores2026: cast(hydrate(highScores2026Compact)),
  districtQuota: cast(hydrate(districtQuotaCompact)),
  entities: cast(hydrate(entitiesCompact)),
  xiaoshengchu: cast(hydrate(xiaoshengchu2026Compact)),
  sites: cast(hydrate(sitesRegistryCompact)),
  brandGroups: cast(hydrate(brandGroupsCompact)),
};

/** 共享数据仓库（查询/判定/匹配业务逻辑全部来自 @gz/shared，双端单点维护） */
export const repository = createRepository(loaders);

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
export const specialMatrix = loaders.specialMatrix;
export const batch2Scores = loaders.batch2Scores;
export const enrollments = loaders.enrollments;
export const brandGroups = loaders.brandGroups;
export const entities = loaders.entities;

/* ================= 查询/常量（来自 repository，名称保持迁移前一致） ================= */
export const {
  isComprehensive,
  matchEnrollment,
  middleQuotaSummary,
  linkageOf,
  specialOf,
  batch2Of,
  districtQuotaOf,
  districtCoverage,
  quotaCoverage,
  specialCoverage,
  xiaoshengchuOf,
  middlePrimaryFeed,
  schoolBadges,
  supportBadge,
  scoresOfSchool,
  scoresBySchoolId,
  resolveSchoolId,
  resolveSite,
  brandGroupOf,
  tier1Schools,
  middleTier1Schools,
  CAMPUS_NAMES,
  CAMPUS_INFO,
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
  Site,
  BrandUnit,
  BrandGroup,
  SchoolBadge,
} from '@gz/shared';
