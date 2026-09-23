/**
 * 首页（地图首页）· 知性蓝 UI 稿重构版。
 * 复用 @gz/shared 的筛选状态机 / 搜索 / 点位构建（shared 不变），
 * 仅实现首页自己的展示、搜索页、筛选半窗、底部悬浮导航与学校卡。
 * 地图页（pages/map）保持原样，本页为独立的新首页。
 */
const { shared, repository, mapPoints } = require('../../utils/data.js');
const {
  DISTRICTS, STAGE_TABS, SCHOOL_NATURE_TABS, STAGE_LABEL,
  districtByAdcode, initialFilterState, toggleDistrict, toggleStage, toggleGrade,
  toggleNature, isVisible, searchSchools,
} = shared;

const STAGE_KEY = { primary: 'p', middle: 'm', high: 'h' };
function markerIcon(stages, selected) {
  const key = stages.map((s) => STAGE_KEY[s]).join('');
  return `/assets/markers-index/marker-${key}${selected ? '-sel' : ''}.png`;
}

// 点位图标尺寸：常态 16 / 选中 22（UI 稿规范表「地图点位」）
const MARKER_OFF = 16;
const MARKER_ON = 22;
// 选中态名称气泡（白底圆角、下方小箭头）
// ⚠️ display 只能取 'BYCLICK' / 'ALWAYS'。写成 'BYALWAYS' 是非法值，
// 会被地图组件退化成「点击才显示」，表现为「搜索定位后点位上不显示校名」。
const CALLOUT_ON = {
  color: '#10182B', bgColor: '#FFFFFF', borderColor: '#E3E8F0',
  borderWidth: 1, borderRadius: 10, padding: 8, fontSize: 12,
  textAlign: 'center', display: 'ALWAYS',
};
// 选中点位 zIndex 置顶，避免被密集点位压住
const Z_ON = 100;
const Z_OFF = 1;
function markerItem(pt, id, on) {
  return {
    id,
    latitude: pt.lat,
    longitude: pt.lng,
    iconPath: markerIcon(pt.stages, on),
    width: on ? MARKER_ON : MARKER_OFF,
    height: on ? MARKER_ON : MARKER_OFF,
    anchor: { x: 0.5, y: 0.5 },
    zIndex: on ? Z_ON : Z_OFF,
    // 未选中：点击才显示校名；选中：常显校名气泡（UI 稿规范表「地图点位」+ 06B）
    callout: on ? { ...CALLOUT_ON, content: pt.name } : { content: pt.name, display: 'BYCLICK' },
  };
}
// 学段标签：多学段拆成多枚（按 小学 > 初中 > 高中 排序），不合并为一个「初中/高中」
function stageTags(stages) {
  return (stages || []).slice().sort((a, b) => STAGE_PRI[a] - STAGE_PRI[b]).map((s) => STAGE_LABEL[s]);
}

const HIST_KEY = 'gz_index_search_history';
const DIST_ORDER = {};
DISTRICTS.forEach((d, i) => { DIST_ORDER[d.adcode] = i; });
const STAGE_PRI = { primary: 0, middle: 1, high: 2 };

// 省市属示范高中推荐排序用：首字拼音首字母（覆盖数据中出现的字，确定性排序）
const PY = { 广: 'g', 东: 'd', 州: 'z', 省: 's', 实: 's', 验: 'y', 华: 'h', 南: 'n', 师: 's', 范: 'f', 大: 'd', 学: 'x', 附: 'f', 中: 'z', 第: 'd', 二: 'e', 六: 'l', 执: 'z', 信: 'x', 铁: 't', 一: 'y', 协: 'x', 和: 'h', 仲: 'z', 元: 'y', 真: 'z', 雅: 'y', 光: 'g', 培: 'p', 英: 'y', 育: 'y', 外: 'w', 国: 'g', 侨: 'q', 天: 't', 河: 'h', 清: 'q', 黄: 'h', 岗: 'g', 爱: 'a', 群: 'q', 贤: 'x', 正: 'z', 衡: 'h', 维: 'w', 为: 'w', 明: 'm', 邝: 'k', 体: 't', 艺: 'y', 曦: 'x', 市: 's', 属: 's', 湾: 'w', 语: 'y', 校: 'x', 区: 'q' };
function pykey(s) {
  let k = '';
  for (const ch of (s || '')) { if (k.length >= 6) break; const p = PY[ch]; if (p) k += p; }
  return k;
}

