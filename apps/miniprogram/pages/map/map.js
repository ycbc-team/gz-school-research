const { primarySchools, tier1Schools, shared } = require('../../utils/data.js');
const { GZ_DISTRICTS, filterSchools, matchTier1ByPoiName } = shared;

Page({
  data: {
    districts: [],
    selected: [],
    markers: [],
    info: '',
  },
  onLoad() {
    const districts = GZ_DISTRICTS.map((d) => ({
      ...d,
      active: false,
      count: primarySchools.schools.filter((s) => s.adcode === d.adcode).length,
    }));
    this.setData({ districts });
    this.render();
  },
  render() {
    const list = filterSchools(primarySchools.schools, { adcodes: this.data.selected });
    const markers = list.map((s, i) => {
      const hit = matchTier1ByPoiName(s.name, tier1Schools);
      return {
        id: i,
        latitude: s.lat,
        longitude: s.lng,
        title: hit ? `${s.name}（${hit.conclusion}）` : s.name,
        width: 18,
        height: 18,
      };
    });
    this.setData({
      markers,
      info: `当前显示 ${list.length} 所小学${this.data.selected.length ? '（已按区筛选）' : '，点击下方区筛选'}`,
    });
  },
  toggle(e) {
    const adcode = e.currentTarget.dataset.adcode;
    const selected = this.data.selected.includes(adcode)
      ? this.data.selected.filter((a) => a !== adcode)
      : [...this.data.selected, adcode];
    const districts = this.data.districts.map((d) => ({
      ...d,
      active: selected.includes(d.adcode),
    }));
    this.setData({ selected, districts });
    this.render();
  },
});
