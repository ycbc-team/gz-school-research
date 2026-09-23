import { createRouter, createWebHashHistory } from 'vue-router';

export const router = createRouter({
  // hash 模式：构建产物支持 file:// 直接打开与任意静态路径部署
  history: createWebHashHistory(),
  routes: [
    // 页面和其数据域一起按路由加载；首页不为地图/详情/排行提前下载完整快照。
    { path: '/', name: 'home', component: () => import('./pages/HomeView.vue') },
    { path: '/map', name: 'map', component: () => import('./pages/MapView.vue') },
    { path: '/policy', name: 'policy', component: () => import('./pages/PolicyView.vue') },
    { path: '/linkage', name: 'linkage', component: () => import('./pages/LinkageView.vue') },
    { path: '/middle', name: 'ranking', component: () => import('./pages/RankingView.vue') },
    { path: '/high', name: 'high-ranking', component: () => import('./pages/HighRankingView.vue') },
    { path: '/awards', name: 'awards', component: () => import('./pages/AwardsView.vue') },
    { path: '/school/:name', name: 'school-detail', component: () => import('./pages/SchoolDetailView.vue'), props: true },
    // 旧路径 /school/:stage/:name 重定向到合并路由（stage 作初始 tab）
    { path: '/school/:stage/:name', redirect: (to) => ({ path: `/school/${to.params.name}`, query: { stage: to.params.stage } }) },
  ],
  // 详情页跳转后回到顶部；浏览器后退/前进恢复原滚动位置。
  // 学校详情页「见说明N」链接带 ?explain=N：不在 scrollBehavior 里定位（懒加载组件
  // 初始导航时 el 定位不可靠，且 { top: 0 } 会覆盖组件滚动），让位给 PolicyView
  // onMounted/watch 负责 scrollIntoView。
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (to.name === 'policy' && to.query.explain) return undefined;
    return { top: 0 };
  },
});
