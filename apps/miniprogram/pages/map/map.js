/**
 * 地图页：三学段点位（共享 buildPoints）+ 三级筛选（区域/学段/分级）+ 搜索 + 底部抽屉信息卡 + 详情跳转。
 * 业务逻辑全部来自 @gz/shared（repository + domain/map），本页只做平台适配与 UI 绑定。
 */
const { shared, repository, mapPoints } = require('../../utils/data.js');
const {
  DISTRICTS,
  STAGE_TABS,
  SCHOOL_NATURE_TABS,
  GRADE_GROUPS,
  CLASS_CFG,
  STAGE_LABEL,
  initialFilterState,
  toggleDistrict,
  toggleStage,
  toggleGrade,
  toggleNature,
  flipDistricts,
  flipStages,
  flipGrades,
  flipNatures,
  districtAll,
  stageAll,
  gradeAll,
  natureAll,
  isVisible,
  searchSchools,
  buildInfoModel,
} = shared;

/** stages 枚举 → PNG 文件名缩写（p/m/h） */
const STAGE_KEY = { primary: 'p', middle: 'm', high: 'h' };
/** marker 图标：stages 升序（p/m/h）→ 14 张 PNG（普通 + -sel 选中态，构建脚本按 shared 颜色生成，对齐 Web） */
function markerIcon(stages, selected) {
  const key = stages.map((s) => STAGE_KEY[s]).join('');
  return `/assets/markers/marker-${key}${selected ? '-sel' : ''}.png`;
}

