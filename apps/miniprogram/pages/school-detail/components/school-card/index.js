/**
 * 学校卡组件（半窗 / 全屏 单层级原位生长）—— 路径 A：窗口整体在分包，渲染于地图页之上。
 *
 * 设计目标（对齐用户示例视频）：
 *  - 同一张卡片，从半窗（45%）跟手向上滑动 → 顶边跟随手指上移 → 松手过阈值补动画到全屏（不跳新页面）；
 *  - 全屏态返回：点左上角返回按钮 / 从左往右滑动 → 掉回半窗；不再有"展开→跳新页→返回→再收"的双跳；
 *  - 全屏态展示该校完整详情（招生计划 / 升学路线 / 中考报考 / 高考信息 / 关联校区），数据全部来自分包；
 *  - 主包 repository 不加载详情数据，分包在 app 启动即预加载，点学校时无等待。
 *
 * 用法：首页（地图）以 wx:if 挂载（context="overlay"），详情页以整屏挂载（context="page"）。
 */
const cast = (v) => v;

// 分包内详情数据（同包，安全 require）；仅声明原始紧凑模块，hydrate 延后到运行时取主包 shared。
// ⚠️ 严禁在此 require 主包模块（utils/data.js / shared）：分包组件跨包 require 主包会在
// componentPlaceholder 异步单组件注入路径下报 i.functions 崩溃；改为由 app.js 注入 globalData 读取。
const rawMiddleEnroll2026 = require('../../data/middle/enrollment/dist/middle_enrollment_2026.js');
const rawQuotaMatrix = require('../../data/linkage/quota_matrix.js');
const rawSpecialMatrix = require('../../data/linkage/special_matrix.js');
const rawBatch2Scores = require('../../data/linkage/batch2_scores.js');
const rawDistrictQuota = require('../../data/linkage/district_quota.js');
const rawBrandGroups = require('../../data/registry/group/src/brand_groups.js');
const rawEducationGroups = require('../../data/registry/group/dist/education_groups.js');

// 就绪哨兵：本模块（分包代码）一旦被执行，立即向 globalData 标记「详情分包已就绪」，
// 供主包地图页同步查询（wx.loadSubpackage 预热 / componentPlaceholder 注入 / 详情页加载，
// 任一路径执行到分包代码都会经过这里），页面据此把 subReady 置真、点学校直接出真卡。
try {
  const g = (typeof getApp === 'function') ? getApp() : null;
  if (g && g.globalData) g.globalData.detailSubReady = true;
} catch (e) { /* 极端场景（如独立分包环境）忽略 */ }

// 主包 shared（函数）/ baseLoaders（数据）由 app.js 启动时注入 globalData，运行时读取，避免跨包 require。
let _ctx = null;
function ctx() {
  if (_ctx && _ctx.repository) return _ctx;
  const g = (typeof getApp === 'function') ? getApp() : null;
  const shared = g && g.globalData && g.globalData.shared;
  const baseLoaders = g && g.globalData && g.globalData.baseLoaders;
  if (!shared || !baseLoaders) {
    throw new Error('school-card: 主包数据未就绪（globalData.shared / baseLoaders 缺失）');
  }
  const { hydrate, createRepository } = shared;
  const middleEnroll2026 = cast(hydrate(rawMiddleEnroll2026));
  const loaders = {
    ...baseLoaders,
    quotaMatrix: cast(hydrate(rawQuotaMatrix)),
    specialMatrix: cast(hydrate(rawSpecialMatrix)),
    batch2Scores: cast(hydrate(rawBatch2Scores)),
    districtQuota: cast(hydrate(rawDistrictQuota)),
    brandGroups: cast(hydrate(rawBrandGroups)),
    educationGroups: cast(hydrate(rawEducationGroups)),
    middleEnrollments: Object.values(middleEnroll2026.districts),
    middleEnrollmentMechanisms: middleEnroll2026.mechanisms,
    middleEnrollmentGroups: middleEnroll2026.groups,
  };
  _ctx = { shared, baseLoaders, loaders, repository: createRepository(loaders) };
  return _ctx;
}
// 与上方 ctx() 配套：延迟取主包 shared 的构建函数，避免模块顶层跨包 require。
function buildDetailModel(...args) { return ctx().shared.buildDetailModel(...args); }
function buildLinkageModel(...args) { return ctx().shared.buildLinkageModel(...args); }

