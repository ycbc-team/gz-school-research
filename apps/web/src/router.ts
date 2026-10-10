import { createRouter, createWebHashHistory } from 'vue-router';

/**
 * 动态导入失败（部署后旧 chunk 404 等）的领域错误。
 * 原生 import() 失败只给消息字符串，无法结构化判断——这里由 lazy() 统一包装
 * 成带类型的错误，router.onError 用 instanceof 判断，不依赖错误文本。
 */
export class ChunkLoadError extends Error {
  readonly cause?: Error;

  constructor(cause?: unknown) {
    super('路由页面资源加载失败（可能已发布新版本）');
    this.name = 'ChunkLoadError';
    this.cause = cause instanceof Error ? cause : undefined;
  }
}

/** 路由懒加载统一入口：加载失败抛 ChunkLoadError（保留原错误于 cause），供 onError 处理 */
function lazy<T>(loader: () => Promise<T>): () => Promise<T> {
  return () =>
    loader().catch((cause: unknown) => {
      throw new ChunkLoadError(cause);
    });
}

export const router = createRouter({
  // hash 模式：构建产物支持 file:// 直接打开与任意静态路径部署
  history: createWebHashHistory(),
  routes: [
    // 页面和其数据域一起按路由加载；首页不为地图/详情/排行提前下载完整快照。
    { path: '/', name: 'home', component: lazy(() => import('./pages/HomeView.vue')) },
    { path: '/map', name: 'map', component: lazy(() => import('./pages/MapView.vue')) },
    { path: '/linkage', name: 'linkage', component: lazy(() => import('./pages/LinkageView.vue')) },
    { path: '/primary', name: 'primary-ranking', component: lazy(() => import('./pages/PrimaryRankingView.vue')) },
    { path: '/middle', name: 'ranking', component: lazy(() => import('./pages/RankingView.vue')) },
    { path: '/high', name: 'high-ranking', component: lazy(() => import('./pages/HighRankingView.vue')) },
    { path: '/awards', name: 'awards', component: lazy(() => import('./pages/AwardsView.vue')) },
    { path: '/school/:name', name: 'school-detail', component: lazy(() => import('./pages/SchoolDetailView.vue')), props: true },
    // 旧路径 /school/:stage/:name 重定向到合并路由（stage 作初始 tab）
    { path: '/school/:stage/:name', redirect: (to) => ({ path: `/school/${to.params.name}`, query: { stage: to.params.stage } }) },
  ],
  // 详情页跳转后回到顶部；浏览器后退/前进恢复原滚动位置。
  // 明细页筛选/排序同步到 URL 属于同路径仅 query 变化，不应触发滚动（false = 不滚动）。
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (to.path === _from.path) return false;
    return { top: 0 };
  },
});

/**
 * 跳转失败兜底：路由懒加载 chunk 404（部署替换后旧文件消失）→ 刷新到新版。
 * sessionStorage 标记本次会话已自愈过一次：非部署原因的偶发加载失败
 * （网络抖动等）不会触发连环刷新。
 */
router.onError((error) => {
  if (!(error instanceof ChunkLoadError)) return;
  if (sessionStorage.getItem('gz-chunk-reloaded')) return;
  sessionStorage.setItem('gz-chunk-reloaded', '1');
  window.location.reload();
});
