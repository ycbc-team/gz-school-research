/**
 * 学校页（底部第 2 tab）· 小学 / 初中 / 高中 分段。
 * 实现 UI 稿 12 / 12A / 12B / 12B-A / 12B-B / 12C / 12C-A / 12C-B 与对应 PRD。
 * 数据：小学 / 高中用主包数据（entities · buildHighRankingGroups）；初中用主包本地数据 pages/school/data（同步 require）跑移植的 RankingView。
 */
const data = require('../../utils/data.js');
const { shared, repository, baseLoaders, plates, metro } = data;
const civilized = require('./civilized_campus_school_ids.js');
const middleRanking = require('./middle-ranking.js');

const DISTRICTS = shared.DISTRICTS;
const districtByAdcode = shared.districtByAdcode;

const CIVILIZED_LABEL = {
  national: '全国文明校园', provincial: '广东省文明校园',
  municipal: '广州市文明校园', advanced: '创建先进学校（储备）', other: '其他',
};

const CIVILIZED_ORDER = ['national', 'provincial', 'municipal', 'advanced'];
const HONOR_BY_SCHOOL = (() => {
  const m = new Map();
  for (const [key, ids] of Object.entries(civilized)) {
    for (const id of ids) { if (!m.has(id)) m.set(id, []); m.get(id).push(key); }
  }
  return m;
})();

// 各筛选项「值→展示文案」映射（用于筛选胶囊单选/多选时回显文案）
const METRIC_LABEL = {
  default: '默认', qu_ratio: '区属指标比例', sheng_ratio: '省市属指标比例',
  sheng_min: '省市属指标最低分', qu_min: '区属指标最低分', top14_min: 'TOP14指标最低分', tekong: '指标×高中特控率',
};
const SCHOOL_FILTER_LABEL = {
  'province-municipal-demo': '省市属示范',
  'district-demo:荔湾': '荔湾属示范', 'district-demo:越秀': '越秀属示范',
  'district-demo:海珠': '海珠属示范', 'district-demo:天河': '天河属示范',
  'district-demo:白云': '白云属示范', 'district-demo:黄埔': '黄埔属示范',
  'district-demo:番禺': '番禺属示范',
  'normal-public': '普通公办高中', 'private': '民办高中',
};
const SORT_LABEL = { score2025: '按 2025 分排', score2026: '按 2026 分排', average: '按全部年份平均分排' };

function highScoreText(arr) {
  if (arr && arr.length && arr[0].text) return arr[0].text;
  return '—';
}
function highCivilizedMatch(schoolId, sel) {
  if (sel === 'all') return true;
  const hits = HONOR_BY_SCHOOL.get(schoolId) || [];
  if (sel.indexOf('other') >= 0 && hits.length === 0) return true;
  return hits.some((k) => sel.indexOf(k) >= 0);
}
function highMatchFilter(row, token) {
  if (token === 'province-municipal-demo') return row.category === '省市属示范' && (row.affiliation === '省属' || row.affiliation === '市属');
  if (token === 'normal-public') return row.category === '普通高中' && !row.minban;
  if (token === 'private') return !!row.minban;
  if (token.indexOf('district-demo:') === 0) {
    const d = token.slice('district-demo:'.length);
    return row.category === '区属示范' && row.affiliation === d;
  }
  return false;
}

