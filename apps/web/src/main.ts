import { createApp } from 'vue';
import App from './App.vue';
import { router } from './router';
import { startVersionCheck } from './versionCheck';
import './styles.css';

createApp(App).use(router).mount('#app');

// 生产环境开启发版检测：发现新版直接 reload（file:// 打开时自动跳过）
if (import.meta.env.PROD) {
  startVersionCheck();
}