const STAGE_SHORT = { primary: '小学', middle: '初中', high: '高中' };
const STAGE_ORDER = { high: 0, middle: 1, primary: 2 };
const sortStages = (stages) => stages.slice().sort((a, b) => STAGE_ORDER[a] - STAGE_ORDER[b]);
/** Web 路由风格 to（/school/xxx?stage=yy&id=zz）→ 小程序页面参数 */
function parseSchoolTo(to) {
  const m = /^\/school\/([^?]+)(?:\?(.+))?$/.exec(to || '');
  if (!m) return null;
  let name = m[1];
  try { name = decodeURIComponent(name); } catch (e) { /* 未编码中文原样 */ }
  const query = {};
  (m[2] || '').split('&').forEach((part) => {
    const idx = part.indexOf('=');
    if (idx < 0) return;
    const key = part.slice(0, idx);
    const val = part.slice(idx + 1);
    if (key) query[key] = decodeURIComponent(val);
  });
  return { name, stage: query.stage || '', id: query.id || '' };
}
/** 校名 + 实体 id → 可点击跳转 to（缺 id 时仅按名兜底） */
function schoolTo(name, stage, id) {
  if (!name) return null;
  return `/school/${encodeURIComponent(name)}?stage=${stage}${id ? `&id=${id}` : ''}`;
}

