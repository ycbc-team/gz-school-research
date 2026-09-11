/**
 * 微信小程序构建脚本（生成产物，勿手改）：
 *   1. 拷贝 packages/shared/dist/cjs → apps/miniprogram/shared/
 *   2. 数据编译：调用 scripts/data/compact.mjs 把 data/**​/*.json（唯一真源）编译为
 *      紧凑列式 CommonJS 模块 → apps/miniprogram/data/（小程序端加载后经 hydrate 还原）
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

// 1) shared cjs
const sharedDest = join(MP, 'shared');
rmSync(sharedDest, { recursive: true, force: true });
mkdirSync(sharedDest, { recursive: true });
cpSync(SHARED_SRC, sharedDest, { recursive: true });

// 2) data json → 紧凑列式 js 模块（compact.mjs 内部自清空重生成 apps/miniprogram/data）
execSync('node scripts/data/compact.mjs', { cwd: ROOT, stdio: 'inherit' });

// 3) 水合一致性验证：紧凑产物还原 === 真源（键序无关深比较）
execSync('node scripts/data/verify_compact.mjs', { cwd: ROOT, stdio: 'inherit' });

// 4) marker 图标生成：shared STAGE_COLOR 唯一真源 → 7 张 PNG（单学部 3 + 多学部 4）
execSync('node scripts/miniprogram/gen-markers.mjs', { cwd: ROOT, stdio: 'inherit' });

console.log(`[miniprogram] shared → ${relative(ROOT, sharedDest)}/`);
console.log(`[miniprogram] data 紧凑 js 模块 → apps/miniprogram/data/`);
