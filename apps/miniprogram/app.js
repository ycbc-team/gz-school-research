const data = require('./utils/data.js');

App({
  // 主包 shared（构建函数）/ baseLoaders（数据）注入全局，供分包 school-card 组件运行时读取，
  // 避免分包组件跨包 require 主包模块（会触发 componentPlaceholder 异步单组件注入路径的 i.functions 崩溃）。
  globalData: {
    shared: data.shared,
    baseLoaders: data.baseLoaders,
  },
  onLaunch() {
    // 预热详情分包（pages/school-detail）。主通道是 app.json 的 preloadRule（官方只支持配置式预下载）；
    // 这里再用 require.async 做一次运行时预热（【注意】小程序运行时没有 wx.loadSubpackage——
    // 那是小游戏 API；正确的分包异步加载通道是 require.async，基础库 ≥2.17.3，下载+执行+Promise 回调）。
    // 就绪后记入 globalData.detailSubReady 供各页面同步查询（避免各页重复预热/回调丢失）。
    try {
      require.async('./pages/school-detail/components/school-card/index')
        .then(() => { this.globalData.detailSubReady = true; })
        .catch(() => { /* 预热失败：首页点学校时会再次尝试 */ });
    } catch (e) { /* 预热失败不影响主包使用 */ }
  },
});
