/**
 * 学校详情页（三学段统一）：数据模型来自 @gz/shared buildDetailModel + buildLinkageModel，
 * 与 Web 详情页同一套业务逻辑，本页只做平台适配与 WXML 渲染。
 * 本页位于分包：主包 baseLoaders（utils/data.js）+ 本分包 data/（linkage/sites/brandGroups/
 * educationGroups 7 个紧凑模块）合并为全量 loaders 后 createRepository。
 */
const { shared, baseLoaders } = require('../../utils/data.js');
const { hydrate, createRepository, buildDetailModel, buildLinkageModel } = shared;

const cast = (v) => v;
/** 全量 loaders：主包 15 + 分包 7 */
const loaders = {
  ...baseLoaders,
  quotaMatrix: cast(hydrate(require('./data/linkage/quota_matrix.js'))),
  specialMatrix: cast(hydrate(require('./data/linkage/special_matrix.js'))),
  batch2Scores: cast(hydrate(require('./data/linkage/batch2_scores.js'))),
  districtQuota: cast(hydrate(require('./data/linkage/district_quota.js'))),
  sites: cast(hydrate(require('./data/registry/sites.js'))),
  brandGroups: cast(hydrate(require('./data/registry/brand_groups.js'))),
  educationGroups: cast(hydrate(require('./data/registry/education_groups_2026.js'))),
};
const repository = createRepository(loaders);

const STAGE_SHORT = { primary: '小学', middle: '初中', high: '高中' };
/** Web 路由风格 to（/school/xxx?stage=yy）→ 小程序页面参数 */
function parseSchoolTo(to) {
  const m = /^\/school\/([^?]+)(?:\?stage=(\w+))?$/.exec(to || '');
  if (!m) return null;
  let name = m[1];
  try { name = decodeURIComponent(name); } catch (e) { /* 未编码中文原样 */ }
  return { name, stage: m[2] || '' };
}

Page({
  data: {
    model: null,
    linkage: null,
    activeStage: 'primary',
    STAGE_SHORT,
  },

  onLoad(query) {
    this.name = decodeURIComponent(query.name || '');
    this.stageParam = query.stage || '';
    // 先以 primary 构建拿 availableStages（完中多学部），再按 query.stage 或首个可用学部激活
    const probe = buildDetailModel('primary', this.name, repository);
    const stages = probe.availableStages;
    let active = 'primary';
    if (stages.length) {
      if (this.stageParam && stages.indexOf(this.stageParam) > -1) active = this.stageParam;
      else active = stages[0];
    }
    this.applyStage(active);
  },

  applyStage(stage) {
    const model = buildDetailModel(stage, this.name, repository);
    const rawLinkage = stage === 'middle' || stage === 'high'
      ? buildLinkageModel(stage, this.name, repository)
      : null;
    // WXML 表达式不支持 join，预计算覆盖行所在区文本
    const linkage = rawLinkage
      ? {
          ...rawLinkage,
          highCoverage: rawLinkage.highCoverage.map((r) => ({
            ...r,
            districtsText: r.districts.join('、') || '—',
          })),
        }
      : null;
    wx.setNavigationBarTitle({ title: this.name });
    this.setData({ model, linkage, activeStage: stage });
  },

  switchStage(e) { this.applyStage(e.currentTarget.dataset.stage); },

  viewOnMap() {
    wx.navigateTo({ url: `/pages/map/map?focus=${encodeURIComponent(this.name)}` });
  },
  goBack() {
    wx.navigateBack({ delta: 1, fail: () => wx.reLaunch({ url: '/pages/map/map' }) });
  },

  /** 详情页内跳转：feed 初中/小学、品牌行、覆盖初中（Web 路由风格 to） */
  goSchool(e) {
    const hit = parseSchoolTo(e.currentTarget.dataset.to);
    if (!hit) return;
    wx.navigateTo({ url: `/pages/school-detail/index?name=${encodeURIComponent(hit.name)}&stage=${hit.stage}` });
  },
});
