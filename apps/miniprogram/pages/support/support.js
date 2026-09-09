const { tier1Schools, middleTier1Schools, shared } = require('../../utils/data.js');

// conclusion 中文值 → WXSS 合法类名（WXSS 类选择器不支持中文）
const CONCLUSION_CLASS = { 有支撑: 'supported', 部分支撑: 'partial', 不支撑: 'unsupported' };

Page({
  data: {
    stage: 'primary',
    list: [],
    summary: '',
    primaryCount: tier1Schools.length,
    middleCount: middleTier1Schools.length,
  },
  onLoad() {
    this.apply('primary');
  },
  apply(stage) {
    const source = stage === 'primary' ? tier1Schools : middleTier1Schools;
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
