/**
 * 顶栏度量 + 全局返回行为（全稿唯一实现，各页禁止各写一套）
 *
 * navMetrics()  —— 返回按钮 / 品牌行所用的顶栏基准：
 *                   capTop = 右上角微信胶囊 top（胶囊不可用时退化为 statusBarHeight + 6）
 *                   capH   = 胶囊高（默认 32）
 *                   backTop= 32×32 返回圆在胶囊内垂直居中的 top（= capTop + (capH - 32) / 2）
 *
 * goBack()       —— 点按 = wx.navigateBack()；页面栈无上一页（分享卡片 / 扫码直达）时
 *                   兜底 switchTab 回「声明」页，保证永远有退路。
 */
function navMetrics() {
  let statusBarHeight = 20;
  let capTop = 0;
  let capH = 32;

  try {
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    statusBarHeight = win.statusBarHeight || 20;
  } catch (e) { /* 用默认状态栏高度 */ }

  try {
    if (typeof wx.getMenuButtonBoundingClientRect === 'function') {
      const cap = wx.getMenuButtonBoundingClientRect();
      if (cap && cap.height && cap.top >= statusBarHeight) {
        capTop = cap.top;
        capH = cap.height;
      }
    }
  } catch (e) { /* 用近似值 */ }

  if (!capTop) capTop = statusBarHeight + 6;

  return {
    statusBarHeight,
    capTop,
    capH,
    backTop: capTop + Math.max((capH - 32) / 2, 0),
  };
}

function goBack(fallback) {
  const url = fallback || '/pages/statement/statement';
  wx.navigateBack({
    delta: 1,
    fail: () => { wx.switchTab({ url }); },
  });
}

module.exports = { navMetrics, goBack };
