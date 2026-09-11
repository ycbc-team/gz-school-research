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

/** 主包列裁剪映射（与 compact.mjs MP_TRIM 同步）：比较时对真源做同款裁剪 */
const MP_TRIM = {
  'primary/xiaoshengchu_2026': ['source_note', 'source_url'],
};

function trimKeys(o, keys) {
  if (Array.isArray(o)) return o.map((e) => trimKeys(e, keys));
  if (o && typeof o === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(o)) if (!keys.includes(k)) out[k] = trimKeys(v, keys);
    return out;
  }
  return o;
}

const MP = join(ROOT, 'apps', 'miniprogram', 'data');
const MP_SUB = join(ROOT, 'apps', 'miniprogram', 'pages', 'school-detail', 'data');
const WEB = join(ROOT, 'apps', 'web', 'src', 'data', 'compact');
const DATA = join(ROOT, 'data');
let fail = 0;
let total = 0;

function checkOne(rel, restored, trim) {
  const jsonPath = join(DATA, rel + '.json');
  if (!exists(jsonPath)) return;
  const original = JSON.parse(readFileSync(jsonPath, 'utf8'));
  const expected = trim ? trimKeys(original, trim) : original;
  total += 1;
  if (!deepEqual(expected, restored)) {
    fail += 1;
    console.error(`❌ ${rel}: 水合还原与真源${trim ? '（主包裁剪子集）' : ''}不一致`);
  }
}

// CJS 产物（小程序主包，含列裁剪）+ 分包
for (const js of walk(MP)) {
  if (!js.endsWith('.js')) continue;
  const rel = relative(MP, js).replace(/\.js$/, '');
  checkOne(rel, hydrate(require(js)), MP_TRIM[rel]);
}
for (const js of walk(MP_SUB)) {
  if (!js.endsWith('.js')) continue;
  checkOne(relative(MP_SUB, js).replace(/\.js$/, ''), hydrate(require(js)));
}
// ESM 产物（Web，全量无裁剪）
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
