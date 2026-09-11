/**
 * 小程序数据加载（与 Web apps/web/src/data/index.ts 同构）：
 * shared 逻辑（@gz/shared cjs 构建产物）+ data 紧凑模块（compact.mjs 从项目根 data/ 唯一真源编译，
 * 经 hydrate 还原为原 JSON 结构），组装 DataLoaders 注入 createRepository。
 * 构建产物勿手改。
 *
 * 主包/分包拆分：地图页消费的主包数据 15 个在此加载；详情页专用数据（linkage/sites/brandGroups/
 * educationGroups 7 个）在 pages/school-detail 分包，由详情页 require 分包模块后
 * 与 baseLoaders 合并为全量 loaders 再 createRepository（buildDetailModel/buildLinkageModel 消费）。
 * 主包 repository 的详情域方法（quota/special/batch2/coverage/brand 等）因空壳数据返回空，地图页不消费。
 */
const shared = require('../shared/index.js');

const { hydrate, createRepository, buildPoints } = shared;

const cast = (v) => v;

/** 主包 loaders（含详情域空壳，供详情页分包展开合并） */
const baseLoaders = {
  primarySchools: cast(hydrate(require('../data/primary/schools-gz.js'))),
  primaryTier1: cast(hydrate(require('../data/primary/tier1_schools_all.js'))),
  middleSchools: cast(hydrate(require('../data/middle/schools-gz.js'))),
  middleTier1: cast(hydrate(require('../data/middle/tier1_schools_all.js'))),
  highSchools: cast(hydrate(require('../data/high/schools-gz.js'))),
  highLevels: cast(hydrate(require('../data/high/levels.js'))),
  highScores2025: cast(hydrate(require('../data/high/scores_2025.js'))),
  highScores2026: cast(hydrate(require('../data/high/scores_2026.js'))),
  enrollments: [
    cast(hydrate(require('../data/primary/enrollments/2026-tianhe.js'))),
    cast(hydrate(require('../data/primary/enrollments/2026-yuexiu.js'))),
    cast(hydrate(require('../data/primary/enrollments/2026-haizhu.js'))),
    cast(hydrate(require('../data/primary/enrollments/2026-liwan.js'))),
    cast(hydrate(require('../data/primary/enrollments/2026-panyu.js'))),
    cast(hydrate(require('../data/primary/enrollments/2026-baiyun.js'))),
    cast(hydrate(require('../data/primary/enrollments/2026-huangpu.js'))),
  ],
  entities: cast(hydrate(require('../data/registry/entities.js'))),
  xiaoshengchu: cast(hydrate(require('../data/primary/xiaoshengchu_2026.js'))),
  // ---- 详情域空壳（分包 pages/school-detail/data/ 提供真实数据） ----
  quotaMatrix: { schools: [], districts: [] },
  specialMatrix: { high_schools: [], matrix: {} },
  batch2Scores: { data: {} },
  districtQuota: { data: {} },
  sites: { schools: [] },
  brandGroups: { brands: [] },
};

const repository = createRepository(baseLoaders);
const mapPoints = buildPoints(baseLoaders);

module.exports = {
  shared,
  baseLoaders,
  repository,
  mapPoints,
  // 快照导出（页面直接消费）
  primarySchools: baseLoaders.primarySchools,
  primaryTier1: baseLoaders.primaryTier1,
  middleSchools: baseLoaders.middleSchools,
  middleTier1: baseLoaders.middleTier1,
  highSchools: baseLoaders.highSchools,
  highLevels: baseLoaders.highLevels,
  enrollments: baseLoaders.enrollments,
};
