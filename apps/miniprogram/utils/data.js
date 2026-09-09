/**
 * 小程序数据加载：shared 逻辑（@gz/shared cjs 构建产物）+ data JSON（由 scripts/miniprogram/build.mjs
 * 从项目根 data/ 唯一真源生成 .js 模块）。构建产物勿手改。
 */
const shared = require('../shared/index.js');

const primarySchools = require('../data/primary/schools-gz.js');
const primaryTier1 = require('../data/primary/tier1_schools_all.js');
const middleSchools = require('../data/middle/schools-gz.js');
const middleTier1 = require('../data/middle/tier1_schools_all.js');
const highSchools = require('../data/high/schools-gz.js');
const highLevels = require('../data/high/levels.js');

function tier1Flat(snapshot) {
  return Object.values(snapshot.districts || {}).flatMap((d) => d.schools || []);
}

module.exports = {
  shared,
  primarySchools,
  primaryTier1,
  middleSchools,
  middleTier1,
  highSchools,
  highLevels,
  tier1Schools: tier1Flat(primaryTier1),
  middleTier1Schools: tier1Flat(middleTier1),
};
