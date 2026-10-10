import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineConfig, type Plugin, type ResolvedConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// base: './' —— 产物可部署到任意子路径，配合 hash 路由支持 file:// 直接打开
export default defineConfig({
  base: './',
  plugins: [vue(), versionJsonPlugin()],
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

/**
 * 发版检测配套：构建结束时生成 dist/version.json。
 *
 * version = index.html 内容（其引用的 JS/CSS 均为内容 hash 命名）的 sha256 摘要——
 * 任何代码/数据变更都会改变引用的资源文件名 → index.html 变化 → version 变化；
 * 产物未变时重复构建 version 保持稳定（builtAt 仅作信息）。
 *
 * 前端（src/versionCheck.ts）轮询比对 version，发现新版即 reload，
 * 解决 GitHub Pages 整体替换后旧页面引用旧 chunk 404、点击跳转失效的问题。
 */
function versionJsonPlugin(): Plugin {
  let config: ResolvedConfig | null = null;
  return {
    name: 'gz-version-json',
    apply: 'build',
    configResolved(cfg) {
      config = cfg;
    },
    closeBundle() {
      const outDir = config?.build.outDir ?? 'dist';
      const indexPath = resolve(outDir, 'index.html');
      if (!existsSync(indexPath)) return;
      const version = createHash('sha256')
        .update(readFileSync(indexPath))
        .digest('hex')
        .slice(0, 12);
      writeFileSync(
        resolve(outDir, 'version.json'),
        JSON.stringify(
          { version, builtAt: new Date().toISOString() },
          null,
          2,
        ) + '\n',
      );
    },
  };
}
