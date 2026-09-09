/**
 * 微信小程序构建脚本（生成产物，勿手改）：
 *   1. 拷贝 packages/shared/dist/cjs → apps/miniprogram/shared/
 *   2. 把 data/**​/*.json（唯一真源）转换为 CommonJS 模块 → apps/miniprogram/data/
 * 运行：node scripts/miniprogram/build.mjs（或 npm run build:mp）
 */
import { execSync } from 'node:child_process';
import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const MP = join(ROOT, 'apps', 'miniprogram');
const SHARED_SRC = join(ROOT, 'packages', 'shared', 'dist', 'cjs');
const DATA_SRC = join(ROOT, 'data');

// 1) shared cjs
const sharedDest = join(MP, 'shared');
rmSync(sharedDest, { recursive: true, force: true });
mkdirSync(sharedDest, { recursive: true });
cpSync(SHARED_SRC, sharedDest, { recursive: true });

// 2) data json -> js module（保留相对结构；跳过 _raw 中间产物与非 json）
const dataDest = join(MP, 'data');
rmSync(dataDest, { recursive: true, force: true });
mkdirSync(dataDest, { recursive: true });

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}

let count = 0;
for (const file of walk(DATA_SRC)) {
  if (!file.endsWith('.json')) continue;
  if (file.split(sep).some((seg) => seg === 'raw' || seg === '_raw')) continue;
  const rel = relative(DATA_SRC, file).replace(/\.json$/, '.js');
  const json = readFileSync(file, 'utf-8');
  const out = join(dataDest, rel);
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(
    out,
    `// 由 scripts/miniprogram/build.mjs 从 data/${relative(DATA_SRC, file)} 生成，勿手改\nmodule.exports = ${json};\n`,
    'utf-8',
  );
  count += 1;
}

console.log(`[miniprogram] shared → ${relative(ROOT, sharedDest)}`);
console.log(`[miniprogram] data js 模块 ${count} 个 → ${relative(ROOT, dataDest)}`);
