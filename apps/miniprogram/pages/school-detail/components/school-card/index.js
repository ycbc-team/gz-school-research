/**
 * 学校卡组件（半窗 / 全屏 单层级原位生长）—— 路径 A：窗口整体在分包，渲染于地图页之上。
 *
 * 设计目标（对齐用户示例视频）：
 *  - 同一张卡片，从半窗（45%）跟手向上滑动 → 顶边跟随手指上移 → 松手过阈值补动画到全屏（不跳新页面）；
 *  - 全屏态返回：点左上角返回按钮 / 左右任意横向滑动（含屏幕边缘侧滑）→ 掉回半窗；不再有"展开→跳新页→返回→再收"的双跳；
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
    dtopH: 64,
    winH: 812,
    winW: 375,
    cardH: 365,
    cardDrag: 0,
    dragging: false,
    collapsing: false,     // 全屏→半窗：是否已处于「收缩动画 / 跟手收缩」态（保持全屏内容 + 地图仍隐藏，结束才切半窗）
    scrollEnabled: true,   // 全屏态 scroll-view 是否可滚；跟手收缩时临时禁用以接管手势
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
    detached() {
      if (this._collapseTimer) { clearTimeout(this._collapseTimer); this._collapseTimer = null; }
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
        // 返回按钮外圈与右侧胶囊完全对齐（用户要求）：top/bottom 分别对齐胶囊最高/最低点 →
        // 圆圈尺寸 = capH、top = capTop（wxml 行内样式给定）；内部 chevron 以 32px 胶囊为基准
        // 设计、按 capH/32 行内缩放，箭头视觉高度 ≈ 胶囊内图标高度（0.55 * capH）。
        this.setData({ statusBarHeight: sb, capTop, capH, dtopH, winH: wh, winW: (win.windowWidth || 375), cardH: Math.round(wh * 0.45) });
      } catch (e) { /* 保底默认值 */ }
      this.updateStyle();
    },
    /* ---------- 样式：根容器高度 ---------- */
    updateStyle() {
      let h;
      if (this.properties.context === 'page') h = '100%';
      // overlay 全屏且未进入收缩：用像素高度 + 始终 bottom:0 锚定（见 .scard.overlay.full 已去除 top:0），
      // 保证「从底部 45% 向上延展到全屏 / 从全屏向下收回到半窗」几何正确、过渡动画平滑（px→px 可过渡）。
      else if (this.data.mode === 'full' && !this.data.collapsing) h = this.data.winH + 'px';
      // 收缩阶段（跟手或动画收起）：高度锚定到半窗，过渡动画由 dragging 开关控制（dragging=false 时平滑过渡）。
      else if (this.data.collapsing) h = this.data.cardH + 'px';
      else h = (this.data.dragging ? this.data.cardH + this.data.cardDrag : this.data.cardH) + 'px';
      this.setData({ rootStyle: 'height:' + h + ';' });
    },
    /* ---------- 通知外部（地图页）当前模式，用于全屏时隐藏地图 ---------- */
    notifyMode() {
      if (this.properties.context === 'overlay') this.triggerEvent('modechange', { mode: this.data.mode });
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
        this.setData({ mode: this.properties.context === 'page' ? 'full' : 'half', cardDrag: 0, dragging: false, collapsing: false, scrollEnabled: true, topTitle: '学校详情', scrollTop: 0 });
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
      // 升学路线空状态：无任何可跳转学校名时，按办学性质给统一文案
      // （民办 → 不参与公办电脑派位；公办无数据 → 暂无数据）
      const hasLink = groups.some((g) => (g.schools || []).some((s) => s.to));
      routes.empty = hasLink ? '' : (model.nature === '民办' ? '不参与公办电脑派位' : '暂无数据');
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
    // 半窗 → 全屏：唯一的展开通道——上滑过阈值 / 轻点「展开」类触点（handle / 校名 / 展开按钮，
    // 经 mark 标记）均从 cardTouchEnd 进入此方法，不存在按钮独立展开逻辑（与手势共用一条路径 → 动画一致）。
    // 按钮点击也走此方法是用户明确要求：展开应与「从下往上滑」同一套延展效果，不能瞬间跳全屏。
    expand() {
      if (this.data.mode === 'full') return;
      if (this._collapseTimer) { clearTimeout(this._collapseTimer); this._collapseTimer = null; }
      this.setData({ dragging: false, cardDrag: 0, collapsing: false, scrollEnabled: true, mode: 'full' });
      this.updateStyle();
      this.notifyMode();
    },
    // 全屏 → 半窗：与展开相反。为避免「先出现高窗再回落 + 地图漏出」的闪烁，拆成两步：
    //  1) 先进入 collapsing 态：高度平滑收到 45%（winH→cardH），但 mode 仍保持 full——
    //     故全屏滚动内容不切走、地图仍隐藏（cardFull 未翻转），只看到卡片平滑收起；
    //  2) 等收起动画结束后（约 240ms）再 finalize：mode→half（内容切到半窗裁剪态）+ notifyMode（卡片转半窗 → 地图恢复显示）。
    // 返回按钮 / 任意横向滑动（含边缘）均走此入口（onBack 按 context 分支）；动画期间若再次触摸会由 cardTouchStart 清掉 pending 定时器。
    _beginCollapseSettle() {
      if (this.data.mode === 'half') return;
      if (this._collapseTimer) { clearTimeout(this._collapseTimer); this._collapseTimer = null; }
      this.setData({ collapsing: true, dragging: false, cardDrag: 0, scrollEnabled: true });
      this.updateStyle(); // collapsing=true → 高度收到 cardH(px)，dragging=false 启过渡（winH/current → 365 平滑）
      this._collapseTimer = setTimeout(() => { this._finalizeCollapse(); }, 240);
    },
    // 收起动画结束：真正切到半窗（内容换半窗裁剪态）+ 通知外部恢复地图
    _finalizeCollapse() {
      this._collapseTimer = null;
      if (this.data.mode === 'half') return;
      this.setData({ mode: 'half', collapsing: false });
      this.notifyMode(); // overlay 上下文：cardFull→false，地图在半窗态恢复显示
    },
    onBack() {
      if (this.properties.context === 'page') {
        wx.navigateBack({ delta: 1, fail: () => wx.reLaunch({ url: '/pages/index/index' }) });
        return;
      }
      this._beginCollapseSettle();
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
    // 全屏态滚动：超 64px 顶栏切换为校名（单行省略号），回顶恢复「学校详情」。
    // scrollTop 始终同步进 data（不仅跨阈值时），供手势判定复用。
    onBodyScroll(e) {
      const st = e.detail.scrollTop || 0;
      const t = st > 64 ? this.properties.name : '学校详情';
      const patch = {};
      if (t !== this.data.topTitle) patch.topTitle = t;
      if (st !== this.data.scrollTop) patch.scrollTop = st;
      if (Object.keys(patch).length) this.setData(patch);
    },

    /* ---------- 跟手拖动（半窗↔全屏 / 关闭；全屏态滚动交 scroll-view，识别左右任意横向滑动返回含边缘触发） ---------- */
    cardTouchStart(e) {
      const t = e.touches && e.touches[0];
      if (!t) return;
      // 记录起手元素是否落在「展开」类触点（grabber / 校名 / 展开按钮）；
      // 用 mark 透传，避免依赖 tap 事件（catchtouch 父容器内轻点常因微小位移被吞、tap 不触发）。
      this._act = (e.mark && e.mark.act) || '';
      if (this.data.mode === 'full') {
        // 收起动画（collapsing）进行中若再次触摸，取消 pending 定时器、恢复可滚动，避免旧定时误 finalize
        if (this.data.collapsing) { if (this._collapseTimer) { clearTimeout(this._collapseTimer); this._collapseTimer = null; } this.setData({ collapsing: false, scrollEnabled: true }); }
        // 记录坐标，用于「左右任意横向滑动（含边缘）返回半窗」判定
        this._sx = t.clientX; this._sy = t.clientY;
        this._ly = t.clientY; this._lt = Date.now();
        return;
      }
      this._sy = t.clientY; this._ly = t.clientY; this._lt = Date.now();
    },
    cardTouchMove(e) {
      // 全屏态：滚动完全交给 scroll-view（已按用户要求去掉「顶部下滑跟手收起」手势），不在此拦截
      if (this.data.mode === 'full') return;
      if (this._sy == null) return;
      const t = e.touches && e.touches[0];
      if (!t) return;
      // dy：上滑为正（展开方向）、下滑为负（关闭方向）。允许双向跟手：上至全屏、下至整卡滑出屏外。
      const dy = this._sy - t.clientY;
      const clamped = Math.max(-this.data.cardH, Math.min(dy, this.data.winH - this.data.cardH));
      this._lx = t.clientX; this._ly = t.clientY; this._lt = Date.now();
      if (Math.abs(clamped) > 4 && !this.data.dragging) this.setData({ dragging: true });
      if (Math.abs(clamped - this.data.cardDrag) >= 2) { this.setData({ cardDrag: clamped }); this.updateStyle(); }
    },
    cardTouchEnd(e) {
      if (this.data.mode === 'full') {
        const t = e.changedTouches && e.changedTouches[0];
        // 全屏态：任意方向横向滑动（左→右 或 右→左，恢复第 50 轮误删的原「右→左」返回）均可收起回半窗，
        // 与返回按钮同通道（onBack 按 context 分支：overlay→两阶段收起 / page→navigateBack）。
        // 起手位置不限——卡片盖满整屏、根容器 bind 捕获全屏任意点的 touchstart/end，故从左右边缘起手也能触发
        // （支持原生「侧滑返回」手感）；边缘起手（距屏边 ≤24px）放宽阈值，使「从边边就触发」更易达。
        if (t && this._sx != null) {
          const dx = t.clientX - this._sx;
          const dy = t.clientY - this._sy;
          const edge = this._sx <= 24 || this._sx >= this.data.winW - 24;
          const thr = edge ? 36 : 60;
          const ratio = edge ? 1.2 : 1.5;
          if (Math.abs(dx) > thr && Math.abs(dx) > Math.abs(dy) * ratio) { this.onBack(); this._resetTouch(); return; }
        }
        this._resetTouch();
        return;
      }
      if (this._sy == null) { this._act = ''; return; }
      const t = e.changedTouches && e.changedTouches[0];
      const startY = this._sy;
      this._sy = null;
      if (!t) { if (this.data.dragging) this.setData({ dragging: false, cardDrag: 0 }); this.updateStyle(); this._act = ''; return; }
      const dy = startY - t.clientY;            // 上滑为正（展开）、下滑为负（关闭）
      const moved = Math.abs(dy);
      const v = (t.clientY - this._ly) / Math.max(1, Date.now() - this._lt);
      const span = this.data.winH - this.data.cardH;
      if (dy > span * 0.28 || (dy > 60 && v < -0.5)) { this.expand(); this._act = ''; return; }
      // 半窗态下滑过阈值 → 关闭半窗卡（手势方向与上滑展开相反）
      if (dy < -this.data.cardH * 0.35 || (dy < -60 && v > 0.5)) { this.onClose(); this._act = ''; return; }
      if (this.data.dragging || this.data.cardDrag) this.setData({ dragging: false, cardDrag: 0 });
      // 轻点「展开」类触点（位移很小）→ 与上滑同走本手势通道展开；触点元素只挂 mark:act="expand"，
      // 不再各设 bindtap/catchtap 独立展开入口（用户要求：展开交互只有手势这一条路径）
      if (moved < 16 && this._act === 'expand') this.expand();
      this.updateStyle();
      this._act = '';
    },
    _resetTouch() { this._sx = null; this._sy = null; this._act = ''; },
  },
});
