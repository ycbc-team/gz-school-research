/**
 * 小程序数据加载（与 Web apps/web/src/data/index.ts 同构）：
 * shared 逻辑（@gz/shared cjs 构建产物）+ data 紧凑模块（compact.mjs 从项目根 data/ 唯一真源编译，
 * 经 hydrate 还原为原 JSON 结构），组装 DataLoaders 注入 createRepository。
 * 构建产物勿手改。
 *
 * 主包 / 分包拆分（体积治理，详见 scripts/data/compact.mjs）：
 *   - 主包保留（地图首页 + 学校页同步消费）：POI / 高中分层(highLevels) / 实体注册表(entities) / 升学备注。
 *     highLevels 必须留主包：地图点位分学段（buildPoints 遍历 highLevels.schools）同步依赖。
 *   - 迁出主包 → pages/school-detail 分包（学校页 onLoad 经 require.async 拉取，app.js 合并进
 *     globalData.baseLoaders 供详情卡）：enrollments / xiaoshengchu / highScores2025/2026 / 初中 linkage / 初中招生计划。
 *     主包 baseLoaders 对迁出项保留兼容空壳，createRepository 不会因空数据崩溃（子 API 对空数组/空对象均有保护）。
 *   - 详情域空壳（brandGroups / educationGroups / quotaMatrix / specialMatrix / batch2Scores / districtQuota）：
 *     真实数据由分包 school-card 组件 require 分包模块提供，主包仅占位。
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

/** 主包 loaders（地图首页 + 学校页同步消费）。迁出项以兼容空壳占位，详情域亦为空壳。 */
const baseLoaders = {
  // —— 主包同步数据（真实） ——
  primarySchools: cast(hydrate(require('../data/poi/dist/primary_poi.js'))),
  middleSchools: cast(hydrate(require('../data/poi/dist/middle_poi.js'))),
  highSchools: cast(hydrate(require('../data/poi/dist/high_poi.js'))),
  // 高中分层：必须留主包（地图点位分学段同步依赖）
  highLevels: cast(hydrate(require('../data/high/level/src/levels.js'))),
  // 实体注册表：首页搜索 + 学校页默认展示同步依赖
  entities: cast(hydrate(require('../data/registry/entity/dist/entities.js'))),
  middleEnrollNotes: cast(hydrate(require('../data/primary/middle_enroll_notes.js'))),
  // 区域 / 地铁数据源（UI 04/04B 三列下钻）
  plates: cast(regionPlates),
  metro: cast(regionMetro),

  // —— 迁出主包 → 分包 school-detail（学校页 onLoad 经 require.async 拉取，app.js 合并进 globalData） ——
  // 空壳仅为占位，createRepository / 子 API 对空数组/空对象均有保护，不会崩溃。
  enrollments: [],                                  // EnrollmentSnapshot[] 空壳
  xiaoshengchu: { groups: [], records: [] },        // { groups, records } 空壳
  highScores2025: { by_school_id: {} },             // HighScores 空壳
  highScores2026: { by_school_id: {} },             // HighScores 空壳

  // —— 详情域空壳（品牌/教育集团/linkage 模块由分包 pages/school-detail 提供真实数据） ——
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
  plates: baseLoaders.plates,
  metro: baseLoaders.metro,
};
