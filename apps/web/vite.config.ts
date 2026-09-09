import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// base: './' —— 产物可部署到任意子路径，配合 hash 路由支持 file:// 直接打开
export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: {
    alias: { '@': new URL('./src', import.meta.url).pathname },
  },
  server: {
    open: false,
    fs: { allow: ['../..'] },
  },
});
