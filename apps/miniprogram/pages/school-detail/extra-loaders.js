/**
 * 主包迁出的重数据聚合（源码，非构建产物，不被 compact.mjs 清空）。
 * 依赖 pages/school-detail/data/ 下由 compact.mjs 生成的模块。
 *
 * 消费方：
 *   - 学校页 pages/school/school.js（主包页面）：onLoad 经 require.async 拉取，hydrate 后并入 fullBaseLoaders
 *     （小学/高中默认态、初中 RankingView 所需数据）。
 *   - app.js onLaunch：合并进 globalData.baseLoaders，供分包 school-card 详情卡读取全量数据。
 *
 * 仅 require 同分包 data 模块（不 cross-require 主包 shared），hydrate 由调用方用主包 shared 完成，
 * 避免分包同步依赖主包模块在 componentPlaceholder 注入路径下崩溃。
 */
module.exports = {
  rawExtra: {
    // 小学 2026 招生计划（7 区）
    enrollments: require('./data/primary/enrollments/2026-all'),
    // 小学 2026 升学路线事实表
    xiaoshengchu: require('./data/primary/xiaoshengchu_2026'),
    // 高中统招录取分数（2025 / 2026）
    highScores2025: require('./data/high/cutoff_score/dist/scores_2025'),
    highScores2026: require('./data/high/cutoff_score/dist/scores_2026'),
    // 初中升学信号（自招/指标/特控率）— 学校页 RankingView
    rankingMiddle: require('./data/linkage/ranking_middle'),
    quotaMatrix: require('./data/linkage/quota_matrix'),
    quotaOutcome: require('./data/linkage/quota_outcome'),
    // 初中 2026 招生计划
    middleEnrollment2026: require('./data/middle/enrollment/dist/middle_enrollment_2026'),
  },
};
