/**
 * 紧凑数据编译：真源 JSON → 小程序紧凑 JS 模块（体积治理）。
 *
 * 结构约定（与 packages/shared/src/compact.ts 的 hydrate 对称）：
 * - 记录数组（元素全为对象）→ { $cols, $rows, $dicts? }
 *   - $cols：全部键的并集（按首次出现顺序）
 *   - $rows：定长行数组，按 $cols 顺序取值；缺失列 = undefined（JS 稀疏，序列化输出空位），
 *     显式 null 保留 null
 *   - $dicts：可选字段字典（高重复值字段，如 group/source_url）；行内存索引，null 不索引
 * - 其余结构原样保留（标量/嵌套对象/非对象数组），标量直接输出
 *
 * 产物为 JS 字面量（非 JSON）：数组稀疏空位依赖 JS 语法，JSON.stringify 会丢 undefined。
 *
 * 运行：node scripts/data/compact.mjs
 * 输出：apps/miniprogram/data/**（git 忽略，由 build.mjs 的构建链路生成）
 */
import { readFileSync, writeFileSync, mkdirSync, readdirSync, statSync, rmSync } from 'node:fs';
import { dirname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const DATA_SRC = join(ROOT, 'data');
const OUT_CJS_MAIN = process.argv[2] || join(ROOT, 'apps', 'miniprogram', 'data');
const OUT_CJS_SUB = process.argv[3] || join(ROOT, 'apps', 'miniprogram', 'pages', 'school-detail', 'data');
const OUT_ESM = process.argv[4] || join(ROOT, 'apps', 'web', 'src', 'data', 'compact');

/** 高重复值字段 → 字典化（值唯一数少才启用） */
const DICT_SPEC = {
  'data/primary/xiaoshengchu_2026.json': { dicts: ['group', 'source_url'] },
};

/**
 * 编译清单：
 * - WEB_TARGETS：Web 端全部消费（apps/web/src/data/index.ts import 全量，bundle gzip 传输 178KB）
 * - MP_TARGETS：小程序主包当前消费（3 页：index/map/support；主包 ≤2MB）。未消费文件
 *   （详情页/通道页数据）等对应页面落地时加入并配分包。
 */
function walkJson(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry);
    if (statSync(p).isDirectory()) out.push(...walkJson(p));
    else if (p.endsWith('.json')) out.push(p);
  }
  return out;
}
const WEB_TARGETS = walkJson(DATA_SRC)
  .filter((p) => !p.split(sep).some((seg) => seg === 'raw' || seg === '_raw'))
  .map((p) => relative(ROOT, p));
// 小程序主包数据（地图页 + 首页/支撑度消费）：POI/tier1/levels/招生/实体/升学路线
const MP_MAIN_TARGETS = [
  'data/primary/schools-gz.json',
  'data/primary/tier1_schools_all.json',
  'data/primary/xiaoshengchu_2026.json',
  'data/middle/schools-gz.json',
  'data/middle/tier1_schools_all.json',
  'data/high/schools-gz.json',
  'data/high/levels.json',
  'data/primary/enrollments/2026-tianhe.json',
  'data/primary/enrollments/2026-yuexiu.json',
  'data/primary/enrollments/2026-haizhu.json',
  'data/primary/enrollments/2026-liwan.json',
  'data/primary/enrollments/2026-panyu.json',
  'data/primary/enrollments/2026-baiyun.json',
  'data/primary/enrollments/2026-huangpu.json',
  'data/registry/entities.json',
];
// 小程序分包数据（school-detail 详情页专用）：升学通道/身份/品牌/教育集团
const MP_SUB_TARGETS = [
  'data/linkage/quota_matrix.json',
  'data/linkage/special_matrix.json',
  'data/linkage/batch2_scores.json',
  'data/linkage/district_quota.json',
  'data/registry/sites.json',
  'data/registry/brand_groups.json',
  'data/registry/education_groups_2026.json',
];

/* ---------- JS 字面量序列化（保留 undefined 稀疏空位） ---------- */
function jsLiteral(v) {
  if (v === undefined) return ''; // 数组稀疏空位
  if (v === null) return 'null';
  const t = typeof v;
  if (t === 'number' || t === 'boolean') return String(v);
  if (t === 'string') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(jsLiteral).join(',') + ']';
  const parts = Object.entries(v).map(([k, val]) => JSON.stringify(k) + ':' + jsLiteral(val));
  return '{' + parts.join(',') + '}';
}

