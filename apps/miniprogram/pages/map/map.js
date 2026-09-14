/**
 * 地图页：三学段点位（共享 buildPoints）+ 三级筛选（区域/学段/分级）+ 搜索 + 底部抽屉信息卡 + 详情跳转。
 * 业务逻辑全部来自 @gz/shared（repository + domain/map），本页只做平台适配与 UI 绑定。
 */
const { shared, repository, mapPoints } = require('../../utils/data.js');
const {
  DISTRICTS,
  STAGE_TABS,
  GRADE_GROUPS,
  CLASS_CFG,
  STAGE_LABEL,
  initialFilterState,
  toggleDistrict,
  toggleStage,
  toggleGrade,
  flipDistricts,
  flipStages,
  flipGrades,
  districtAll,
  stageAll,
  gradeAll,
  isVisible,
  searchSchools,
  buildInfoModel,
} = shared;

/** marker 图标：stages 升序（p/m/h）→ 14 张 PNG（普通 + -sel 选中态，构建脚本按 shared 颜色生成，对齐 Web） */
function markerIcon(stages, selected) {
  return `/assets/markers/marker-${stages.join('')}${selected ? '-sel' : ''}.png`;
}

Page({
  data: {
    districts: [],
    selectedDistricts: [],
    selectedStages: [],
    selectedGrades: [],
    districtAll: true,
    stageAll: true,
    gradeAll: true,
    markers: [],
    visibleCount: 0,
    activeMarkerId: null,
    kw: '',
    searchResults: [],
    searchOpen: false,
    menu: '',
    info: null,
    centerLat: 23.13,
    centerLng: 113.3,
    scale: 11,
  },

  onLoad(query) {
    this.setData({
      districts: DISTRICTS.map((d) => ({ name: d.name, short: d.name.replace('区', ''), adcode: d.adcode })),
      STAGE_TABS,
      GRADE_GROUPS,
    });
    this.syncState(initialFilterState());
    this.renderMarkers();
    // 详情页"在地图中查看"：定位并弹出信息卡（放大居中 + 选中态，对齐 Web）
    if (query && query.focus) {
      const name = decodeURIComponent(query.focus);
      const pt = mapPoints.find((p) => p.name === name) || mapPoints.find((p) => p.name.includes(name));
      if (pt) {
        this.showInfo(pt);
        const idx = this.visible.findIndex((p) => p === pt);
        this.setData({ activeMarkerId: idx >= 0 ? idx : null });
        this.renderMarkers();
        this.setData({ scale: 16 }, () => {
          wx.createMapContext('gzmap', this).moveToLocation({ latitude: pt.lat, longitude: pt.lng });
        });
      }
    }
  },

  /** 共享状态机 → 页面 data（Set → 数组 + 预计算 checked 标志，WXML 不支持 indexOf） */
  syncState(st) {
    const selD = st.selectedDistricts;
    const selS = st.selectedStages;
    const selG = st.selectedGrades;
    this.setData({
      selectedDistricts: [...selD],
      selectedStages: [...selS],
      selectedGrades: [...selG],
      districtAll: districtAll(st),
      stageAll: stageAll(st),
      gradeAll: gradeAll(st),
      // 预计算 chips 选中态（WXML 表达式不支持方法调用）
      districts: this.data.districts.map((d) => ({ ...d, checked: selD.has(d.adcode) })),
      STAGE_TABS: this.data.STAGE_TABS.map((t) => ({ ...t, checked: selS.has(t.v) })),
      GRADE_GROUPS: this.data.GRADE_GROUPS.map((g) => ({
        ...g,
        checked: selG.has(g.v),
        items: (g.items || []).map((o) => ({ ...o, checked: selG.has(o.v) })),
      })),
    });
  },
  currentState() {
    const d = this.data;
    return {
      selectedDistricts: new Set(d.selectedDistricts),
      selectedStages: new Set(d.selectedStages),
      selectedGrades: new Set(d.selectedGrades),
    };
  },

  /** 渲染可见集（共享 isVisible；全量 ~1300 点，P4 再上聚类/视野裁剪）；activeMarkerId 命中用选中态图标 */
  renderMarkers() {
    this.visible = mapPoints.filter((p) => isVisible(this.currentState(), p));
    let active = this.data.activeMarkerId;
    const patch = {
      markers: this.visible.map((pt, i) => ({
        id: i,
        latitude: pt.lat,
        longitude: pt.lng,
        iconPath: markerIcon(pt.stages, active === i),
        width: 30,
        height: 30,
        anchor: { x: 0.5, y: 0.5 },
      })),
      visibleCount: this.visible.length,
    };
    // 选中的点被筛掉：清除选中态并关闭浮层（对齐 Web applyFilters）
    if (active !== null && !this.visible[active]) {
      patch.info = null;
      patch.activeMarkerId = null;
    }
    this.setData(patch);
  },

  /* ---------- 三级筛选 ---------- */
  toggleMenu(e) {
    const m = e.currentTarget.dataset.menu;
    this.setData({ menu: this.data.menu === m ? '' : m });
  },
  closeMenu() { this.setData({ menu: '' }); },
  toggleDistrictAd(e) { this.syncState(toggleDistrict(this.currentState(), e.currentTarget.dataset.adcode)); this.renderMarkers(); },
  toggleStageTab(e) { this.syncState(toggleStage(this.currentState(), e.currentTarget.dataset.stage)); this.renderMarkers(); },
  toggleGradeCls(e) { this.syncState(toggleGrade(this.currentState(), e.currentTarget.dataset.cls)); this.renderMarkers(); },
  flipAllDistricts() { this.syncState(flipDistricts(this.currentState())); this.renderMarkers(); },
  flipAllStages() { this.syncState(flipStages(this.currentState())); this.renderMarkers(); },
  flipAllGrades() { this.syncState(flipGrades(this.currentState())); this.renderMarkers(); },

  /* ---------- 搜索 ---------- */
  onSearchInput(e) {
    const kw = e.detail.value;
    this.setData({ kw, searchResults: searchSchools(mapPoints, kw, repository.entities), searchOpen: true });
  },
  pickResult(e) {
    const pt = this.data.searchResults[e.currentTarget.dataset.idx];
    if (!pt) return;
    const idx = this.visible.findIndex((p) => p === pt);
    this.setData({ activeMarkerId: idx >= 0 ? idx : null, kw: '', searchResults: [], searchOpen: false });
    this.renderMarkers();
    this.showInfo(pt);
    // 放大居中 + 选中态（对齐 Web focusSchool）
    this.setData({ scale: 16 }, () => {
      wx.createMapContext('gzmap', this).moveToLocation({ latitude: pt.lat, longitude: pt.lng });
    });
  },

  /* ---------- 信息卡（底部抽屉，对齐 Web） ---------- */
  onMarkerTap(e) {
    const pt = this.visible[e.detail.markerId];
    if (!pt) return;
    this.setData({ activeMarkerId: e.detail.markerId });
    this.renderMarkers();
    this.showInfo(pt);
    // 对齐 Web：点击点位放大（scale 16）并居中
    this.setData({ scale: 16 }, () => {
      wx.createMapContext('gzmap', this).moveToLocation({ latitude: pt.lat, longitude: pt.lng });
    });
  },
  onMapTap(e) {
    // marker 上的 tap 由 onMarkerTap 处理（部分基础库 detail 含 markerId）
    if (e && e.detail && e.detail.markerId !== undefined) return;
    if (this.data.info || this.data.activeMarkerId !== null) {
      this.setData({ info: null, activeMarkerId: null });
      this.renderMarkers();
    }
  },
  showInfo(pt) {
    this.setData({ info: buildInfoModel(pt, repository) });
  },
  closeInfo() {
    this.setData({ info: null, activeMarkerId: null });
    this.renderMarkers();
  },

  /* ---------- 详情跳转（Web 路由风格 to → 小程序页面参数） ---------- */
  goDetail(e) {
    const to = e.currentTarget.dataset.to;
    const m = /^\/school\/([^?]+)(?:\?stage=(\w+))?$/.exec(to || '');
    if (!m) return;
    wx.navigateTo({
      url: `/pages/school-detail/index?name=${decodeURIComponent(m[1])}&stage=${m[2] || ''}`,
    });
  },
});
