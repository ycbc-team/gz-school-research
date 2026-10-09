/**
 * 学校详情页：整屏宿主，渲染 school-card 组件（context="page"）。
 * 所有详情渲染与全屏交互均在组件内完成；本页只解析路由参数并透传。
 * 关联校区链接在 page 上下文由组件 redirectTo 到该校详情页（不堆叠页面）。
 */
Page({
  data: {
    schoolId: '',
    name: '',
    stage: '',
  },
  onLoad(query) {
    this.setData({
      name: decodeURIComponent(query.name || ''),
      stage: query.stage || '',
      schoolId: query.id || '',
    });
  },
});
