const { tier1Schools, middleTier1Schools, shared } = require('../../utils/data.js');

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
    const list = stage === 'primary' ? tier1Schools : middleTier1Schools;
    const by = { 有支撑: 0, 部分支撑: 0, 不支撑: 0 };
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
