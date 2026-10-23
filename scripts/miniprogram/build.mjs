/**
 * 微信小程序构建脚本（生成产物，勿手改）：
 *   1. 拷贝 packages/shared/dist/cjs → apps/miniprogram/shared/
 *   2. 数据编译：调用 scripts/data/compact.mjs 把 data/**​/*.json（唯一真源）编译为
 *      紧凑列式 CommonJS 模块 → apps/miniprogram/data/（小程序端加载后经 hydrate 还原）
 *   3. marker 图标生成：首页 assets/markers-index/（14 张 PNG）
 * 运行：node scripts/miniprogram/build.mjs（或 npm run build:mp）
 * 前置：先跑 npm run build:shared（@gz/shared 双产物）
 */
import { execSync } from 'node:child_process';
import { cpSync, mkdirSync, rmSync, existsSync } from 'node:fs';
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

// 3.5) 区域/地铁数据源（UI 04/04B 三列下钻）校验：
// 产出已由 compact.mjs 在清空 data 后自行完成（单跑 compact / npm run check 也不会丢，避免白屏）。
// 这里只做存在性断言，防止上游改写后静默缺失。
const regionDest = join(MP, 'data', 'region');
for (const name of ['plates', 'metro']) {
  if (!existsSync(join(regionDest, `${name}.js`))) {
    throw new Error(`[miniprogram] 缺少 data/region/${name}.js —— compact.mjs 未产出，页面 require 会白屏`);
  }
}
console.log(`[miniprogram] 区域/地铁数据校验通过 → ${relative(ROOT, regionDest)}/`);

// 4) marker 图标生成：首页（UI 稿《知性蓝》学段分色唯一真源）→ apps/miniprogram/assets/markers-index/（14 张 PNG）
execSync('node scripts/miniprogram/gen-markers-index.mjs', { cwd: ROOT, stdio: 'inherit' });

console.log(`[miniprogram] shared → ${relative(ROOT, sharedDest)}/`);
console.log(`[miniprogram] data 紧凑 js 模块 → apps/miniprogram/data/`);
