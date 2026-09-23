/**
 * 微信小程序构建脚本（生成产物，勿手改）：
 *   1. 拷贝 packages/shared/dist/cjs → apps/miniprogram/shared/
 *   2. 数据编译：调用 scripts/data/compact.mjs 把 data/**​/*.json（唯一真源）编译为
 *      紧凑列式 CommonJS 模块 → apps/miniprogram/data/（小程序端加载后经 hydrate 还原）
 *   3. marker 图标生成：map 页 assets/markers/ ＋ 首页 assets/markers-index/（各 14 张 PNG）
 * 运行：node scripts/miniprogram/build.mjs（或 npm run build:mp）
 * 前置：先跑 npm run build:shared（@gz/shared 双产物）
 */
import { execSync } from 'node:child_process';
import { cpSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const MP = join(ROOT, 'apps', 'miniprogram');
const SHARED_SRC = join(ROOT, 'packages', 'shared', 'dist', 'cjs');

// 1) shared cjs：dist 是 gitignore 产物，构建自身必须保证前置条件，不能依赖调用者先手动执行。
execSync('npm run build -w @gz/shared', { cwd: ROOT, stdio: 'inherit' });
const sharedDest = join(MP, 'shared');
rmSync(sharedDest, { recursive: true, force: true });
mkdirSync(sharedDest, { recursive: true });
cpSync(SHARED_SRC, sharedDest, { recursive: true });

// 2) data json → 紧凑列式 js 模块（compact.mjs 内部自清空重生成 apps/miniprogram/data）
execSync('node scripts/data/compact.mjs', { cwd: ROOT, stdio: 'inherit' });

// 3) 水合一致性验证：紧凑产物还原 === 真源（键序无关深比较）
execSync('node scripts/data/verify_compact.mjs', { cwd: ROOT, stdio: 'inherit' });

// 4) marker 图标生成：map 页（shared STAGE_COLOR 唯一真源）→ 14 张 PNG（普通 + 选中态两套，单学部 3 + 多学部 4）
execSync('node scripts/miniprogram/gen-markers.mjs', { cwd: ROOT, stdio: 'inherit' });

// 5) 首页 marker 图标生成：UI 稿《知性蓝》学段分色（与 map 页分开的独立真源，勿混用）→ apps/miniprogram/assets/markers-index/
execSync('node scripts/miniprogram/gen-markers-index.mjs', { cwd: ROOT, stdio: 'inherit' });

console.log(`[miniprogram] shared → ${relative(ROOT, sharedDest)}/`);
console.log(`[miniprogram] data 紧凑 js 模块 → apps/miniprogram/data/`);
