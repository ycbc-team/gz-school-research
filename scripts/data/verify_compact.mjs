/**
 * 紧凑产物一致性验证：apps/miniprogram/data（CJS）与 apps/web/src/data/compact（ESM）
 * 的紧凑模块 hydrate 还原后，与 data/ 真源 JSON 语义深比较（键序无关；数组顺序敏感）。
 * 失败退出码 1。运行：node scripts/data/verify_compact.mjs（build:mp 后自动执行）
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const require = createRequire(import.meta.url);
const { hydrate } = require(join(ROOT, 'packages/shared/dist/cjs/compact.js'));

function walk(dir) {
  const out = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}

/** 语义深比较：对象键序无关，数组顺序敏感，标量用 Object.is */
function deepEqual(a, b) {
  if (Object.is(a, b)) return true;
  if (typeof a !== typeof b) return false;
  if (Array.isArray(a)) {
    return Array.isArray(b) && a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  }
  if (a && b && typeof a === 'object') {
    const ka = Object.keys(a);
    const kb = Object.keys(b);
    return ka.length === kb.length && ka.every((k) => k in b && deepEqual(a[k], b[k]));
  }
  return false;
}

function exists(p) {
  try { statSync(p); return true; } catch { return false; }
}

const MP = join(ROOT, 'apps', 'miniprogram', 'data');
const WEB = join(ROOT, 'apps', 'web', 'src', 'data', 'compact');
const DATA = join(ROOT, 'data');
let fail = 0;
let total = 0;

function checkOne(rel, restored) {
  const jsonPath = join(DATA, rel + '.json');
  if (!exists(jsonPath)) return;
  const original = JSON.parse(readFileSync(jsonPath, 'utf8'));
  total += 1;
  if (!deepEqual(original, restored)) {
    fail += 1;
    console.error(`❌ ${rel}: 水合还原与真源不一致`);
  }
}

// CJS 产物（小程序）
for (const js of walk(MP)) {
  if (!js.endsWith('.js')) continue;
  checkOne(relative(MP, js).replace(/\.js$/, ''), hydrate(require(js)));
}
// ESM 产物（Web）
for (const js of walk(WEB)) {
  if (!js.endsWith('.js')) continue;
  const mod = await import(pathToFileURL(js).href);
  checkOne(relative(WEB, js).replace(/\.js$/, ''), hydrate(mod.default));
}

if (fail) {
  console.error(`[verify_compact] ${fail}/${total} 个文件不一致`);
  process.exit(1);
}
console.log(`[verify_compact] ✅ ${total} 个紧凑模块（CJS ${total > 0 ? '小程序' : ''} + ESM Web）水合还原与真源语义等价`);
