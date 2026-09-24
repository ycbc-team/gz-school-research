import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// base: './' —— 产物可部署到任意子路径，配合 hash 路由支持 file:// 直接打开
export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: {
    // 开发预览始终使用当前 worktree 的共享源码，避免多 worktree 共用 node_modules 时误加载另一分支构建产物。
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
      '@gz/shared': new URL('../../packages/shared/src/index.ts', import.meta.url).pathname,
    },
  },
  server: {
    open: false,
    fs: { allow: ['../..'] },
  },
});
