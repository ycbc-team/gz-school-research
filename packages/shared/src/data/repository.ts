/**
 * 数据仓库：createRepository(loaders) 聚合各域 API，双端共享的查询入口。
 * 查询索引在构建时一次性建立，双端行为完全一致。
 *
 * Web：apps/web/src/data/index.ts 组装 loaders 后调用
 * 小程序：apps/miniprogram/utils/data.js 同构组装
 */
import type { DataLoaders } from './loader.js';
import { createSchoolsApi } from './schools.js';
import { createEnrollmentApi } from './enrollment.js';
import { createQuotaApi } from './quota.js';
import { createRegistryApi } from './registry.js';
import { createBadgesApi } from './badges.js';
import {
  CAMPUS_SHORT, CAMPUS_SCHOOL, CAMPUS_TO_SPECIAL, CAMPUS_TO_BATCH2,
} from './campuses.js';

export type { DataLoaders };

export function createRepository(loaders: DataLoaders) {
  const schools = createSchoolsApi(loaders);
  const enrollment = createEnrollmentApi(loaders);
  const quota = createQuotaApi(loaders);
  const registry = createRegistryApi(loaders);
  const badges = createBadgesApi(loaders);

  return {
    /** tier1 学校数组（跨区拍平） */
    tier1Schools: Object.values(loaders.primaryTier1.districts).flatMap((d) => d.schools),
    middleTier1Schools: Object.values(loaders.middleTier1.districts).flatMap((d) => d.schools),
    /** 实体注册表（口碑匹配别名唯一宿主） */
    entities: loaders.entities.entities,

    /** 学段 POI 快照（学段判定/徽章等场景用） */
    schools: {
      primary: loaders.primarySchools,
      middle: loaders.middleSchools,
      high: loaders.highSchools,
    },
    /** 高中分类/出口数据（高中详情、高中学段判定用） */
    highLevels: loaders.highLevels,
    /** tier1 快照（小学小升初机制等场景用） */
    primaryTier1: loaders.primaryTier1,
    middleTier1: loaders.middleTier1,

    ...schools,
    ...enrollment,
    ...quota,
    ...registry,
    ...badges,

    /** 校区常量（21 省市属，quota_matrix.sz 键序） */
    CAMPUS_SHORT,
    CAMPUS_SCHOOL,
    CAMPUS_TO_SPECIAL,
    CAMPUS_TO_BATCH2,
  };
}

export type Repository = ReturnType<typeof createRepository>;
