const { primarySchools, middleSchools, highSchools, primaryTier1, middleTier1, shared } = require('../../utils/data.js');
/** tier1 数据为 { districts: { 区: { schools: [...] } } }，拍平各区口碑校总数 */
function tier1Count(t) {
  return Object.values((t && t.districts) || {}).reduce((n, d) => n + ((d && d.schools) ? d.schools.length : 0), 0);
}

Page({
  data: {
    stats: [],
  },
  onLoad() {
    const { summarizeSchools } = shared;
    const primarySum = summarizeSchools(primarySchools.schools);
    const middleSum = summarizeSchools(middleSchools.schools);
    const highSum = summarizeSchools(highSchools.schools);
    const pT = tier1Count(primaryTier1);
    const mT = tier1Count(middleTier1);
    this.setData({
      stats: [
        { label: '小学点位', value: primarySum.total, sub: this.top3(primarySum.byDistrict) },
        { label: '初中点位', value: middleSum.total, sub: this.top3(middleSum.byDistrict) },
        { label: '高中点位', value: highSum.total, sub: this.top3(highSum.byDistrict) },
        { label: '口碑核验', value: pT + mT, sub: `小学 ${pT} · 初中 ${mT}` },
      ],
    });
  },
  top3(by) {
    return by.slice(0, 3).map((d) => `${d.name} ${d.count}`).join(' · ');
  },
  goMap() { wx.navigateTo({ url: '/pages/map/map' }); },
  goSupport() { wx.navigateTo({ url: '/pages/support/support' }); },
});
