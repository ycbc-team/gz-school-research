/**
 * 声明 tab 落地页（L0，底部 tabBar 第 3 项）
 *
 * UI 稿 04 节 L0：顶部完全沿用现网样式（状态栏 + 品牌名「广州学途」+ 微信系统胶囊，
 * 不自绘标题栏、不加返回键）；品牌行下方两行文件入口直接平铺在白底上（无外层卡片、
 * 仅行间 1px 分割线），一行一条、右侧 ›，整行为热区。
 * 两页文件均为普通页面（非 tab 页），wx.navigateTo 进入，返回由文件页顶栏承担。
 */
const { navMetrics } = require('../../utils/nav.js');

Page({
  data: {
    capTop: 26,
  },

  onLoad() {
    const m = navMetrics();
    this.setData({ capTop: m.capTop });
  },

  onShow() {
    // 自定义 tabBar：第 3 项「声明」高亮，并确保不被上个页面的弹层残留隐藏
    const tab = this.getTabBar && this.getTabBar();
    if (tab) tab.setData({ selected: 2, hidden: false });
  },

  openPolicy() {
    wx.navigateTo({ url: '/pages/policy/policy' });
  },

  openPrivacy() {
    wx.navigateTo({ url: '/pages/privacy/privacy' });
  },
});
