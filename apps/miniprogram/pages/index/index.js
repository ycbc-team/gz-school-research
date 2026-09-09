const { primarySchools, middleSchools, highSchools, tier1Schools, middleTier1Schools, shared } = require('../../utils/data.js');

Page({
  data: {
    stats: [],
  },
  onLoad() {
    const { summarizeSchools } = shared;
    const primarySum = summarizeSchools(primarySchools.schools);
    const middleSum = summarizeSchools(middleSchools.schools);
    const highSum = summarizeSchools(highSchools.schools);
    this.setData({
      stats: [
        { label: '小学点位', value: primarySum.total, sub: this.top3(primarySum.byDistrict) },
        { label: '初中点位', value: middleSum.total, sub: this.top3(middleSum.byDistrict) },
        { label: '高中点位', value: highSum.total, sub: this.top3(highSum.byDistrict) },
        { label: '口碑核验', value: tier1Schools.length + middleTier1Schools.length, sub: `小学 ${tier1Schools.length} · 初中 ${middleTier1Schools.length}` },
      ],
    });
  },
  top3(by) {
    return by.slice(0, 3).map((d) => `${d.name} ${d.count}`).join(' · ');
  },
  goMap() { wx.navigateTo({ url: '/pages/map/map' }); },
  goSupport() { wx.navigateTo({ url: '/pages/support/support' }); },
});
