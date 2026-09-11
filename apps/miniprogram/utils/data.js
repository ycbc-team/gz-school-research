/**
 * 小程序数据加载：shared 逻辑（@gz/shared cjs 构建产物）+ data 紧凑模块（由 scripts/data/compact.mjs
 * 从项目根 data/ 唯一真源编译，加载后经 hydrate 还原为原 JSON 结构）。构建产物勿手改。
 */
const shared = require('../shared/index.js');

const hydrate = shared.hydrate;
const primarySchools = hydrate(require('../data/primary/schools-gz.js'));
const primaryTier1 = hydrate(require('../data/primary/tier1_schools_all.js'));
const middleSchools = hydrate(require('../data/middle/schools-gz.js'));
const middleTier1 = hydrate(require('../data/middle/tier1_schools_all.js'));
const highSchools = hydrate(require('../data/high/schools-gz.js'));
const highLevels = hydrate(require('../data/high/levels.js'));

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
