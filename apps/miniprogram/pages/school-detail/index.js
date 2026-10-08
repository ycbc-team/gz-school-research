/**
 * 学校详情页（三学段统一，按 UI 稿 07 重绘）：数据模型来自 @gz/shared buildDetailModel + buildLinkageModel，
 * 与 Web 详情页同一套业务逻辑，本页只做平台适配与 WXML 渲染（预计算 view，WXML 仅做展示）。
 * 视觉语言严格对齐 docs/design/school-search-ui-spec.html 第 07 / 07B / 07C / 07D / 07E / 07F 帧：
 *   .dtop（‹ 返回 / 校名 / ✕）→ .dbody（.dh1/.dtags/.stagebar/.dmod/.grp-* /.route/.lk/.dnote/.dsub/.ddiv/.chartbox/.pubbox/.pill）
 * 初中「招生计划（2026年）」模块消费 repository.middleEnrollmentsOf（含 plan_classes/scope/mechanism/派位组生源小学）；
 * 其余数据沿用 buildDetailModel / buildLinkageModel。
 */
const { shared, baseLoaders } = require('../../utils/data.js');
const { hydrate, createRepository, buildDetailModel, buildLinkageModel } = shared;

const cast = (v) => v;
/** 全量 loaders：主包 baseLoaders（含详情域空壳）+ 本分包 7 个紧凑模块 + 初中 2026 招生计划 */
const middleEnroll2026 = cast(hydrate(require('./data/middle/enrollment/dist/middle_enrollment_2026.js')));
const loaders = {
  ...baseLoaders,
  quotaMatrix: cast(hydrate(require('./data/linkage/quota_matrix.js'))),
  specialMatrix: cast(hydrate(require('./data/linkage/special_matrix.js'))),
  batch2Scores: cast(hydrate(require('./data/linkage/batch2_scores.js'))),
  districtQuota: cast(hydrate(require('./data/linkage/district_quota.js'))),
  brandGroups: cast(hydrate(require('./data/registry/group/src/brand_groups.js'))),
  educationGroups: cast(hydrate(require('./data/registry/group/dist/education_groups.js'))),
  // 初中 2026 招生计划（dist 合并一份：{districts,groups,mechanisms}）
  middleEnrollments: Object.values(middleEnroll2026.districts),
  middleEnrollmentMechanisms: middleEnroll2026.mechanisms,
  middleEnrollmentGroups: middleEnroll2026.groups,
};
const repository = createRepository(loaders);

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

