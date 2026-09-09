import { createRouter, createWebHashHistory } from 'vue-router';
import HomeView from './pages/HomeView.vue';
import MapView from './pages/MapView.vue';
import SupportView from './pages/SupportView.vue';

export const router = createRouter({
  // hash 模式：构建产物支持 file:// 直接打开与任意静态路径部署
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/map', name: 'map', component: MapView },
    { path: '/support', name: 'support', component: SupportView },
  ],
});