Page({
  data: {
    districts: [],
    selectedDistricts: [],
    selectedStages: [],
    selectedGrades: [],
    selectedNatures: [],
    districtAll: true,
    stageAll: true,
    gradeAll: true,
    natureAll: true,
    markers: [],
    visibleCount: 0,
    activeMarkerId: null,
    kw: '',
    searchResults: [],
    searchOpen: false,
    menu: '',
    topHidden: false,
    info: null,
    // 底部抽屉下拉时的视觉位移（px）。手势状态留在实例上，避免每次触摸都触发无关渲染。
    drawerOffset: 0,
    drawerDragging: false,
    centerLat: 23.13,
    centerLng: 113.3,
    scale: 11,
  },

  onLoad(query) {
    this.setData({
      districts: DISTRICTS.map((d) => ({ name: d.name, short: d.name.replace('区', ''), adcode: d.adcode })),
      STAGE_TABS,
      SCHOOL_NATURE_TABS,
      GRADE_GROUPS,
    });
    this.syncState(initialFilterState());
    this.renderMarkers();
    // 详情页"在地图中查看"：定位并弹出信息卡（放大居中 + 选中态，对齐 Web）
    if (query && query.focus) {
      const name = decodeURIComponent(query.focus);
      const pt = mapPoints.find((p) => p.school_id === name) || mapPoints.find((p) => p.name === name) || mapPoints.find((p) => p.name.includes(name));
      if (pt) {
        this.showInfo(pt);
        const idx = this.visible.findIndex((p) => p === pt);
        this.setData({ activeMarkerId: idx >= 0 ? idx : null, centerLat: pt.lat, centerLng: pt.lng, scale: 16 });
        this.renderMarkers();
      }
    }
  },

  onReady() {
    // 原生 map 的视野动画必须通过 MapContext 发起；仅更新 latitude/longitude 通常会直接跳转。
    this.mapCtx = wx.createMapContext('gzmap', this);
  },

  /** 共享状态机 → 页面 data（Set → 数组 + 预计算 checked 标志，WXML 不支持 indexOf） */
  syncState(st) {
    const selD = st.selectedDistricts;
    const selS = st.selectedStages;
    const selG = st.selectedGrades;
    const selN = st.selectedNatures;
    this.setData({
      selectedDistricts: [...selD],
      selectedStages: [...selS],
      selectedGrades: [...selG],
      selectedNatures: [...selN],
      districtAll: districtAll(st),
      stageAll: stageAll(st),
      gradeAll: gradeAll(st),
      natureAll: natureAll(st),
      // 预计算 chips 选中态（WXML 表达式不支持方法调用）
      districts: this.data.districts.map((d) => ({ ...d, checked: selD.has(d.adcode) })),
      STAGE_TABS: this.data.STAGE_TABS.map((t) => ({ ...t, checked: selS.has(t.v) })),
      GRADE_GROUPS: this.data.GRADE_GROUPS.map((g) => ({
        ...g,
        checked: selG.has(g.v),
        items: (g.items || []).map((o) => ({ ...o, checked: selG.has(o.v) })),
      })),
      SCHOOL_NATURE_TABS: this.data.SCHOOL_NATURE_TABS.map((o) => ({ ...o, checked: selN.has(o.v) })),
    });
  },
  currentState() {
    const d = this.data;
    return {
      selectedDistricts: new Set(d.selectedDistricts),
      selectedStages: new Set(d.selectedStages),
      selectedGrades: new Set(d.selectedGrades),
      selectedNatures: new Set(d.selectedNatures),
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
    this.closeInfo();
    const m = e.currentTarget.dataset.menu;
    this.setData({ menu: this.data.menu === m ? '' : m });
  },
  closeMenu() { this.setData({ menu: '' }); },
  toggleDistrictAd(e) { this.closeInfo(); this.syncState(toggleDistrict(this.currentState(), e.currentTarget.dataset.adcode)); this.renderMarkers(); },
  toggleStageTab(e) { this.closeInfo(); this.syncState(toggleStage(this.currentState(), e.currentTarget.dataset.stage)); this.renderMarkers(); },
  toggleNatureTab(e) { this.closeInfo(); this.syncState(toggleNature(this.currentState(), e.currentTarget.dataset.nature)); this.renderMarkers(); },
  toggleGradeCls(e) { this.closeInfo(); this.syncState(toggleGrade(this.currentState(), e.currentTarget.dataset.cls)); this.renderMarkers(); },
  flipAllDistricts() { this.closeInfo(); this.syncState(flipDistricts(this.currentState())); this.renderMarkers(); },
  flipAllStages() { this.closeInfo(); this.syncState(flipStages(this.currentState())); this.renderMarkers(); },
  flipAllNatures() { this.closeInfo(); this.syncState(flipNatures(this.currentState())); this.renderMarkers(); },
  flipAllGrades() { this.closeInfo(); this.syncState(flipGrades(this.currentState())); this.renderMarkers(); },

  /* ---------- 搜索 ---------- */
  onSearchInput(e) {
    this.closeInfo();
    const kw = e.detail.value;
    this.setData({ kw, searchResults: searchSchools(mapPoints, kw, repository.entities), searchOpen: true });
  },
  pickResult(e) {
    const pt = this.data.searchResults[e.currentTarget.dataset.idx];
    if (!pt) return;
    const idx = this.visible.findIndex((p) => p === pt);
    this.setData({ kw: '', searchResults: [], searchOpen: false });
    this.focusPoint(pt, idx >= 0 ? idx : null);
  },

  /* ---------- 信息卡（底部抽屉，对齐 Web） ---------- */
  onMarkerTap(e) {
    const pt = this.visible[e.detail.markerId];
    if (!pt) return;
    // 部分基础库会在同一次 marker tap 后继续派发 map tap（且 detail 不含 markerId）。
    // 吞掉这一帧的后续 tap，避免抽屉刚打开就被 onMapTap 关闭。
    this.ignoreNextMapTap = true;
    clearTimeout(this.ignoreMapTapTimer);
    this.ignoreMapTapTimer = setTimeout(() => { this.ignoreNextMapTap = false; }, 300);
    this.focusPoint(pt, e.detail.markerId);
  },
  /**
   * 一次原生镜头动画完成“平移 + 放大”。
   * 用目标点周围不可见的一对对角参考点确定最终视野，避免 includePoints 结束后再 setData 收束，
   * 造成两段动画之间的画面跳变。
   */
  focusPoint(pt, markerId) {
    this.setData({ activeMarkerId: markerId });
    this.renderMarkers();
    this.showInfo(pt);

    this.isFocusing = true;
    clearTimeout(this.focusTimer);
    // 个别基础库在目标已居中时不会发 regionchange end，超时兜底后仍能响应用户拖图关闭抽屉。
    this.focusTimer = setTimeout(() => { this.isFocusing = false; }, 1000);
    const target = { latitude: pt.lat, longitude: pt.lng };
    const token = (this.cameraToken || 0) + 1;
    this.cameraToken = token;
    const isCurrent = (center) => Math.abs(center.latitude - target.latitude) < 0.00005 &&
      Math.abs(center.longitude - target.longitude) < 0.00005;
    const fallback = () => {
      if (this.cameraToken !== token) return;
      // 不支持 includePoints 时保留单次属性更新，避免人为拆成两段而闪跳。
      this.setData({ centerLat: target.latitude, centerLng: target.longitude, scale: 16 });
    };
    if (!this.mapCtx) return fallback();
    this.mapCtx.getCenterLocation({
      success: (center) => {
        if (this.cameraToken !== token) return;
        if (isCurrent(center)) return this.setData({ scale: 16 });
        // 约 16 级视野的半径；经度按纬度校正，四点的包围盒中心即目标点。
        const latDelta = 0.0018;
        const lngDelta = latDelta / Math.cos(target.latitude * Math.PI / 180);
        const targetFrame = [
          { latitude: target.latitude - latDelta, longitude: target.longitude - lngDelta },
          { latitude: target.latitude + latDelta, longitude: target.longitude + lngDelta },
        ];
        this.mapCtx.includePoints({
          // includePoints 自身会从当前视野过渡到此最终视野；targetFrame 决定目标中心与缩放级别。
          points: targetFrame,
          // 底部抽屉会遮住下半屏，留出更大的下边距。
          padding: [80, 40, 360, 40],
          fail: fallback,
        });
      },
      fail: fallback,
    });
  },
  /** 用户拖动/缩放地图后同步中心（受控经纬度必须回写，否则下次 setData 会跳回旧中心） */
  onRegionChange(e) {
    if (e.type === 'begin' && !this.isFocusing) this.closeInfo();
    if (e.type === 'end' && e.detail && e.detail.centerLocation) {
      this.setData({
        centerLat: e.detail.centerLocation.latitude,
        centerLng: e.detail.centerLocation.longitude,
      });
      this.isFocusing = false;
      clearTimeout(this.focusTimer);
    }
  },
  onMapTap(e) {
    // marker 上的 tap 由 onMarkerTap 处理（部分基础库 detail 含 markerId）
    if (this.ignoreNextMapTap || (e && e.detail && e.detail.markerId !== undefined)) {
      this.ignoreNextMapTap = false;
      clearTimeout(this.ignoreMapTapTimer);
      return;
    }
    if (this.data.info || this.data.activeMarkerId !== null) {
      this.closeInfo();
    }
  },
  showInfo(pt) {
    this.drawerScrollTop = 0;
    this.setData({ info: buildInfoModel(pt, repository), drawerOffset: 0, drawerDragging: false, topHidden: true, menu: '', searchOpen: false });
  },
  closeInfo() {
    this.setData({ info: null, activeMarkerId: null, drawerOffset: 0, drawerDragging: false, topHidden: false });
    this.renderMarkers();
  },

  /* ---------- 底部抽屉手势：内容回到顶部后向下拖动关闭（与 Web 一致） ---------- */
  onDrawerScroll(e) {
    this.drawerScrollTop = e.detail.scrollTop || 0;
  },
  onDrawerTouchStart(e) {
    const touch = e.touches && e.touches[0];
    if (!touch) return;
    this.drawerStartY = touch.clientY;
    this.drawerDy = 0;
    this.drawerTracking = true;
    this.drawerHeight = 0;
    wx.createSelectorQuery().select('.drawer').boundingClientRect((rect) => {
      this.drawerHeight = rect ? rect.height : 0;
    }).exec();
    this.setData({ drawerOffset: 0, drawerDragging: false });
  },
  onDrawerTouchMove(e) {
    if (!this.drawerTracking) return;
    const touch = e.touches && e.touches[0];
    if (!touch) return;
    const dy = touch.clientY - this.drawerStartY;
    // 上滑和内容滚动时交给 scroll-view；只有位于顶部时下拉抽屉。
    if (dy <= 0 || this.drawerScrollTop > 0) {
      this.drawerDy = 0;
      return;
    }
    this.drawerDy = dy;
    this.setData({ drawerOffset: Math.min(dy * 0.5, 200), drawerDragging: true });
  },
  onDrawerTouchEnd() {
    if (!this.drawerTracking) return;
    this.drawerTracking = false;
    // 与 Web 相同：至少下拉 90px，或超过抽屉高度的约 22% 时关闭。
    const threshold = Math.max(90, (this.drawerHeight || 0) * 0.22);
    if (this.drawerDy > threshold) {
      this.closeInfo();
      return;
    }
    this.drawerDy = 0;
    this.setData({ drawerOffset: 0, drawerDragging: false });
  },

  /* ---------- 详情跳转（Web 路由风格 to → 小程序页面参数） ---------- */
  goDetail(e) {
    const to = e.currentTarget.dataset.to;
    const m = /^\/school\/([^?]+)(?:\?(.+))?$/.exec(to || '');
    if (!m) return;
    const query = {};
    (m[2] || '').split('&').forEach((part) => {
      const [key, value = ''] = part.split('=');
      if (key) query[key] = decodeURIComponent(value);
    });
    wx.navigateTo({
      url: `/pages/school-detail/index?name=${decodeURIComponent(m[1])}&stage=${query.stage || ''}&id=${encodeURIComponent(query.id || '')}`,
    });
  },
});