Page({
  data: {
    topTitle: '学校详情',
    name: '',
    activeStage: 'primary',
    tabs: [],
    tags: [],
    primary: null,
    middle: null,
    high: null,
    brand: null,
    // 自定义导航：顶栏需避让系统状态栏（与首页同款处理），dtopH = 状态栏 + 顶栏(14+36+14)
    statusBarHeight: 20,
    dtopH: 84,
  },

  onLoad(query) {
    this.name = decodeURIComponent(query.name || '');
    this.stageParam = query.stage || '';
    this.schoolId = query.id || '';
    this._scrollTop = 0;
    this._py = null;
    // 自定义导航避让系统状态栏（否则 ‹/✕ 与状态栏文字重叠）
    try {
      const win = (typeof wx.getWindowInfo === 'function') ? wx.getWindowInfo() : wx.getSystemInfoSync();
      const sb = win.statusBarHeight || 20;
      this.setData({ statusBarHeight: sb, dtopH: sb + 64 });
    } catch (e) { /* 保底默认值 */ }
    // 先以 primary 构建拿 availableStages（完中多学部），再按 query.stage 或首个可用学部激活
    const probe = buildDetailModel('primary', this.name, repository, this.schoolId);
    const stages = probe.availableStages;
    let active = 'primary';
    if (stages.length) {
      if (this.stageParam && stages.indexOf(this.stageParam) > -1) active = this.stageParam;
      else active = stages[0];
    }
    this.applyStage(active);
  },

  onPageScroll(e) {
    this._scrollTop = e.scrollTop || 0;
    const t = this._scrollTop > 64 ? this.data.name : '学校详情';
    if (t !== this.data.topTitle) this.setData({ topTitle: t });
  },
  // 全屏页顶部下滑（scrollTop≈0 且向下滑 >60px）→ 收回半窗卡（navigateBack 回首页半窗）
  pageTouchStart(e) {
    this._py = e.touches && e.touches[0] ? e.touches[0].clientY : null;
  },
  pageTouchEnd(e) {
    if (this._py == null) return;
    const cy = (e.changedTouches && e.changedTouches[0] && e.changedTouches[0].clientY) || this._py;
    const dy = cy - this._py;
    this._py = null;
    if (dy > 60 && (this._scrollTop || 0) <= 2) this.goBack();
  },

  applyStage(stage) {
    const model = buildDetailModel(stage, this.name, repository, this.schoolId);
    const rawLinkage = stage === 'middle' || stage === 'high'
      ? buildLinkageModel(stage, this.name, repository, this.schoolId || null)
      : null;

    const tabs = sortStages(model.availableStages).map((s) => ({ stage: s, label: STAGE_SHORT[s], on: s === stage }));
    const tags = [
      { cls: 'dist', text: model.district || '—' },
      { cls: 'stage', text: STAGE_SHORT[stage] },
      { cls: 'nature', text: model.nature || '公办' },
    ];

    const view = {
      topTitle: stage && this._scrollTop > 64 ? this.data.name : '学校详情',
      name: model.name,
      activeStage: stage,
      tabs,
      tags,
      primary: stage === 'primary' ? this.buildPrimaryView(model) : null,
      middle: stage === 'middle' ? this.buildMiddleView(model, rawLinkage) : null,
      high: stage === 'high' ? this.buildHighView(model, rawLinkage) : null,
      brand: this.buildBrandView(model),
    };
    this.setData(view);
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
    // 升学路线：按 mechanism 拆分成 routeGroups（模型已排序：对口直升＞多校电脑派位＞单校划片＞电脑派位＞自主招生）
    const rg = model.routeGroups || [];
    const CN_NUM = ['一', '二', '三', '四', '五', '六'];
    const schoolsOf = (g) => (g.schools || []).map((s) => ({ name: s.name, to: s.id ? schoolTo(s.name, 'middle', s.id) : null }));
    let routes;
    if (rg.length >= 2) {
      routes = {
        mode: 'multi',
        groups: rg.map((g, i) => ({ n: CN_NUM[i] || (i + 1), label: g.label, schools: schoolsOf(g) })),
        note: model.feedGap || (model.feedJuniors && model.feedJuniors.source_note) || '',
      };
    } else if (rg.length === 1) {
      routes = {
        mode: 'single',
        tag: rg[0].label,
        schools: schoolsOf(rg[0]),
        note: model.feedGap || (model.feedJuniors && model.feedJuniors.source_note) || '',
      };
    } else {
      routes = { mode: 'none' };
    }
    return { plan, routes };
  },

  /* ---------- 初中（07B / 07D） ---------- */
  buildMiddleView(model, linkage) {
    const matches = repository.middleEnrollmentsOf(this.schoolId) || [];
    const groups = loaders.middleEnrollmentGroups || {};
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
          return { name: nm, to: ids[0] ? schoolTo(nm, 'primary', ids[0]) : null, isCurrent: ids.indexOf(this.schoolId) > -1 };
        });
      } else if (rec.scope_school_ids) {
        schools = Object.keys(rec.scope_school_ids).map((nm) => {
          const ids = rec.scope_school_ids[nm] || [];
          return { name: nm, to: ids[0] ? schoolTo(nm, 'primary', ids[0]) : null, isCurrent: ids.indexOf(this.schoolId) > -1 };
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

    // 中考报考情况（linkage）
    let link = null;
    if (linkage && linkage.hasMiddleData) {
      link = {
        has: true,
        quota: linkage.quota ? {
          kaosheng: linkage.quota.kaosheng,
          sheng: linkage.quota.sheng_quota,
          qu: linkage.quota.qu_quota,
        } : null,
        campuses: (linkage.campuses || []).map((c) => ({ name: c.campus, to: c.poiName ? schoolTo(c.poiName, 'middle', c.schoolId) : null })),
        city: (linkage.batchMerged || []).map((r) => ({
          name: r.campusFull || r.campus, n: r.n, min: r.min,
          to: r.poiName ? schoolTo(r.poiName, 'high', '') : null,
        })),
        district: (linkage.districtRows || []).map((r) => ({
          name: r.name, n: r.n, min: r.min,
          to: r.poiName ? schoolTo(r.poiName, 'high', '') : null,
        })),
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
          district: linkage.highDistrictCoverage.map((r) => ({
            name: r.school, n: r.n,
            to: r.poiName ? schoolTo(r.poiName, 'middle', '') : null,
          })),
        }
      : null;
    return {
      gaokao: model.gaokaoRows || [],
      admission: model.admissionRows || [],
      special,
      coverage,
    };
  },

  /* ---------- 关联校区（07 / 07F） ---------- */
  buildBrandView(model) {
    const toRow = (r) => ({
      name: r.name,
      isCurrent: !!r.isCurrent,
      stages: (r.stages || []).map((s) => ({ text: s })),
      to: r.link || null,
    });
    if (model.brandCardUseful && model.brandCard) {
      const bc = model.brandCard;
      const rows = bc.groups.reduce((acc, g) => acc.concat(g.rows), []);
      const sameCore = rows.filter((r) => r.legal === 'same' && r.role === '核心校').map(toRow);
      const sameMember = rows.filter((r) => r.legal === 'same' && r.role !== '核心校').map(toRow);
      const indepMember = rows.filter((r) => r.legal === 'independent').map(toRow);
      const pubNote = bc.note || (bc.sourceUrls && bc.sourceUrls.length ? `公示文件说明：${bc.sourceUrls.join('、')}` : '');
      return {
        brand: bc.brand, pubNote,
        same: { core: sameCore, member: sameMember },
        indep: { member: indepMember },
        multi: null,
      };
    }
    if (model.multiCampusCardUseful && model.multiCampusCard) {
      const rows = model.multiCampusCard.groups.reduce((acc, g) => acc.concat(g.rows), []).map(toRow);
      return { brand: '', pubNote: '', same: null, indep: null, multi: rows };
    }
    return null;
  },

  onStageTap(e) {
    const stage = e.currentTarget.dataset.stage;
    if (stage === this.data.activeStage) return;
    this.applyStage(stage);
  },

  goBack() {
    wx.navigateBack({ delta: 1, fail: () => wx.reLaunch({ url: '/pages/index/index' }) });
  },
  viewOnMap() {
    const app = getApp();
    app.pendingFocus = this.schoolId || this.name;
    wx.switchTab({ url: '/pages/index/index' });
  },
  goSchool(e) {
    const hit = parseSchoolTo(e.currentTarget.dataset.to);
    if (!hit) return;
    wx.navigateTo({ url: `/pages/school-detail/index?name=${encodeURIComponent(hit.name)}&stage=${hit.stage}&id=${encodeURIComponent(hit.id)}` });
  },
  openCampusPicker(e) {
    let raw = e.currentTarget.dataset.campuses;
    if (typeof raw === 'string') { try { raw = JSON.parse(raw); } catch (_) { raw = []; } }
    if (!Array.isArray(raw) || !raw.length) return;
    wx.showActionSheet({
      itemList: raw.map((c) => c.poiName || c.campus),
      success: (res) => {
        const c = raw[res.tapIndex];
        if (!c) return;
        this.goSchool({ currentTarget: { dataset: { to: `/school/${c.poiName || c.campus}?stage=middle&id=${c.schoolId}` } } });
      },
    });
  },
});
