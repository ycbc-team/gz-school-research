const { primaryTier1, middleTier1, shared } = require('../../utils/data.js');

// conclusion 中文值 → WXSS 合法类名（WXSS 类选择器不支持中文）
const CONCLUSION_CLASS = { 有支撑: 'supported', 部分支撑: 'partial', 不支撑: 'unsupported' };
/** tier1 数据为 { districts: { 区: { schools: [...] } } }，拍平为口碑校数组 */
function flattenTier1(t) {
  return Object.values((t && t.districts) || {}).flatMap((d) => (d && d.schools) || []);
}

Page({
  data: {
    stage: 'primary',
    list: [],
    summary: '',
    primaryCount: flattenTier1(primaryTier1).length,
    middleCount: flattenTier1(middleTier1).length,
  },
  onLoad() {
    this.apply('primary');
  },
  apply(stage) {
    const source = stage === 'primary' ? flattenTier1(primaryTier1) : flattenTier1(middleTier1);
    const by = { 有支撑: 0, 部分支撑: 0, 不支撑: 0 };
    const list = source.map((s) => ({
      ...s,
      badgeClass: CONCLUSION_CLASS[s.conclusion] || 'unknown',
    }));
    list.forEach((s) => {
      if (by[s.conclusion] !== undefined) by[s.conclusion] += 1;
    });
    this.setData({
      stage,
      list,
      summary: `有支撑 ${by['有支撑']} · 部分支撑 ${by['部分支撑']} · 不支撑 ${by['不支撑']}`,
    });
  },
  switchStage(e) {
    this.apply(e.currentTarget.dataset.stage);
  },
});
