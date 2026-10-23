/**
 * 微信官方隐私授权（需求文档 13.3「合规硬动作」第 ② 条）
 *
 * 首次调用 wx.getLocation 之前先触发官方隐私授权弹窗（wx.requirePrivacyAuthorize，基础库 ≥ 2.32.3）。
 * 说明：
 *  · 后台《用户隐私保护指引》已配置时，微信会在此弹出官方隐私弹窗；用户未同意，后续位置类 API 会自行失败。
 *  · 基础库过低（无此 API）或后台尚未配置时，这里不阻断主流程 —— 真正的系统授权弹窗仍由 getLocation 兜底，
 *    避免「隐私接口不可用 → 定位功能整体不可用」。
 *  · 无论如何都 resolve，调用方只需 `.then(...)` 继续原有定位逻辑。
 */
function ensurePrivacy() {
  return new Promise((resolve) => {
    if (typeof wx.requirePrivacyAuthorize !== 'function') { resolve(true); return; }
    wx.requirePrivacyAuthorize({
      success: () => resolve(true),
      fail: () => resolve(false),
      complete: () => {},
    });
  });
}

module.exports = { ensurePrivacy };
