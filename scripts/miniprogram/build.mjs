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
import { cpSync, mkdirSync, rmSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
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

// 3.5) 区域/地铁数据源（UI 04/04B 三列下钻）：data/region/*.json → apps/miniprogram/data/region/*.js
// 注意：compact.mjs 会自清空 apps/miniprogram/data/，故必须在 compact 之后生成；该目录 git 忽略（构建产物）。
// 微信小程序 require 不能可靠加载显式 .json 扩展名（会回退 .json.js 报 not defined），故此处直接产出
// .js 模块（与 data/ 下其余紧凑模块一致），页面以无扩展名 require 加载。compact.mjs 走显式源登记表，
// 不会处理 data/region/*，因此本步是 region 数据的唯一生产者。
const regionSrc = join(ROOT, 'data', 'region');
const regionDest = join(MP, 'data', 'region');
if (existsSync(regionSrc)) {
  mkdirSync(regionDest, { recursive: true });
  for (const name of ['plates', 'metro']) {
    const jsonPath = join(regionSrc, `${name}.json`);
    if (!existsSync(jsonPath)) continue;
    const json = readFileSync(jsonPath, 'utf8');
    JSON.parse(json); // 构建期校验合法 JSON，非法立即抛错
    writeFileSync(join(regionDest, `${name}.js`), `module.exports = ${json};\n`, 'utf8');
  }
  console.log(`[miniprogram] 区域/地铁数据 → ${relative(ROOT, regionDest)}/ (plates.js, metro.js)`);
}

// 4) marker 图标生成：首页（UI 稿《知性蓝》学段分色唯一真源）→ apps/miniprogram/assets/markers-index/（14 张 PNG）
execSync('node scripts/miniprogram/gen-markers-index.mjs', { cwd: ROOT, stdio: 'inherit' });

console.log(`[miniprogram] shared → ${relative(ROOT, sharedDest)}/`);
console.log(`[miniprogram] data 紧凑 js 模块 → apps/miniprogram/data/`);
