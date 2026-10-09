App({
  onLaunch() {
    // 预加载详情页分包（pages/school-detail）：点学校打开半窗卡时无分包下载等待。
    // preloadSubPackage 返回 task 需手动 .load()；旧版 loadSubPackage 直接开始，二者兼容。
    const pre = (typeof wx.preloadSubPackage === 'function')
      ? wx.preloadSubPackage
      : (typeof wx.loadSubPackage === 'function' ? wx.loadSubPackage : null);
    if (pre) {
      try {
        const task = pre({ name: 'pages/school-detail', success() {}, fail() {} });
        if (task && typeof task.load === 'function') task.load();
      } catch (e) { /* 预加载失败不影响主包使用 */ }
    }
  },
});
