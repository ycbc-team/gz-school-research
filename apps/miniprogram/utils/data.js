/**
 * 小程序数据加载（与 Web apps/web/src/data/index.ts 同构）：
 * shared 逻辑（@gz/shared cjs 构建产物）+ data 紧凑模块（compact.mjs 从项目根 data/ 唯一真源编译，
 * 经 hydrate 还原为原 JSON 结构），组装 DataLoaders 注入 createRepository。
 * 构建产物勿手改。
 *
 * 主包/分包拆分：地图页消费的主包数据 15 个在此加载；详情页专用数据（linkage/brandGroups/
 * educationGroups 7 个）在 pages/school-detail 分包，由详情页 require 分包模块后
 * 与 baseLoaders 合并为全量 loaders 再 createRepository（buildDetailModel/buildLinkageModel 消费）。
 * 主包 repository 的详情域方法（quota/special/batch2/coverage/brand 等）因空壳数据返回空，地图页不消费。
 */
const shared = require('../shared/index.js');

const { hydrate, splitEnrollments, createRepository, buildPoints } = shared;

const cast = (v) => v;

/**
 * 构建产物容错：data/** 是 gitignore 产物，历史上两度因「构建链路只跑了一半」导致模块缺失
 * （2026-10-14 / 2026-10-23：compact.mjs 会清空 apps/miniprogram/data/，region 由后续步骤补生成，
 * 中途中断或工具未重新扫描新目录就缺模块）。顶层 require 一旦抛错，app.js 启动即失败 → 整站白屏。
 * 故仅对「独立生产者」region 数据降级：缺失时告警 + 空结构，地图退化为无板块/地铁，其余页面照常。
 * require 的路径必须保持字面量，否则小程序无法静态打包依赖。
 */
let regionPlates = { districts: {} };
try {
  regionPlates = require('../data/region/plates');
} catch (err) {
  console.error('[data] 缺少 data/region/plates，已降级为空板块（请执行 npm run build:mp 重建）', err && err.message);
}
let regionMetro = { lines: [] };
try {
  regionMetro = require('../data/region/metro');
} catch (err) {
  console.error('[data] 缺少 data/region/metro，已降级为空线网（请执行 npm run build:mp 重建）', err && err.message);
}

/** 主包 loaders（含详情域空壳，供详情页分包展开合并） */
const baseLoaders = {
  primarySchools: cast(hydrate(require('../data/poi/dist/primary_poi.js'))),
  middleSchools: cast(hydrate(require('../data/poi/dist/middle_poi.js'))),
  highSchools: cast(hydrate(require('../data/poi/dist/high_poi.js'))),
  highLevels: cast(hydrate(require('../data/high/level/src/levels.js'))),
  highScores2025: cast(hydrate(require('../data/high/cutoff_score/dist/scores_2025.js'))),
  highScores2026: cast(hydrate(require('../data/high/cutoff_score/dist/scores_2026.js'))),
  enrollments: cast(splitEnrollments(hydrate(require('../data/primary/enrollments/2026-all.js')))),
  entities: cast(hydrate(require('../data/registry/entity/dist/entities.js'))),
  xiaoshengchu: cast(hydrate(require('../data/primary/xiaoshengchu_2026.js'))),
  middleEnrollNotes: cast(hydrate(require('../data/primary/middle_enroll_notes.js'))),
  // ---- 区域/地铁数据源（UI 04/04B 三列下钻过滤）：真源 data/region → compact.mjs 产出 apps/miniprogram/data/region ----
  plates: cast(regionPlates),
  metro: cast(regionMetro),
  // ---- 详情域空壳（品牌/教育集团/linkage 模块由分包 pages/school-detail 提供真实数据） ----
  brandGroups: { brands: [] },
  educationGroups: { groups: [] },
  quotaMatrix: { ids: [], schools: [] },
  specialMatrix: { high_school_ids: {}, autonomy_plan: {}, special_plan: {} },
  batch2Scores: { ids: {}, schools: {} },
  districtQuota: { ids: {}, schools: {} },
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
  middleSchools: baseLoaders.middleSchools,
  highSchools: baseLoaders.highSchools,
  highLevels: baseLoaders.highLevels,
  enrollments: baseLoaders.enrollments,
  plates: baseLoaders.plates,
  metro: baseLoaders.metro,
};