Page({
  data: {
    districts: [],
    SCHOOL_NATURE_TABS: [],
    markers: [],
    visibleCount: 0,
    activeMarkerId: null,
    menu: '',            // '' | 'district' | 'stage' | 'nature'
    // 筛选胶囊显示文案：单选显示选中内容，多选/未选显示维度名（UI 稿 筛选栏入口规则）
    // 注：胶囊不显示任何数量角标（UI 稿 01 帧修正）
    districtLabel: '行政区',
    stageLabel: '学段',
    natureLabel: '办学性质',
    // 半窗学段分组选中态
    stagePri: true, stageMid: true, hM: true, hD: true, hN: true,
    centerLat: 23.1150, centerLng: 113.3245, scale: 15,
    // 学校卡
    card: null,
    cardExpanded: false,
    // 筛选结果为空浮层（UI 稿异常态 C）
    filterEmpty: false,
    // 搜索页
    searchVisible: false,
    searchFocus: false,
    kw: '',
    assocs: [],
    history: [],
    recommends: [],
    // 自定义导航适配：状态栏高度 + 右上角胶囊避让（px）
    statusBarHeight: 20,
    // 搜索页头行 top（= 胶囊 top − (44 − 胶囊高)/2，使搜索框与胶囊垂直居中对齐）
    searchHeadTop: 20,
    searchHeadRight: 0,
    // 顶部白底常驻条高度（状态栏 + 小程序名行），UI 稿 .topcover
    topcoverH: 60,
  },

  onLoad() {
    this.initNavMetrics();
    this.setData({
      districts: DISTRICTS.map((d) => ({ name: d.name, adcode: d.adcode })),
      SCHOOL_NATURE_TABS,
    });
    this.draft = initialFilterState();
    this.syncState(this.draft);
    this.renderMarkers();
    this.recommends = this.buildRecommends();
    this.setData({ recommends: this.recommends.map((r) => ({ name: r.name })) });
  },

  onShow() {
    const tab = this.getTabBar && this.getTabBar();
    if (tab) {
      tab.setData({ selected: 0 });
      tab.setData({ hidden: !!(this.data.card || this.data.menu) });
    }
  },
  onHide() {
    const tab = this.getTabBar && this.getTabBar();
    if (tab) tab.setData({ hidden: false });
  },
  // 弹窗（详情卡 / 筛选半窗 / 搜索页）需覆盖底部导航栏：自定义 tabBar 是独立组件层，
  // 页面内 z-index 压不过它，故弹出时直接隐藏 tabBar，关闭时恢复。
  setTabBarHidden(hidden) {
    const tab = this.getTabBar && this.getTabBar();
    if (tab) tab.setData({ hidden: !!hidden });
  },

  onReady() {
    this.mapCtx = wx.createMapContext('gzmap', this);
  },

  /* ---------- 自定义导航适配 ---------- */
  initNavMetrics() {
    try {
      const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
      const statusBarHeight = win.statusBarHeight || 20;
      let padTop = statusBarHeight;
      let headTop = statusBarHeight;
      let padRight = 0;
      if (typeof wx.getMenuButtonBoundingClientRect === 'function') {
        const cap = wx.getMenuButtonBoundingClientRect();
        if (cap && cap.height) {
          // 首页小程序名行：与胶囊同行（顶对齐），整行 32px 与胶囊同高
          padTop = cap.top;
          // 搜索页头行 44px、搜索框 32px 垂直居中 → 头行 top 需上移 (44-32)/2 = 6px，
          // 才能使搜索框与胶囊「同行且同高齐平」（UI 稿规范表「小程序胶囊」行）
          headTop = Math.max(0, cap.top - (44 - cap.height) / 2);
          // 右侧安全位：内容右缘止于胶囊左缘，留 4px 间隙（UI 稿 375 画框下等价 padding-right:98px）
          if (win.windowWidth && cap.left) padRight = Math.max(0, win.windowWidth - cap.left + 4);
        }
      }
      this.setData({
        statusBarHeight: padTop,
        searchHeadTop: headTop,
        searchHeadRight: padRight,
        topcoverH: padTop + 40,
      });
    } catch (e) { /* 保底默认值 */ }
  },

  /* ---------- 状态机 ---------- */
  committedState() {
    const d = this.data;
    return {
      selectedDistricts: new Set(d.selectedDistricts),
      selectedStages: new Set(d.selectedStages),
      selectedGrades: new Set(d.selectedGrades),
      selectedNatures: new Set(d.selectedNatures),
    };
  },
  syncState(st) {
    const selD = st.selectedDistricts, selS = st.selectedStages, selG = st.selectedGrades, selN = st.selectedNatures;
    this.setData({
      selectedDistricts: [...selD],
      selectedStages: [...selS],
      selectedGrades: [...selG],
      selectedNatures: [...selN],
      districts: this.data.districts.map((d) => ({ ...d, checked: selD.has(d.adcode) })),
      SCHOOL_NATURE_TABS: this.data.SCHOOL_NATURE_TABS.map((o) => ({ ...o, checked: selN.has(o.v) })),
    });
    this.syncStageGroups(st);
    this.applyChipLabels();
  },
  syncStageGroups(st) {
    const selS = st.selectedStages, selG = st.selectedGrades;
    const stagePri = selS.has('primary') && selG.has('pN');
    const stageMid = selS.has('middle') && selG.has('mN');
    const hM = selS.has('high') && selG.has('hM');
    const hD = selS.has('high') && selG.has('hD');
    const hN = selS.has('high') && selG.has('hN');
    this.setData({ stagePri, stageMid, hM, hD, hN });
  },
  // 筛选胶囊标签：单选显示选中内容，多选/未选显示维度名（UI 稿 筛选栏入口规则）
  // 行政区固定显示全名（带「区」字），不做去字处理
  applyChipLabels() {
    const d = this.data;
    const dsel = d.districts.filter((x) => x.checked);
    const districtLabel = dsel.length === 1 ? dsel[0].name : '行政区';
    const nsel = d.SCHOOL_NATURE_TABS.filter((x) => x.checked);
    const natureLabel = nsel.length === 1 ? nsel[0].l : '办学性质';
    const groups = [['stagePri', '小学'], ['stageMid', '初中'], ['hM', '省市属示范'], ['hD', '区属示范'], ['hN', '其他学校']];
    const son = groups.filter(([k]) => d[k]).map(([, v]) => v);
    const stageLabel = son.length === 1 ? son[0] : '学段';
    this.setData({ districtLabel, stageLabel, natureLabel });
  },
  // 半窗草稿态同步到视图：选项勾选态 + 学段分组态（保证点选项即时高亮）
  syncDraftView() {
    const d = this.draft || this.committedState();
    const stagePri = d.selectedStages.has('primary') && d.selectedGrades.has('pN');
    const stageMid = d.selectedStages.has('middle') && d.selectedGrades.has('mN');
    const hM = d.selectedStages.has('high') && d.selectedGrades.has('hM');
    const hD = d.selectedStages.has('high') && d.selectedGrades.has('hD');
    const hN = d.selectedStages.has('high') && d.selectedGrades.has('hN');
    this.setData({
      districts: this.data.districts.map((x) => ({ ...x, checked: d.selectedDistricts.has(x.adcode) })),
      SCHOOL_NATURE_TABS: this.data.SCHOOL_NATURE_TABS.map((x) => ({ ...x, checked: d.selectedNatures.has(x.v) })),
      stagePri, stageMid, hM, hD, hN,
    });
    this.applyChipLabels();
  },

  renderMarkers() {
    this.visible = mapPoints.filter((p) => isVisible(this.committedState(), p));
    const active = this.data.activeMarkerId;
    const patch = {
      markers: this.visible.map((pt, i) => markerItem(pt, i, active === i)),
      visibleCount: this.visible.length,
    };
    if (active !== null && !this.visible[active]) { patch.card = null; patch.activeMarkerId = null; this.currentPt = null; }
    this.setData(patch);
  },

  // 选中态切换：只下发变化的那一两个点位（data 路径补丁），
  // 不再整份 markers（最多上千条）重复跨线程序列化 —— 否则每次点选/关卡片都会卡顿
  markerPatch(i, on) {
    const pt = this.visible[i];
    if (!pt || !this.data.markers[i]) return null;
    return {
      [`markers[${i}].iconPath`]: markerIcon(pt.stages, on),
      [`markers[${i}].width`]: on ? MARKER_ON : MARKER_OFF,
      [`markers[${i}].height`]: on ? MARKER_ON : MARKER_OFF,
      [`markers[${i}].zIndex`]: on ? Z_ON : Z_OFF,
      [`markers[${i}].callout`]: on ? { ...CALLOUT_ON, content: pt.name } : { content: pt.name, display: 'BYCLICK' },
    };
  },
  setActiveMarker(id) {
    const next = (id === undefined || id === null || id < 0) ? null : id;
    const prev = this.data.activeMarkerId;
    if (prev === next) return;
    const patch = { activeMarkerId: next };
    if (prev !== null) Object.assign(patch, this.markerPatch(prev, false) || {});
    if (next !== null) Object.assign(patch, this.markerPatch(next, true) || {});
    this.setData(patch);
  },

  /* ---------- 筛选半窗 ---------- */
  openSheet(e) {
    const dim = e.currentTarget.dataset.dim;
    if (this.data.menu === dim) { this.closeSheet(); return; }
    if (!this.data.menu) this.draft = this.committedState();
    this.setData({ menu: dim });
    this.syncDraftView();
    this.setTabBarHidden(true);
  },
  switchDim(e) {
    const dim = e.currentTarget.dataset.dim;
    if (this.data.menu === dim) { this.closeSheet(); return; }
    this.setData({ menu: dim });
    this.syncDraftView();
    this.setTabBarHidden(true);
  },
  closeSheet() { this.setData({ menu: '' }); this.draft = this.committedState(); this.syncDraftView(); this.applyChipLabels(); this.setTabBarHidden(false); },
  toggleDistrict(e) { this.draft = toggleDistrict(this.draft, e.currentTarget.dataset.adcode); this.syncDraftView(); },
  toggleStage(e) {
    const s = e.currentTarget.dataset.stage;
    let st = toggleStage(this.draft, s);
    st = toggleGrade(st, s === 'primary' ? 'pN' : s === 'middle' ? 'mN' : 'hN');
    this.draft = st; this.syncDraftView();
  },
  toggleGrade(e) {
    const g = e.currentTarget.dataset.grade;
    let st = toggleGrade(this.draft, g);
    const anyHigh = ['hM', 'hD', 'hN'].some((k) => st.selectedGrades.has(k));
    if (anyHigh && !st.selectedStages.has('high')) st = toggleStage(st, 'high');
    if (!anyHigh && st.selectedStages.has('high')) st = toggleStage(st, 'high');
    this.draft = st; this.syncDraftView();
  },
  toggleNature(e) {
    this.draft = toggleNature(this.draft, e.currentTarget.dataset.nature);
    this.syncDraftView();
  },
  clearDim() {
    const d = this.draft;
    if (this.data.menu === 'district') d.selectedDistricts = new Set();
    else if (this.data.menu === 'nature') d.selectedNatures = new Set();
    else if (this.data.menu === 'stage') {
      d.selectedStages = new Set();
      d.selectedGrades = new Set();
    }
    this.syncDraftView();
  },
  confirmSheet() {
    const prevD = (this.data.selectedDistricts || []).slice().sort().join(',');
    this.syncState(this.draft);
    this.renderMarkers();
    this.setData({ menu: '', filterEmpty: this.visible.length === 0 });
    // 行政区是「地理维度」：选区变化且收窄（非全选）时，把视野自动适配到筛选结果范围，
    // 否则会出现「人停在番禺、筛了荔湾、地图却不动」的错位（UI 稿 04 帧 / 规范表「筛选半窗」）。
    // 学段 / 办学性质是「属性维度」，不改变学校地理位置，故不移动相机。
    const nextD = (this.data.selectedDistricts || []).slice().sort().join(',');
    const narrowed = (this.data.selectedDistricts || []).length < DISTRICTS.length;
    if (this.visible.length && prevD !== nextD && narrowed) this.fitVisible();
  },

  /* ---------- 重置筛选（UI 稿异常态 A/C 主操作） ---------- */
  resetFilters() {
    this.draft = initialFilterState();
    this.syncState(this.draft);
    this.renderMarkers();
    this.setData({ filterEmpty: false });
  },
  // 搜索空态「清空并重新搜索」：清输入回默认态 + 重置全部筛选
  clearAndResearch() {
    this.resetFilters();
    this.setData({ kw: '', assocs: [], searchFocus: true });
  },

  /* ---------- 搜索页 ---------- */
  openSearch() {
    this.setData({ searchVisible: true, searchFocus: true, kw: '', assocs: [], history: this.loadHistory() });
    this.setTabBarHidden(true);
  },
  closeSearch() { this.setData({ searchVisible: false, searchFocus: false }); this.setTabBarHidden(!!(this.data.card || this.data.menu)); },
  onSearchInput(e) {
    const kw = e.detail.value;
    this.setData({ kw, assocs: kw ? this.buildAssocs(kw) : [] });
  },
  onSearchConfirm() {
    const kw = (this.data.kw || '').trim();
    if (!kw) return;
    this.saveHistory(kw);
    if (this.data.assocs.length) this.pickAssoc({ currentTarget: { dataset: { idx: 0 } } });
    // 无匹配时停留在搜索页，展示“未找到匹配的学校”空态（不自动关页）
  },
  tapHistory(e) {
    const kw = e.currentTarget.dataset.kw;
    this.setData({ kw, assocs: this.buildAssocs(kw), searchFocus: true });
  },
  tapRecommend(e) {
    const name = e.currentTarget.dataset.name;
    const r = this.recommends.find((x) => x.name === name);
    if (r) this.saveHistory(name);
    this.closeSearch();
    if (r) this.focusPoint(r.pt);
  },
  pickAssoc(e) {
    const pt = this.assocPts[e.currentTarget.dataset.idx];
    if (pt) this.saveHistory((this.data.kw || '').trim());
    this.closeSearch();
    if (pt) this.focusPoint(pt);
  },
  clearHistory() {
    wx.showModal({
      title: '提示', content: '确定一键清空历史词条吗', success: (res) => {
        if (res.confirm) { try { wx.removeStorageSync(HIST_KEY); } catch (e) {} this.setData({ history: [] }); }
      },
    });
  },
  loadHistory() { try { return wx.getStorageSync(HIST_KEY) || []; } catch (e) { return []; } },
  saveHistory(kw) {
    if (!kw) return;
    let list = this.loadHistory().filter((x) => x !== kw);
    list.unshift(kw);
    if (list.length > 10) list = list.slice(0, 10);
    try { wx.setStorageSync(HIST_KEY, list); } catch (e) {}
    this.setData({ history: list });
  },
  hasTier(pt) { return Object.values(pt.tierOf || {}).some(Boolean); },
  buildAssocs(kw) {
    const k = (kw || '').trim();
    if (!k) return [];
    const direct = mapPoints.filter((p) => (p.names || []).some((n) => n.includes(k)) || p.name.includes(k));
    const pool = direct.length ? direct : searchSchools(mapPoints, k, repository.entities.entities);
    const exact = (p) => (p.names || []).some((n) => n === k) || p.name === k;
    pool.sort((a, b) => {
      const ea = exact(a), eb = exact(b);
      if (ea !== eb) return ea ? -1 : 1;
      const da = DIST_ORDER[a.adcode] ?? 9, db = DIST_ORDER[b.adcode] ?? 9;
      if (da !== db) return da - db;
      const sa = STAGE_PRI[a.mainStage], sb = STAGE_PRI[b.mainStage];
      if (sa !== sb) return sa - sb;
      const ta = this.hasTier(a) ? 0 : 1, tb = this.hasTier(b) ? 0 : 1;
      if (ta !== tb) return ta - tb;
      return a.name.localeCompare(b.name);
    });
    this.assocPts = pool;
    return pool.slice(0, 20).map((p) => ({
      name: p.name,
      // 行政区固定带「区」字；多学段按学段拆成多枚标签（UI 稿 03 帧 + 规范表「标签」）
      district: districtByAdcode[p.adcode] || '',
      stages: stageTags(p.stages),
    }));
  },
  buildRecommends() {
    const seen = new Set(); const out = [];
    for (const p of mapPoints) {
      if (p.stages.includes('high') && p.clsOf && p.clsOf.high === 'hM') {
        const base = (p.rec && p.rec.name) || p.name;
        if (!seen.has(base)) { seen.add(base); out.push({ name: base, pt: p }); }
      }
    }
    out.sort((a, b) => pykey(a.name).localeCompare(pykey(b.name)) || a.name.localeCompare(b.name));
    return out;
  },

  /* ---------- 地图交互 ---------- */
  onMarkerTap(e) {
    const pt = this.visible[e.detail.markerId];
    if (!pt) return;
    this.ignoreNextMapTap = true;
    this.lastMarkerTapAt = Date.now();
    clearTimeout(this.ignoreMapTapTimer);
    this.ignoreMapTapTimer = setTimeout(() => { this.ignoreNextMapTap = false; }, 300);
    this.focusPoint(pt, e.detail.markerId);
  },
  focusPoint(pt, markerId) {
    if (!pt) return;
    this.currentPt = pt;
    this.showCard(pt);
    let id = (markerId === undefined || markerId === null) ? this.visible.indexOf(pt) : markerId;
    // 搜索命中的学校若被当前筛选条件过滤掉 → 恢复默认筛选，保证点位可见且呈选中态
    // （UI 稿 06B「地图自动定位并缩放至结果学校、该点位进入选中态」）
    if (id < 0) {
      this.draft = initialFilterState();
      this.syncState(this.draft);
      this.renderMarkers();
      id = this.visible.indexOf(pt);
    }
    this.setActiveMarker(id >= 0 ? id : null);
    this.zoomTo(pt);
  },
  // 相机定位：只用 mapCtx.includePoints 单向驱动，绝不回写 centerLat/centerLng。
  // 回写中心点会让「setData → 地图动画 → regionchange → setData」形成正反馈，
  // 表现为地图持续抖动、来回跳（搜索回到首页后的卡死现象即此）。
  // padding = [上, 右, 下, 左]（px）：底部留出半窗学校卡的高度。
  zoomTo(pt) {
    const target = { latitude: pt.lat, longitude: pt.lng };
    const token = (this.cameraToken || 0) + 1;
    this.cameraToken = token;
    const applyCenter = () => {
      if (this.cameraToken !== token) return;
      this.setData({ centerLat: target.latitude, centerLng: target.longitude, scale: 16 });
    };
    if (!this.mapCtx || typeof this.mapCtx.includePoints !== 'function') return applyCenter();
    const latDelta = 0.0016;
    const lngDelta = latDelta / Math.cos(target.latitude * Math.PI / 180);
    this.mapCtx.includePoints({
      points: [
        { latitude: target.latitude - latDelta, longitude: target.longitude - lngDelta },
        { latitude: target.latitude + latDelta, longitude: target.longitude + lngDelta },
      ],
      padding: [80, 60, 300, 60],
      fail: applyCenter,
    });
  },
  // 视野适配：把地图缩放到「恰好容纳当前全部可见点位」的范围（筛选确认后调用）。
  // 与 zoomTo 同一条铁律：只用 includePoints 单向驱动、绝不回写 center，
  // 否则程序化相机与回写互相触发，会重现地图持续抖动的问题。
  fitVisible() {
    const pts = this.visible || [];
    if (!pts.length) return;
    let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity;
    for (const p of pts) {
      if (p.lat < minLat) minLat = p.lat;
      if (p.lat > maxLat) maxLat = p.lat;
      if (p.lng < minLng) minLng = p.lng;
      if (p.lng > maxLng) maxLng = p.lng;
    }
    // 最小跨度兜底：单点 / 极窄范围时避免 includePoints 直接把地图放到最大级别
    const MIN_SPAN = 0.012; // ≈ 1.3km
    if (maxLat - minLat < MIN_SPAN) { const c = (minLat + maxLat) / 2; minLat = c - MIN_SPAN / 2; maxLat = c + MIN_SPAN / 2; }
    if (maxLng - minLng < MIN_SPAN) { const c = (minLng + maxLng) / 2; minLng = c - MIN_SPAN / 2; maxLng = c + MIN_SPAN / 2; }
    const token = (this.cameraToken || 0) + 1;
    this.cameraToken = token;
    const applyCenter = () => {
      if (this.cameraToken !== token) return;
      this.setData({ centerLat: (minLat + maxLat) / 2, centerLng: (minLng + maxLng) / 2 });
    };
    if (!this.mapCtx || typeof this.mapCtx.includePoints !== 'function') return applyCenter();
    this.mapCtx.includePoints({
      points: [
        { latitude: minLat, longitude: minLng },
        { latitude: maxLat, longitude: maxLng },
      ],
      // padding = [上, 右, 下, 左]：上避让小程序名行 + 搜索框 + 筛选栏；下避让图例 + 底部导航
      padding: [150, 70, 200, 70],
      fail: applyCenter,
    });
  },
  showCard(pt) {
    // UI 稿 06：半窗学校卡顶部 = 校名 + 行政区／学段／办学性质 标签
    // 行政区固定带「区」字；多学段拆成多枚学段标签（不写成「初中/高中」）
    const tags = [{ key: 'dist', cls: 'dist', text: districtByAdcode[pt.adcode] || '—' }];
    stageTags(pt.stages).forEach((t, i) => tags.push({ key: `stage${i}`, cls: 'stage', text: t }));
    const main = pt.mainStage;
    const nat = pt.natureOf[main] || 'public';
    tags.push({ key: 'nat', cls: 'nat', text: nat === 'private' ? '民办' : '公办' });
    this.setData({ card: { name: pt.name, tags }, cardExpanded: false });
    this.setTabBarHidden(true);
  },
  // 学校卡：25% ↔ 全屏 展开/收起（原型：上滑展开、下滑或返回收起、关闭按钮/点击地图外关闭）
  expandCard() { if (this.data.card) this.setData({ cardExpanded: true }); },
  collapseCard() { this.setData({ cardExpanded: false }); },
  onHandleTap() { if (this.data.cardExpanded) this.collapseCard(); else this.expandCard(); },
  cardTouchStart(e) { this._cy = e.touches[0].clientY; },
  cardTouchEnd(e) {
    if (this._cy == null) return;
    const dy = e.changedTouches[0].clientY - this._cy;
    this._cy = null;
    if (dy < -40) this.expandCard();
    else if (dy > 40 && this.data.cardExpanded) this.collapseCard();
  },
  closeCard() { this.setData({ card: null, activeMarkerId: null, cardExpanded: false }); this.renderMarkers(); this.setTabBarHidden(false); },
  onMapTap(e) {
    if (this.ignoreNextMapTap || (e && e.detail && e.detail.markerId !== undefined)) { this.ignoreNextMapTap = false; clearTimeout(this.ignoreMapTapTimer); return; }
    // 点浮层外区域：仅关闭筛选空态浮层、保留当前筛选（UI 稿异常态 C）
    if (this.data.filterEmpty) { this.setData({ filterEmpty: false }); return; }
    if (this.data.card || this.data.activeMarkerId !== null) this.closeCard();
  },
  onRegionChange(e) {
    const det = e.detail || {};
    const causedBy = det.causedBy;
    const byUser = causedBy === 'drag' || causedBy === 'scale' || causedBy === 'gesture';
    if (e.type === 'begin' && byUser && this.data.card) this.closeCard();
    // 只有「用户手动拖动／缩放结束」才回写中心点。
    // 程序化相机（includePoints / scale 变更）引起的 regionchange 若也回写，
    // 会与地图自身动画互相触发，导致地图持续抖动、来回切换到不同位置。
    if (e.type === 'end' && byUser && det.centerLocation) {
      this.setData({
        centerLat: det.centerLocation.latitude,
        centerLng: det.centerLocation.longitude,
      });
    }
  },
  goDetail() {
    const pt = this.currentPt;
    if (!pt) return;
    wx.navigateTo({ url: `/pages/school-detail/index?name=${encodeURIComponent(pt.name)}&stage=${pt.mainStage}&id=${encodeURIComponent(pt.school_id || '')}` });
  },
});