Component({
  options: { multipleSlots: false, addGlobalClass: false },
  properties: {
    context: { type: String, value: 'overlay' }, // 'overlay'（地图页浮层）| 'page'（详情页整屏宿主）
    visible: { type: Boolean, value: true },
    schoolId: { type: String, value: '' },
    name: { type: String, value: '' },
    stage: { type: String, value: '' },          // 初始学段提示（优先激活）
  },
  data: {
    mode: 'half',            // 'half' | 'full'
    activeStage: 'primary',
    tabs: [],
    tags: [],
    primary: null,
    middle: null,
    high: null,
    brand: null,
    topTitle: '学校详情',
    scrollTop: 0,
    statusBarHeight: 20,
    capTop: 26,
    capH: 32,
    sbackTop: 24,
    dtopH: 64,
    winH: 812,
    cardH: 365,
    cardDrag: 0,
    dragging: false,
    rootStyle: 'height:365px;',
  },
  observers: {
    'schoolId,name,stage': function () { this._init(); },
  },
  lifetimes: {
    attached() {
      console.log('[school-card] attached, name=', this.properties.name, 'context=', this.properties.context);
      this._metrics();
      this._init();
    },
  },
  methods: {
    /* ---------- 度量：状态栏 / 屏高 / 半窗高度 / 顶栏对齐胶囊 ---------- */
    _metrics() {
      try {
        const win = (typeof wx.getWindowInfo === 'function') ? wx.getWindowInfo() : wx.getSystemInfoSync();
        const sb = win.statusBarHeight || 20;
        const wh = win.windowHeight || 812;
        // 顶栏与右侧胶囊对齐：拿胶囊实测坐标（top/height），内容行 = 胶囊上下各留 (capsule.top - statusBar) 的对称间距，
        // 返回按钮/标题与胶囊垂直居中。胶囊 API 不可用时退化为「sb + 6 / 32px」的通用近似值。
        let capTop = sb + 6, capH = 32;
        try {
          if (typeof wx.getMenuButtonBoundingClientRect === 'function') {
            const rect = wx.getMenuButtonBoundingClientRect();
            if (rect && rect.height > 0 && rect.top >= sb) { capTop = rect.top; capH = rect.height; }
          }
        } catch (e2) { /* 用近似值 */ }
        const gap = Math.max(capTop - sb, 4);            // 胶囊距状态栏的间隙（对称用于下划线之下）
        const dtopH = capTop + capH + gap;               // 顶栏总高 = 状态栏 + 胶囊行 + 对称间隙，下划线紧贴其下
        // 返回按钮底边与胶囊底边对齐：返回按钮→下划线 与 胶囊→下划线 间隔一致（用户要求两侧间隔对齐）
        const sbackTop = capTop + capH - 36;
        this.setData({ statusBarHeight: sb, capTop, capH, sbackTop, dtopH, winH: wh, cardH: Math.round(wh * 0.45) });
      } catch (e) { /* 保底默认值 */ }
      this.updateStyle();
    },
    /* ---------- 样式：根容器高度 ---------- */
    updateStyle() {
      let h;
      if (this.properties.context === 'page') h = '100%';
      else if (this.data.mode === 'full') h = '100%'; // overlay.full：配合 .scard.overlay.full 的 top:0 覆盖整个 webview
      else h = (this.data.dragging ? this.data.cardH + this.data.cardDrag : this.data.cardH) + 'px';
      this.setData({ rootStyle: 'height:' + h + ';' });
    },
    /* ---------- 初始化：探测可用学段 + 激活 + 设模式 ---------- */
    _init() {
      const name = this.properties.name;
      const id = this.properties.schoolId;
      const stageParam = this.properties.stage;
      if (!name) return;
      // 数据链路兜底：真机一旦抛错（globalData 未注入 / 数据模块异常），给出可见提示而非渲染一张空卡
      try {
        const probe = buildDetailModel('primary', name, ctx().repository, id);
        const stages = probe.availableStages;
        let active = 'primary';
        if (stages.length) {
          if (stageParam && stages.indexOf(stageParam) > -1) active = stageParam;
          else active = stages[0];
        }
        this.applyStage(active);
        this.setData({ mode: this.properties.context === 'page' ? 'full' : 'half', cardDrag: 0, dragging: false, topTitle: '学校详情', scrollTop: 0 });
        this.updateStyle();
      } catch (e) {
        console.error('[school-card] 初始化失败:', e);
        wx.showToast({ title: '学校信息加载失败，请重试', icon: 'none', duration: 2500 });
      }
    },
    /* ---------- 切换学段：重建视图 ---------- */
    applyStage(stage) {
      const name = this.properties.name;
      const id = this.properties.schoolId;
      const model = buildDetailModel(stage, name, ctx().repository, id);
      const rawLinkage = (stage === 'middle' || stage === 'high')
        ? buildLinkageModel(stage, name, ctx().repository, id || null)
        : null;
      const tabs = sortStages(model.availableStages).map((s) => ({ stage: s, label: STAGE_SHORT[s], on: s === stage }));
      const tags = [
        { cls: 'dist', text: model.district || '—' },
        { cls: 'stage', text: STAGE_SHORT[stage] },
        { cls: 'nature', text: model.nature || '公办' },
      ];
      this.setData({
        activeStage: stage,
        tabs,
        tags,
        primary: stage === 'primary' ? this.buildPrimaryView(model) : null,
        middle: stage === 'middle' ? this.buildMiddleView(model, rawLinkage) : null,
        high: stage === 'high' ? this.buildHighView(model, rawLinkage) : null,
        brand: this.buildBrandView(model),
        topTitle: '学校详情',
      });
    },

    /* ---------- 小学（07） ---------- */
    buildPrimaryView(model) {
      let plan;
      if (model.enrollment) {
        const e = model.enrollment;
        plan = {
          has: true,
          planClasses: e.plan_classes,
          meta: e.plan_classes != null ? `计划 ${e.plan_classes} 个班` : '',
          zone: e.zone || '',
        };
      } else {
        plan = { has: false, empty: '未在 2026 招生计划中匹配到招生地段（数据覆盖七区；分校区、新建校暂缺，后续补录）。' };
      }
      const rg = model.routeGroups || [];
      const CN_NUM = ['一', '二', '三', '四', '五', '六'];
      const schoolsOf = (g) => (g.schools || []).map((s) => ({ name: s.name, to: s.id ? schoolTo(s.name, 'middle', s.id) : null }));
      const groups = rg.map((g, i) => ({
        n: rg.length > 1 ? (CN_NUM[i] || (i + 1)) : '',
        label: g.label,
        schools: schoolsOf(g),
      }));
      const routes = { groups, note: model.feedGap || (model.feedJuniors && model.feedJuniors.source_note) || '' };
      return { plan, routes };
    },

    /* ---------- 初中（07B / 07D） ---------- */
    buildMiddleView(model, linkage) {
      const matches = ctx().repository.middleEnrollmentsOf(this.properties.schoolId) || [];
      const groups = ctx().loaders.middleEnrollmentGroups || {};
      const plans = matches.map((mt) => {
        const rec = mt.record;
        const def = mt.mechanismDef;
        let schools = [];
        let groupName = '';
        const grp = rec.group_id ? groups[rec.group_id] : null;
        if (grp && grp.primaryIds) {
          groupName = grp.name || '';
          schools = Object.keys(grp.primaryIds).map((nm) => {
            const ids = grp.primaryIds[nm] || [];
            return { name: nm, to: ids[0] ? schoolTo(nm, 'primary', ids[0]) : null, isCurrent: ids.indexOf(this.properties.schoolId) > -1 };
          });
        } else if (rec.scope_school_ids) {
          schools = Object.keys(rec.scope_school_ids).map((nm) => {
            const ids = rec.scope_school_ids[nm] || [];
            return { name: nm, to: ids[0] ? schoolTo(nm, 'primary', ids[0]) : null, isCurrent: ids.indexOf(this.properties.schoolId) > -1 };
          });
        } else if (rec.scope) {
          schools = [{ name: rec.scope, to: null, isCurrent: false }];
        }
        return {
          mechLabel: def ? def.label : rec.mechanism,
          planClasses: rec.plan_classes,
          scope: rec.scope && !rec.scope_school_ids ? rec.scope : '',
          schools,
          groupName,
          note: rec.mechanism_note || '',
        };
      });
      let link = null;
      if (linkage && linkage.hasMiddleData) {
        link = {
          has: true,
          quota: linkage.quota ? { kaosheng: linkage.quota.kaosheng, sheng: linkage.quota.sheng_quota, qu: linkage.quota.qu_quota } : null,
          campuses: (linkage.campuses || []).map((c) => ({ name: c.campus, to: c.poiName ? schoolTo(c.poiName, 'middle', c.schoolId) : null })),
          city: (linkage.batchMerged || []).map((r) => ({ name: r.campusFull || r.campus, n: r.n, min: r.min, to: r.poiName ? schoolTo(r.poiName, 'high', '') : null })),
          district: (linkage.districtRows || []).map((r) => ({ name: r.name, n: r.n, min: r.min, to: r.poiName ? schoolTo(r.poiName, 'high', '') : null })),
        };
      } else {
        link = { has: false };
      }
      return { hasPlan: matches.length > 0, enrollNote: model.enrollNote, plans, linkage: link };
    },

    /* ---------- 高中（07E） ---------- */
    buildHighView(model, linkage) {
      const special = (linkage && (linkage.autonomyPlan != null || linkage.sportsPlan != null || linkage.artsPlan != null))
        ? {
            autonomyPlan: linkage.autonomyPlan, sportsPlan: linkage.sportsPlan, artsPlan: linkage.artsPlan,
            sportsProjects: linkage.sportsProjects || [], artsProjects: linkage.artsProjects || [],
            planNotes: linkage.planNotes || [],
          }
        : null;
      const coverage = (linkage && (linkage.highCoverage.length || linkage.highDistrictCoverage.length))
        ? {
            city: linkage.highCoverage.map((r) => ({
              name: r.school, n: r.n, districts: (r.districts || []).join('、'),
              to: r.poiName ? schoolTo(r.poiName, 'middle', '') : null,
              campuses: (r.campuses || []).map((c) => ({ name: c.campus, to: c.poiName ? schoolTo(c.poiName, 'middle', c.schoolId) : null })),
            })),
            district: linkage.highDistrictCoverage.map((r) => ({ name: r.school, n: r.n, to: r.poiName ? schoolTo(r.poiName, 'middle', '') : null })),
          }
        : null;
      return { gaokao: model.gaokaoRows || [], admission: model.admissionRows || [], special, coverage };
    },

    /* ---------- 关联校区（07 / 07B / 07E / 07F）：所属集团 / 集团核心校 / 集团成员校（不区分法人维度） ---------- */
    buildBrandView(model) {
      // 当前查看的学校排在其所属模块（集团核心校 / 集团成员校）首位
      const sortCurrentFirst = (arr) => arr.slice().sort((a, b) => (b.isCurrent ? 1 : 0) - (a.isCurrent ? 1 : 0));
      const toRow = (r) => ({ name: r.name, isCurrent: !!r.isCurrent, stages: (r.stages || []).map((s) => ({ text: s })), to: r.link || null });
      if (model.brandCardUseful && model.brandCard) {
        const bc = model.brandCard;
        const rows = bc.groups.reduce((acc, g) => acc.concat(g.rows), []);
        const core = sortCurrentFirst(rows.filter((r) => r.legal === 'same' && r.role === '核心校').map(toRow));
        const member = sortCurrentFirst(rows.filter((r) => !(r.legal === 'same' && r.role === '核心校')).map(toRow));
        return { group: bc.brand, core, member, multi: null };
      }
      if (model.multiCampusCardUseful && model.multiCampusCard) {
        const rows = sortCurrentFirst(model.multiCampusCard.groups.reduce((acc, g) => acc.concat(g.rows), []).map(toRow));
        return { group: '', core: null, member: null, multi: rows };
      }
      return null;
    },

    /* ---------- 交互 ---------- */
    onStageTap(e) {
      const stage = e.currentTarget.dataset.stage;
      if (stage === this.data.activeStage) return;
      this.applyStage(stage);
    },
    // 半窗 → 全屏：跟手松手过阈值后从此方法补齐（也在 handle / 校名 / 展开详情 处直接调用）
    expand() {
      if (this.data.mode === 'full') return;
      this.setData({ dragging: false, cardDrag: 0, mode: 'full' });
      this.updateStyle();
    },
    onBack() {
      if (this.properties.context === 'page') {
        wx.navigateBack({ delta: 1, fail: () => wx.reLaunch({ url: '/pages/index/index' }) });
        return;
      }
      this.setData({ mode: 'half', cardDrag: 0, dragging: false });
      this.updateStyle();
    },
    onClose() { this.triggerEvent('close'); },
    // 关联校区链接：overlay 上下文→地图页原位切换该校（不发新页面）；page 上下文→重定向到该校详情页
    goSchool(e) {
      const hit = parseSchoolTo(e.currentTarget.dataset.to);
      if (!hit) return;
      if (this.properties.context === 'page') {
        wx.redirectTo({ url: `/pages/school-detail/index?name=${encodeURIComponent(hit.name)}&stage=${hit.stage}&id=${encodeURIComponent(hit.id)}` });
      } else {
        this.triggerEvent('goto', { name: hit.name, stage: hit.stage, id: hit.id });
      }
    },
    // 全屏态滚动：超 64px 顶栏切换为校名（单行省略号），回顶恢复「学校详情」
    onBodyScroll(e) {
      const st = e.detail.scrollTop || 0;
      const t = st > 64 ? this.properties.name : '学校详情';
      if (t !== this.data.topTitle) this.setData({ topTitle: t, scrollTop: st });
    },

    /* ---------- 跟手拖动（半窗↔全屏） ---------- */
    cardTouchStart(e) {
      const t = e.touches && e.touches[0];
      if (!t) return;
      // 记录起手元素是否落在「展开」类触点（grabber / 校名 / 展开按钮）；
      // 用 mark 透传，避免依赖 tap 事件（catchtouch 父容器内轻点常因微小位移被吞、tap 不触发）。
      this._act = (e.mark && e.mark.act) || '';
      if (this.data.mode === 'full') {
        // 全屏态：仅记录坐标，用于「从左往右滑返回半窗」判定（不拦截 scroll-view 滚动）
        this._sx = t.clientX; this._sy = t.clientY;
        return;
      }
      this._sy = t.clientY; this._ly = t.clientY; this._lt = Date.now();
    },
    cardTouchMove(e) {
      if (this.data.mode === 'full') return; // 全屏滚动交给 scroll-view
      if (this._sy == null) return;
      const t = e.touches && e.touches[0];
      if (!t) return;
      const dy = Math.max(0, Math.min(this._sy - t.clientY, this.data.winH - this.data.cardH));
      this._lx = t.clientX; this._ly = t.clientY; this._lt = Date.now();
      if (dy > 4 && !this.data.dragging) this.setData({ dragging: true });
      if (Math.abs(dy - this.data.cardDrag) >= 2) { this.setData({ cardDrag: dy }); this.updateStyle(); }
    },
    cardTouchEnd(e) {
      if (this.data.mode === 'full') {
        // 从左往右滑（dx>60 且横向主导）→ 返回半窗卡
        const t = e.changedTouches && e.changedTouches[0];
        if (t && this._sx != null) {
          const dx = t.clientX - this._sx;
          const dy = t.clientY - this._sy;
          if (dx > 60 && dx > Math.abs(dy) * 1.5) this.onBack();
        }
        this._sx = null; this._sy = null; this._act = '';
        return;
      }
      if (this._sy == null) { this._act = ''; return; }
      const t = e.changedTouches && e.changedTouches[0];
      const startY = this._sy;
      this._sy = null;
      if (!t) { if (this.data.dragging) this.setData({ dragging: false, cardDrag: 0 }); this.updateStyle(); this._act = ''; return; }
      const dy = startY - t.clientY;
      const moved = Math.abs(dy);
      const v = (t.clientY - this._ly) / Math.max(1, Date.now() - this._lt);
      const span = this.data.winH - this.data.cardH;
      if (dy > span * 0.28 || (dy > 60 && v < -0.5)) { this.expand(); this._act = ''; return; }
      if (this.data.dragging || this.data.cardDrag) this.setData({ dragging: false, cardDrag: 0 });
      // 轻点「展开」类触点（位移很小）→ 兜底触发展开；真机上 tap 在 catchtouch 父容器内常被吞，故此处补一手
      if (moved < 16 && this._act === 'expand') this.expand();
      this.updateStyle();
      this._act = '';
    },
  },
});