/* ---------- 编译 ---------- */
function compileRows(rows, dictFields) {
  // 键并集（首次出现顺序）
  const cols = [];
  const seen = new Set();
  for (const r of rows) {
    for (const k of Object.keys(r)) {
      if (!seen.has(k)) { seen.add(k); cols.push(k); }
    }
  }
  // 字典：唯一值数 < 行数/3 才有收益
  const dicts = {};
  const dictMaps = {};
  for (const df of dictFields) {
    if (!seen.has(df)) continue;
    const uniq = [];
    const um = new Map();
    for (const r of rows) {
      const v = r[df];
      if (v !== null && v !== undefined && !um.has(v)) { um.set(v, uniq.length); uniq.push(v); }
    }
    if (uniq.length * 3 < rows.length) { dicts[df] = uniq; dictMaps[df] = um; }
  }
  const outRows = rows.map((r) => {
    const row = new Array(cols.length);
    for (let i = 0; i < cols.length; i += 1) {
      const c = cols[i];
      if (!(c in r)) continue; // 缺失列 → undefined（稀疏空位）
      const v = r[c];
      if (v === null) { row[i] = null; continue; }
      const um = dictMaps[c];
      if (um) { row[i] = um.get(v); continue; }
      row[i] = compileValue(v);
    }
    return row;
  });
  const out = { $cols: cols, $rows: outRows };
  if (Object.keys(dicts).length) out.$dicts = dicts;
  return out;
}

function compileValue(v, dictFields = []) {
  if (v === null || typeof v !== 'object') return v;
  if (Array.isArray(v)) {
    // 记录数组（元素全为对象）→ 列式化；否则逐元素递归
    if (v.length > 0 && v.every((e) => typeof e === 'object' && e !== null && !Array.isArray(e))) {
      return compileRows(v, dictFields);
    }
    return v.map((e) => compileValue(e));
  }
  const out = {};
  for (const [k, val] of Object.entries(v)) {
    // 字典字段仅作用于顶层 records 数组
    out[k] = compileValue(val, k === 'records' ? dictFields : []);
  }
  return out;
}

/* ---------- 主流程 ---------- */
for (const dir of [OUT_CJS_MAIN, OUT_CJS_SUB, OUT_ESM]) {
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
}

/** 编译单个真源文件到目标目录，fmt: 'cjs' | 'esm' */
function emit(file, outDir, fmt) {
  const abs = join(ROOT, file);
  const relPath = relative(DATA_SRC, abs);
  const json = JSON.parse(readFileSync(abs, 'utf8'));
  const dictFields = DICT_SPEC[file]?.dicts || [];
  const compact = compileValue(json, dictFields);
  const literal = jsLiteral(compact);
  const out = join(outDir, relPath.replace(/\.json$/, '.js'));
  mkdirSync(dirname(out), { recursive: true });
  if (fmt === 'cjs') {
    writeFileSync(out, '// 由 scripts/data/compact.mjs 从 data/' + relPath + ' 编译（紧凑列式），勿手改\nmodule.exports = ' + literal + ';\n', 'utf8');
  } else {
    writeFileSync(out, '// 由 scripts/data/compact.mjs 从 data/' + relPath + ' 编译（紧凑列式），勿手改\nconst data = ' + literal + ';\nexport default data;\n', 'utf8');
    writeFileSync(out.replace(/\.js$/, '.d.ts'), 'declare const data: unknown;\nexport default data;\n', 'utf8');
  }
  return { file: relPath, jsonKB: readFileSync(abs, 'utf8').length / 1024, jsKB: readFileSync(out, 'utf8').length / 1024 };
}

const stats = [];
for (const file of MP_MAIN_TARGETS) stats.push(emit(file, OUT_CJS_MAIN, 'cjs'));
for (const file of MP_SUB_TARGETS) stats.push(emit(file, OUT_CJS_SUB, 'cjs'));
for (const file of WEB_TARGETS) stats.push(emit(file, OUT_ESM, 'esm'));

stats.sort((a, b) => b.jsKB - a.jsKB);
let sumJ = 0;
let sumC = 0;
console.log(`[compact] ${stats.length} 个文件 → ${relative(ROOT, OUT_CJS_MAIN)}(主包) + ${relative(ROOT, OUT_CJS_SUB)}(分包) + ${relative(ROOT, OUT_ESM)}(web)`);
for (const s of stats) {
  sumJ += s.jsonKB;
  sumC += s.jsKB;
  const pct = ((1 - s.jsKB / s.jsonKB) * 100).toFixed(0);
  console.log(`  ${s.file.padEnd(46)} ${s.jsonKB.toFixed(1).padStart(7)}K → ${s.jsKB.toFixed(1).padStart(7)}K  (-${pct}%)`);
}
console.log(`  ${'合计'.padEnd(46)} ${sumJ.toFixed(1).padStart(7)}K → ${sumC.toFixed(1).padStart(7)}K  (-${((1 - sumC / sumJ) * 100).toFixed(0)}%)`);