Page({
  data: {
    statusBarHeight: 20,
    topcoverH: 60,
    stage: 'p',
    chips: [],
    columns: [],
    groups: [],
    showScroll: false,
    scrHintOff: false,  // 横滑提示：用户滑动一次后消失（UI 12B-B）
    middleLoading: false,
    middleError: false,
    emptyOn: false,
    panel: '',          // '' | region | civilized | mech | metric | schoolFilter | sort
    headH: 0,           // 头部高度（px，onReady 实测），用于列表 padding-top 与区头 sticky
    gridCols: '',       // 当前表格 grid-template-columns
    // 区域：单层级行政区多选（平铺 7 区，交互同校园荣誉）
    regionOpts: [],
    // 多选/单选面板选项
    civilizedOpts: [],
    mechOpts: [],
    metricOpts: [],
    schoolFilterOpts: [],
    sortOpts: [],
  },

  onLoad() {
    this.initNavMetrics();
    // 筛选状态（按学段各一份，已应用维度独立保留；区域也按学段各自记忆，互不串台）
    this.regions = {
      p: { selectedDistricts: [] },
      m: { selectedDistricts: [] },
      h: { selectedDistricts: [] },
    };
    this.pFilters = { civilized: 'all' };
    this.mFilters = { civilized: 'all', mech: 'all', metric: 'default' };
    this.hFilters = { civilized: 'all', schoolFilter: 'all', sortBy: 'score2026' };
    this.locatedDistrict = '';
    this._middleLoaded = false;
    this._middleLoading = false;
    this.tryLocate();
    this.buildChips();
    this.renderGroups();
    this.loadMiddleData();
  },

  onShow() {
    const tab = this.getTabBar && this.getTabBar();
    if (tab) tab.setData({ selected: 1 });
  },

  onReady() {
    // 实测头部高度（含状态栏占位 + 品牌 + 学段 + 筛选栏），用于列表 padding-top 与区头 sticky
    try {
      wx.createSelectorQuery().in(this).select('.headbar').boundingClientRect((r) => {
        if (r && r.height) this.setData({ headH: r.height });
      }).exec();
    } catch (e) {}
  },

  /* ---------- 自定义导航适配（同首页） ---------- */
  initNavMetrics() {
    try {
      const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      const statusBarHeight = win.statusBarHeight || 20;
      let padTop = statusBarHeight;
      if (typeof wx.getMenuButtonBoundingClientRect === 'function') {
        const cap = wx.getMenuButtonBoundingClientRect();
        if (cap && cap.height) padTop = cap.top;
      }
      this.setData({ statusBarHeight: padTop, topcoverH: padTop + 40 });
    } catch (e) { /* 保底默认值 */ }
  },

  // 已授权则取定位点所属区，用于区排序定位置顶
  tryLocate() {
    try {
      wx.getSetting({
        success: (res) => {
          if (res.authSetting['scope.userLocation']) {
            wx.getLocation({
              type: 'gcj02',
              success: (r) => {
                // 简单取最近点位所属区
                const pts = (data.mapPoints || []);
                let best = null, bestD = Infinity;
                for (const p of pts) {
                  const d = (p.lat - r.latitude) ** 2 + (p.lng - r.longitude) ** 2;
                  if (d < bestD) { bestD = d; best = p; }
                }
                if (best && best.adcode) this.locatedDistrict = (districtByAdcode[best.adcode] || '').replace('区', '');
                if (this.data.stage) this.renderGroups();
              },
              fail: () => {},
            });
          }
        },
      });
    } catch (e) {}
  },

  /* ---------- 学段切换 ---------- */
  onStageTap(e) {
    const stage = e.currentTarget.dataset.stage; // p | m | h
    if (stage === this.data.stage) return;
    this.setData({ stage });
    this.closePanel();
    this.buildChips();
    this.renderGroups();
    if (stage === 'm' && !this._middleLoaded) this.loadMiddleData();
  },

  // 当前学段对应的区域筛选（各学段独立记忆）
  curRegion() {
    return this.regions[this.data.stage] || this.regions.p;
  },

  // 筛选胶囊显示状态：单选/多选维度，仅选中 1 项时回显该项文案；选中多项或默认态回显维度名
  // （胶囊本身底色/字体始终不变，激活态仅由文案体现）
  dimState(key) {
    const stage = this.data.stage;
    if (key === 'region') {
      const sel = this.curRegion().selectedDistricts;
      if (sel.length === 1) {
        const d = DISTRICTS.find((x) => x.adcode === sel[0]);
        return { label: d ? d.name : '区域', on: true };
      }
      return { label: '区域', on: sel.length > 0 };
    }
    if (key === 'civilized') {
      const sel = this.stageCivilized();
      const arr = (sel === 'all' || !sel) ? [] : sel;
      if (arr.length === 1) return { label: CIVILIZED_LABEL[arr[0]] || arr[0], on: true };
      return { label: '校园荣誉', on: arr.length > 0 };
    }
    if (key === 'mech') {
      const sel = this.mFilters.mech === 'all' ? [] : this.mFilters.mech;
      if (sel.length === 1) {
        const m = this.mechLabelMap || {};
        return { label: (m[sel[0]] && m[sel[0]].label) || sel[0], on: true };
      }
      return { label: '招生机制', on: sel.length > 0 };
    }
    if (key === 'metric') {
      const v = this.mFilters.metric;
      if (v === 'default') return { label: '指标', on: false };
      return { label: METRIC_LABEL[v] || v, on: true };
    }
    if (key === 'schoolFilter') {
      const sel = this.hFilters.schoolFilter === 'all' ? [] : this.hFilters.schoolFilter;
      if (sel.length === 1) return { label: SCHOOL_FILTER_LABEL[sel[0]] || sel[0], on: true };
      return { label: '学校分类', on: sel.length > 0 };
    }
    if (key === 'sort') {
      const v = this.hFilters.sortBy;
      if (v === 'score2026') return { label: '排序', on: false };
      return { label: SORT_LABEL[v] || v, on: true };
    }
    return { label: key, on: false };
  },

  buildChips() {
    const stage = this.data.stage;
    const chips = [{ key: 'region', ...this.dimState('region') }];
    if (stage === 'p') {
      chips.push({ key: 'civilized', ...this.dimState('civilized') });
    } else if (stage === 'm') {
      chips.push({ key: 'civilized', ...this.dimState('civilized') });
      chips.push({ key: 'mech', ...this.dimState('mech') });
      chips.push({ key: 'metric', ...this.dimState('metric') });
    } else {
      chips.push({ key: 'civilized', ...this.dimState('civilized') });
      chips.push({ key: 'schoolFilter', ...this.dimState('schoolFilter') });
      chips.push({ key: 'sort', ...this.dimState('sort') });
    }
    this.setData({ chips });
  },

  // 最低分横滑：首次滑动后隐藏提示（UI 12B-B）
  onXScroll() {
    if (this._xScrolled) return;
    this._xScrolled = true;
    this.setData({ scrHintOff: true });
  },

  /* ---------- 列表构建 ---------- */
  renderGroups() {
    this.buildChips();   // 筛选变动后即时刷新胶囊文案（单选回显值/多选回显维度名）
    const stage = this.data.stage;
    let columns = [], groups = [], showScroll = false, middleLoading = false, gridCols = '';
    if (stage === 'p') {
      columns = ['校园荣誉'];
      groups = this.buildPrimaryGroups();
      gridCols = 'minmax(0,1fr) 208rpx';   /* UI .sq：荣誉列 104px */
    } else if (stage === 'h') {
      columns = ['2025录取线', '2026录取线'];
      groups = this.buildHighGroups();
      gridCols = 'minmax(0,1fr) 176rpx 176rpx';   /* UI .mq4：88px×2 */
    } else {
      if (!this._middleLoaded) {
        middleLoading = this._middleLoading;
        columns = [];
        groups = [];
      } else {
        const r = middleRanking.buildMiddleGroups(this.middleLoaders, {
          metric: this.mFilters.metric,
          selectedDistricts: this.curRegion().selectedDistricts,
          selectedCivilized: this.mFilters.civilized,
          selectedMechs: this.mFilters.mech,
          locatedDistrict: this.locatedDistrict,
        });
        columns = r.columns;
        groups = r.groups;
        showScroll = (this.mFilters.metric === 'sheng_min' || this.mFilters.metric === 'qu_min' || this.mFilters.metric === 'top14_min');
        gridCols = showScroll
          ? '320rpx 120rpx 168rpx 88rpx 108rpx'   /* UI .mq5：160/60/84/44/54px，内容总宽 852rpx */
          : 'minmax(0,1fr) 208rpx 152rpx';        /* UI .mq3：104px/76px */
      }
    }
    this.setData({ columns, groups, showScroll, middleLoading, gridCols, emptyOn: !middleLoading && groups.length === 0 });
  },

  // 小学：实体按区归类 + 校园荣誉多行（仅展示右侧校园荣誉列非空的学校；校园荣誉筛选只保留命中档）
  buildPrimaryGroups() {
    const entities = (baseLoaders.entities && baseLoaders.entities.entities) || [];
    const selDist = this.curRegion().selectedDistricts;
    const civSel = this.pFilters.civilized;
    const civArr = (civSel === 'all' || !civSel) ? [] : civSel;
    const seen = new Set();
    const rows = [];
    for (const e of entities) {
      if (e.stage !== 'primary' || !e.school_id || seen.has(e.school_id)) continue;
      seen.add(e.school_id);
      const adcode = e.school_id.slice(3, 9);
      if (!districtByAdcode[adcode]) continue;
      if (selDist.length && selDist.indexOf(adcode) < 0) continue;
      const hits = HONOR_BY_SCHOOL.get(e.school_id) || [];
      const allKeys = CIVILIZED_ORDER.filter((h) => hits.indexOf(h) >= 0);
      // 仅展示右侧「校园荣誉」列非空的学校（空值学校不展示）
      if (allKeys.length === 0) continue;
      // 校园荣誉筛选：只保留命中所选档的行；学校未命中任何所选档则不展示
      const shownKeys = civArr.length ? allKeys.filter((h) => civArr.indexOf(h) >= 0) : allKeys;
      if (shownKeys.length === 0) continue;
      rows.push({ schoolId: e.school_id, name: e.name, adcode, honors: shownKeys.map((h) => CIVILIZED_LABEL[h]) });
    }
    const map = new Map();
    for (const r of rows) {
      const k = districtByAdcode[r.adcode];
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(r);
    }
    const orderIndex = (d) => {
      if (this.locatedDistrict && d.replace('区', '') === this.locatedDistrict) return -1;
      const i = DISTRICTS.findIndex((x) => x.name.replace('区', '') === d.replace('区', ''));
      return i < 0 ? 99 : i;
    };
    const keys = [...map.keys()].sort((a, b) => orderIndex(a) - orderIndex(b));
    return keys.map((k) => {
      const items = map.get(k).slice().sort((a, b) => a.name.localeCompare(b.name, 'zh'));
      const expanded = [];
      for (const it of items) {
        it.honors.forEach((h, i) => expanded.push({
          school: i === 0 ? it.name : '', navId: i === 0 ? it.schoolId : null, navName: i === 0 ? it.name : '',
          showSchool: i === 0, cells: [h],
        }));
      }
      return { district: k, title: k, items: expanded };
    });
  },

  // 高中：buildHighRankingGroups + 区域 / 校园荣誉 / 学校分类 过滤 + 排序
  buildHighGroups() {
    const sortBy = this.hFilters.sortBy || 'score2026';
    const all = shared.buildHighRankingGroups(baseLoaders, { groupBy: 'district', sortBy });
    const selDist = this.curRegion().selectedDistricts;
    const civ = this.hFilters.civilized;
    const sf = this.hFilters.schoolFilter;
    const out = [];
    for (const g of all) {
      let items = g.items;
      if (selDist.length) items = items.filter((it) => selDist.indexOf(it.adcode) >= 0);
      if (civ !== 'all') items = items.filter((it) => highCivilizedMatch(it.schoolId, civ));
      if (sf !== 'all') items = items.filter((it) => sf.some((t) => highMatchFilter(it, t)));
      if (!items.length) continue;
      out.push({
        district: g.title, title: g.title,
        items: items.map((it) => ({
          school: it.displayName, navId: it.schoolId, navName: it.name, showSchool: true, minban: false,
          cells: [highScoreText(it.score2025), highScoreText(it.score2026)],
        })),
      });
    }
    // 已开定位且未筛区域：定位区置顶（与小学/初中一致）
    if (this.locatedDistrict && !selDist.length) {
      const idx = out.findIndex((g) => (g.title || '').replace('区', '') === this.locatedDistrict);
      if (idx > 0) { const [g] = out.splice(idx, 1); out.unshift(g); }
    }
    return out;
  },

  /* ---------- 初中数据（主包本地同步加载，已编译进 pages/school/data，无需跨包 require.async） ---------- */
  loadMiddleData() {
    if (this._middleLoaded) return;
    try {
      const rm = require('./data/linkage/ranking_middle');
      const qm = require('./data/linkage/quota_matrix');
      const qo = require('./data/linkage/quota_outcome');
      const me = require('./data/middle/enrollment/dist/middle_enrollment_2026');
      const meH = shared.hydrate(me);
      this.middleLoaders = {
        rankingMiddle: shared.hydrate(rm),
        quotaMatrix: shared.hydrate(qm),
        quotaOutcome: shared.hydrate(qo),
        middleEnrollments: Object.values(meH.districts || {}).map((d) => ({ records: d.records || [] })),
        middleEnrollmentMechanisms: meH.mechanisms || {},
        entities: baseLoaders.entities,
        civilizedCampusSchoolIds: civilized,
      };
      this.mechLabelMap = this.middleLoaders.middleEnrollmentMechanisms || {};
      this._middleLoaded = true;
      this.setData({ middleError: false });
      if (this.data.stage === 'm') this.renderGroups();
    } catch (e) {
      console.warn('[school] 初中数据加载失败', e);
      this.setData({ middleError: true });
    }
  },
  // 数据获取失败后可重试（兜底，同步加载通常无需重试）
  retryMiddle() {
    this._middleLoaded = false;
    this.setData({ middleError: false });
    this.loadMiddleData();
  },

  /* ---------- 筛选胶囊入口 ---------- */
  onChipTap(e) {
    const dim = e.currentTarget.dataset.dim;
    if (dim === 'region') {
      if (this.data.panel === 'region') { this.closePanel(); return; }
      this.openRegionPanel();
      return;
    }
    if (this.data.panel === dim) { this.closePanel(); return; }
    this.openSelectPanel(dim);
  },

  openSelectPanel(dim) {
    const data = {};
    if (dim === 'civilized') data.civilizedOpts = this.buildCivilizedOpts();
    else if (dim === 'mech') data.mechOpts = this.buildMechOpts();
    else if (dim === 'metric') data.metricOpts = this.buildMetricOpts();
    else if (dim === 'schoolFilter') data.schoolFilterOpts = this.buildSchoolFilterOpts();
    else if (dim === 'sort') data.sortOpts = this.buildSortOpts();
    this.setData(Object.assign({ panel: dim }, data));
  },

  closePanel() {
    this.setData({ panel: '' });
    this.buildChips();
  },

  // 多选面板「全不选」：按当前面板分发
  clearDim() {
    const p = this.data.panel;
    if (p === 'civilized') this.clearCivilized();
    else if (p === 'mech') this.clearMech();
    else if (p === 'region') this.clearRegion();
    else if (p === 'schoolFilter') this.clearSchoolFilter();
  },

  // 空状态「重置筛选」：清空全部筛选维度（区域 + 当前学段筛选），关闭面板
  resetAllFilters() {
    this.curRegion().selectedDistricts = [];
    if (this.data.stage === 'p') this.pFilters = { civilized: 'all' };
    else if (this.data.stage === 'm') this.mFilters = { civilized: 'all', mech: 'all', metric: 'default' };
    else this.hFilters = { civilized: 'all', schoolFilter: 'all', sortBy: 'score2026' };
    this.setData({ panel: '' });
    this.buildChips();
    this.renderGroups();
  },

  /* ---------- 校园荣誉面板（多选） ---------- */
  buildCivilizedOpts() {
    const opts = [
      ['national', '全国文明校园'], ['provincial', '广东省文明校园'],
      ['municipal', '广州市文明校园'], ['advanced', '创建先进学校（储备）'],
    ];
    if (this.data.stage !== 'p') opts.push(['other', '其他']);
    const sel = this.stageCivilized();
    return opts.map(([k, l]) => ({ key: k, label: l, on: sel === 'all' || sel.indexOf(k) >= 0 }));
  },
  stageCivilized() {
    const s = this.data.stage;
    return s === 'p' ? this.pFilters.civilized : s === 'm' ? this.mFilters.civilized : this.hFilters.civilized;
  },
  toggleCivilized(e) {
    const key = e.currentTarget.dataset.key;
    let sel = this.stageCivilized();
    if (sel === 'all') sel = CIVILIZED_ORDER.concat(this.data.stage !== 'p' ? ['other'] : []);
    const i = sel.indexOf(key);
    if (i >= 0) sel.splice(i, 1); else sel.push(key);
    this.setCivilized(sel);
    this.setData({ civilizedOpts: this.buildCivilizedOpts() });
    this.renderGroups();
  },
  setCivilized(sel) {
    if (this.data.stage === 'p') this.pFilters.civilized = sel;
    else if (this.data.stage === 'm') this.mFilters.civilized = sel;
    else this.hFilters.civilized = sel;
  },
  clearCivilized() {
    this.setCivilized([]);
    this.setData({ civilizedOpts: this.buildCivilizedOpts() });
    this.renderGroups();
  },

  /* ---------- 招生机制面板（初中多选） ---------- */
  buildMechOpts() {
    const m = this.mechLabelMap || {};
    return middleRanking.MECH_FILTER_ORDER.map((mech) => ({
      key: mech, label: (m[mech] && m[mech].label) || mech,
      on: this.mFilters.mech === 'all' || this.mFilters.mech.indexOf(mech) >= 0,
    }));
  },
  toggleMech(e) {
    const key = e.currentTarget.dataset.key;
    let sel = this.mFilters.mech;
    if (sel === 'all') sel = middleRanking.MECH_FILTER_ORDER.slice();
    const i = sel.indexOf(key);
    if (i >= 0) sel.splice(i, 1); else sel.push(key);
    this.mFilters.mech = sel;
    this.setData({ mechOpts: this.buildMechOpts() });
    this.renderGroups();
  },
  clearMech() { this.mFilters.mech = []; this.setData({ mechOpts: this.buildMechOpts() }); this.renderGroups(); },

  /* ---------- 指标面板（初中单选，驱动表头） ---------- */
  buildMetricOpts() {
    const GROUPS = [
      { title: '综合排序', items: [{ v: 'default', l: '默认' }] },
      {
        title: '指标到校', items: [
          { v: 'qu_ratio', l: '区属指标比例' }, { v: 'sheng_ratio', l: '省市属指标比例' },
          { v: 'sheng_min', l: '省市属指标最低分' }, { v: 'qu_min', l: '区属指标最低分' },
          { v: 'top14_min', l: 'TOP14指标最低分' },
        ],
      },
      { title: '升学出口质量', items: [{ v: 'tekong', l: '指标×高中特控率' }] },
    ];
    return GROUPS.map((g) => ({
      title: g.title,
      items: g.items.map((it) => ({ v: it.v, label: it.l, on: this.mFilters.metric === it.v })),
    }));
  },
  selectMetric(e) {
    const v = e.currentTarget.dataset.v;
    this.mFilters.metric = v;
    this.setData({ metricOpts: this.buildMetricOpts() });
    this.renderGroups();
  },

  /* ---------- 学校分类面板（高中多选） ---------- */
  buildSchoolFilterOpts() {
    const tokens = [
      ['province-municipal-demo', '省市属示范'],
      ['district-demo:荔湾', '荔湾属示范'], ['district-demo:越秀', '越秀属示范'],
      ['district-demo:海珠', '海珠属示范'], ['district-demo:天河', '天河属示范'],
      ['district-demo:白云', '白云属示范'], ['district-demo:黄埔', '黄埔属示范'],
      ['district-demo:番禺', '番禺属示范'],
      ['normal-public', '普通公办高中'], ['private', '民办高中'],
    ];
    const sel = this.hFilters.schoolFilter;
    return tokens.map(([v, l]) => ({ v, label: l, on: sel === 'all' || sel.indexOf(v) >= 0 }));
  },
  toggleSchoolFilter(e) {
    const v = e.currentTarget.dataset.v;
    let sel = this.hFilters.schoolFilter;
    if (sel === 'all') sel = ['province-municipal-demo', 'district-demo:荔湾', 'district-demo:越秀', 'district-demo:海珠', 'district-demo:天河', 'district-demo:白云', 'district-demo:黄埔', 'district-demo:番禺', 'normal-public', 'private'];
    const i = sel.indexOf(v);
    if (i >= 0) sel.splice(i, 1); else sel.push(v);
    this.hFilters.schoolFilter = sel;
    this.setData({ schoolFilterOpts: this.buildSchoolFilterOpts() });
    this.renderGroups();
  },
  clearSchoolFilter() { this.hFilters.schoolFilter = []; this.setData({ schoolFilterOpts: this.buildSchoolFilterOpts() }); this.renderGroups(); },

  /* ---------- 排序面板（高中单选） ---------- */
  buildSortOpts() {
    const items = [
      { v: 'score2025', l: '按 2025 分排' }, { v: 'score2026', l: '按 2026 分排' }, { v: 'average', l: '按全部年份平均分排' },
    ];
    return items.map((it) => ({ v: it.v, label: it.l, on: this.hFilters.sortBy === it.v }));
  },
  selectSort(e) {
    const v = e.currentTarget.dataset.v;
    this.hFilters.sortBy = v;
    this.setData({ sortOpts: this.buildSortOpts() });
    this.renderGroups();
  },

  /* ---------- 区域筛选（单层级行政区多选；平铺 7 区，交互同校园荣誉：点选即时应用、全不选、完成） ---------- */
  openRegionPanel() {
    this.setData({ panel: 'region', regionOpts: this.buildRegionOpts() });
  },
  buildRegionOpts() {
    const sel = this.curRegion().selectedDistricts;
    return DISTRICTS.map((d) => ({
      adcode: d.adcode, name: d.name,
      on: sel.indexOf(d.adcode) >= 0,
    }));
  },
  toggleRegion(e) {
    const adcode = e.currentTarget.dataset.adcode;
    const sel = this.curRegion().selectedDistricts;
    const i = sel.indexOf(adcode);
    if (i >= 0) sel.splice(i, 1); else sel.push(adcode);
    this.setData({ regionOpts: this.buildRegionOpts() });
    this.renderGroups();
  },
  clearRegion() {
    this.curRegion().selectedDistricts = [];
    this.setData({ regionOpts: this.buildRegionOpts() });
    this.renderGroups();
  },

  /* ---------- 点校名 → 详情页 ---------- */
  onSchoolTap(e) {
    const { id, name } = e.currentTarget.dataset;
    if (!id && !name) return;
    const stageMap = { p: 'primary', m: 'middle', h: 'high' };
    const stage = stageMap[this.data.stage];
    wx.navigateTo({
      url: `/pages/school-detail/index?name=${encodeURIComponent(name || '')}&stage=${stage}&id=${encodeURIComponent(id || '')}`,
    });
  },

  noop() {},
});
