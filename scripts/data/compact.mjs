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
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { dirname, join, relative, sep, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const DATA_SRC = join(ROOT, 'data');
const OUT_CJS_MAIN = process.argv[2] || join(ROOT, 'apps', 'miniprogram', 'data');
const OUT_CJS_SUB = process.argv[3] || join(ROOT, 'apps', 'miniprogram', 'pages', 'school-detail', 'data');
const OUT_ESM = process.argv[4] || join(ROOT, 'apps', 'web', 'src', 'data', 'compact');

/** 高重复值字段 → 字典化（值唯一数少才启用）；listDicts 为数组元素字典（如初中实体 id 列表）。
 * 2026-10-08：xiaoshengchu 记录扁平 feed_school_ids 已删（feed 只以机制分组形态
 * feed_school_ids_by_mechanism 存在，Record<string,string[]> 结构暂不做元素字典化）。 */
const DICT_SPEC = {
  'data/primary/transition/dist/xiaoshengchu_2026.json': {
    dicts: ['group', 'source_url'],
  },
  // 获奖明细：school（3383 唯一）/project（850）/award（31）高重复值列字典化，原始省 ~2.4MB
  'data/awards/dist/detailed_records.json': {
    dicts: ['school', 'project', 'award'],
  },
  // 初中招生：mechanism_note 84% 重复（番禺说明模板/派位组名，73 唯一/630 行）→ 字典化
  'data/middle/enrollment/dist/middle_enrollment_2026.json': {
    dicts: ['mechanism_note'],
  },
  // 小学招生：note 80% 重复（番禺说明模板等，33 唯一/782 行）→ 字典化
  'data/primary/enrollment/dist/2026-all.json': {
    dicts: ['note'],
  },
};

/**
 * 小程序主包专用列裁剪：地图信息卡不消费的字段不编译进主包产物
 * （详情页在分包，用 Web 全量产物；shapeRecord/formatXiaoshengchuBrief 不读被裁字段）。
 * 收益：source_url 已字典化（省 ~2KB）；source_note 自 2026-10 起仅保留在 parsed 审计层，
 * 不再进入 dist 产物，无需裁剪。
 */
const MP_TRIM = {
  // 主包地图页/信息卡不消费 source_url（详情页分包用全量产物）
  'data/primary/transition/dist/xiaoshengchu_2026.json': ['source_url'],
};

/**
 * 编译清单：
 * - WEB_TARGETS：Web 端显式消费白名单（apps/web/src 实际 import 的 31 个产物；
 *   源文件在此登记，输出路径由 SRC_REMAP 决定）。此前为 walkJson 全量编译，data/ 下
 *   parsed 中间表/构建期表大量混入运行时目录（死代码 ~6.7MB）→ 改为白名单 + 构建自检。
 * - MP_TARGETS：小程序主包当前消费（3 页：index/map/support；主包 ≤2MB）。未消费文件
 *   （详情页/通道页数据）等对应页面落地时加入并配分包。
 */
const WEB_TARGETS = [
  // 获奖（六赛事 compiled + 明细；各赛事 parsed 中间产物不编译，明细已聚合进 detailed_records）
  'data/awards/chuangke/dist/compiled.json',
  'data/awards/innovation/dist/compiled.json',
  'data/awards/science_experiment/dist/compiled.json',
  'data/awards/science_literacy/dist/compiled.json',
  'data/awards/tech_sports/dist/compiled.json',
  'data/awards/yueyunbei/dist/compiled.json',
  'data/awards/dist/detailed_records.json',
  // 文明校园
  'data/civilized_campuses/dist/civilized_campus_school_ids.json',
  // 高中：录取线/高分段/分类（levels 为人工源无 dist 构建）
  'data/high/cutoff_score/dist/scores_2025.json',
  'data/high/cutoff_score/dist/scores_2026.json',
  'data/registry/affiliation/src/levels.json',
  // 初中升学通道（remap 源，输出 linkage/xxx.js）
  'data/linkage/dist/batch2_scores.json',
  'data/linkage/dist/district_quota.json',
  'data/linkage/dist/quota_matrix.json',
  'data/linkage/dist/ranking_middle.json',
  'data/linkage/dist/special_matrix.json',
  'data/linkage/dist/quota_outcome.json',
  // 初中：2026 招生/排序
  'data/middle/enrollment/dist/middle_enrollment_2026.json',
  'data/middle/org_sort/dist/compiled.json',
  // POI（三学段）
  'data/poi/dist/high_poi.json',
  'data/poi/dist/middle_poi.json',
  'data/poi/dist/primary_poi.json',
  // 小学：2026 招生合并产物/小升初（含 remap 与 src 手工源）
  'data/primary/enrollment/dist/2026-all.json',
  'data/primary/transition/dist/xiaoshengchu_2026.json',
  'data/middle/enrollment/src/middle_enroll_notes.json',
  // 实体注册表/教育集团/品牌
  'data/registry/entity/dist/entities.json',
  'data/registry/group/dist/education_groups.json',
  'data/registry/group/dist/non_group_multi_campuses.json',
  'data/registry/group/src/brand_groups.json',
  // 特色校
  'data/specialty_schools/dist/specialty_schools.json',
];

/** 构建自检：前端 import 的输出 rel（WEB_TARGETS 对应产物）必须全部生成，防白名单漏登记 */
const WEB_OUTPUT_RELS = [
  'awards/chuangke/dist/compiled.js',
  'awards/innovation/dist/compiled.js',
  'awards/science_experiment/dist/compiled.js',
  'awards/science_literacy/dist/compiled.js',
  'awards/tech_sports/dist/compiled.js',
  'awards/yueyunbei/dist/compiled.js',
  'awards/dist/detailed_records.js',
  'civilized_campuses/dist/civilized_campus_school_ids.js',
  'high/cutoff_score/dist/scores_2025.js',
  'high/cutoff_score/dist/scores_2026.js',
  'high/level/src/levels.js',
  'linkage/batch2_scores.js',
  'linkage/district_quota.js',
  'linkage/quota_matrix.js',
  'linkage/ranking_middle.js',
  'linkage/special_matrix.js',
  'linkage/quota_outcome.js',
  'middle/enrollment/dist/middle_enrollment_2026.js',
  'middle/org_sort/dist/compiled.js',
  'poi/dist/high_poi.js',
  'poi/dist/middle_poi.js',
  'poi/dist/primary_poi.js',
  'primary/enrollments/2026-all.js',
  'primary/xiaoshengchu_2026.js',
  'primary/middle_enroll_notes.js',
  'registry/entity/dist/entities.js',
  'registry/group/dist/education_groups.js',
  'registry/group/dist/non_group_multi_campuses.js',
  'registry/group/src/brand_groups.js',
  'specialty_schools/dist/specialty_schools.js',
];
// 小程序主包数据（地图页 + 首页消费）：POI/levels/招生/实体/升学路线/官方录取分
const MP_MAIN_TARGETS = [
  'data/poi/dist/primary_poi.json',
  'data/primary/transition/dist/xiaoshengchu_2026.json',
  'data/middle/enrollment/src/middle_enroll_notes.json',
  'data/poi/dist/middle_poi.json',
  'data/poi/dist/high_poi.json',
  'data/registry/affiliation/src/levels.json',
  'data/high/cutoff_score/dist/scores_2025.json',
  'data/high/cutoff_score/dist/scores_2026.json',
  'data/registry/entity/dist/entities.json',
  'data/primary/enrollment/dist/2026-all.json',
];
// 小学招生 C 层合并产物（dist/2026-all.json）通用编译为 enrollments/2026-all.js
// 小程序分包数据（school-detail 详情页专用）：升学通道/身份/品牌/教育集团
// （sites.json 已于 2026-09-21 废弃：法人别名挂载内联 build_entities，无运行时消费）
// （官方录取分 scores 已在主包加载，详情页经 baseLoaders 继承，无需重复编译）
const MP_SUB_TARGETS = [
  'data/linkage/dist/quota_matrix.json',
  'data/linkage/dist/special_matrix.json',
  'data/linkage/dist/batch2_scores.json',
  'data/linkage/dist/district_quota.json',
  'data/linkage/dist/quota_outcome.json',
  'data/registry/group/src/brand_groups.json',
  'data/registry/group/dist/education_groups.json',
  // 初中 2026 招生计划（一校多规则：mechanism/plan_classes/scope/派位组生源小学），
  // 详情页 07B「招生计划（2026年）」模块消费（Web 端同名产物已编译）
  'data/middle/enrollment/dist/middle_enrollment_2026.json',
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
function compileRows(rows, dictFields, listDictFields = [], trim = []) {
  // 键并集（首次出现顺序；trim 列不编译）
  const cols = [];
  const seen = new Set();
  for (const r of rows) {
    for (const k of Object.keys(r)) {
      if (trim.includes(k)) continue;
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
  // 列表元素字典：数组元素（如实体 id）唯一值少时索引化
  const listDicts = {};
  const listMaps = {};
  for (const lf of listDictFields) {
    if (!seen.has(lf)) continue;
    const uniq = [];
    const um = new Map();
    let refs = 0;
    for (const r of rows) {
      const arr = r[lf];
      if (!Array.isArray(arr)) continue;
      for (const e of arr) {
        if (typeof e !== 'string') continue;
        refs += 1;
        if (!um.has(e)) { um.set(e, uniq.length); uniq.push(e); }
      }
    }
    if (uniq.length * 2 < refs) { listDicts[lf] = uniq; listMaps[lf] = um; }
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
      const lm = listMaps[c];
      if (lm && Array.isArray(v)) { row[i] = v.map((e) => (typeof e === 'string' ? lm.get(e) : e)); continue; }
      row[i] = compileValue(v);
    }
    return row;
  });
  const out = { $cols: cols, $rows: outRows };
  if (Object.keys(dicts).length) out.$dicts = dicts;
  if (Object.keys(listDicts).length) out.$listDicts = listDicts;
  return out;
}

function compileValue(v, opts = {}) {
  const { dictFields = [], listDictFields = [], trim = [] } = opts;
  if (v === null || typeof v !== 'object') return v;
  if (Array.isArray(v)) {
    // 记录数组（元素全为对象）→ 列式化；否则逐元素递归
    if (v.length > 0 && v.every((e) => typeof e === 'object' && e !== null && !Array.isArray(e))) {
      return compileRows(v, dictFields, listDictFields, trim);
    }
    return v.map((e) => compileValue(e));
  }
  const out = {};
  for (const [k, val] of Object.entries(v)) {
    // 字典字段仅作用于顶层 records 数组
    out[k] = compileValue(val, k === 'records' ? opts : {});
  }
  return out;
}

/* ---------- 主流程 ---------- */
for (const dir of [OUT_CJS_MAIN, OUT_CJS_SUB, OUT_ESM]) {
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
}

/** 编译单个真源文件到目标目录，fmt: 'cjs' | 'esm'；opts.trim 仅主包列裁剪 */
function emit(file, outDir, fmt, opts = {}) {
  const abs = join(ROOT, file);
  /**
 * 数据源归位 data/primary/transition 后，产物 rel 保持历史稳定（前端 import 不变）：
 * 输入真源路径 → 输出 rel 路径（相对 data/）
 */
const SRC_REMAP = {
  'primary/transition/dist/xiaoshengchu_2026': 'primary/xiaoshengchu_2026',
  'primary/transition/dist/xiaoshengchu_all': 'primary/xiaoshengchu_all',
  'primary/transition/dist/xiaoshengchu_baiyun': 'primary/enrollments/xiaoshengchu_baiyun',
  'primary/transition/dist/xiaoshengchu_haizhu': 'primary/enrollments/xiaoshengchu_haizhu',
  'primary/transition/dist/xiaoshengchu_huangpu': 'primary/enrollments/xiaoshengchu_huangpu',
  'primary/transition/dist/xiaoshengchu_liwan': 'primary/enrollments/xiaoshengchu_liwan',
  'primary/transition/dist/xiaoshengchu_panyu': 'primary/enrollments/xiaoshengchu_panyu',
  'primary/transition/dist/xiaoshengchu_tianhe': 'primary/enrollments/xiaoshengchu_tianhe',
  'primary/transition/dist/xiaoshengchu_yuexiu': 'primary/enrollments/xiaoshengchu_yuexiu',
  'primary/enrollment/dist/2026-baiyun': 'primary/enrollments/2026-baiyun',
  'primary/enrollment/dist/2026-haizhu': 'primary/enrollments/2026-haizhu',
  'primary/enrollment/dist/2026-huangpu': 'primary/enrollments/2026-huangpu',
  'primary/enrollment/dist/2026-liwan': 'primary/enrollments/2026-liwan',
  'primary/enrollment/dist/2026-panyu': 'primary/enrollments/2026-panyu',
  'primary/enrollment/dist/2026-tianhe': 'primary/enrollments/2026-tianhe',
  'primary/enrollment/dist/2026-yuexiu': 'primary/enrollments/2026-yuexiu',
  'primary/enrollment/dist/2026-all': 'primary/enrollments/2026-all',
  'primary/transition/dist/schools-backfill': 'primary/schools-backfill',
  'middle/enrollment/src/middle_enroll_notes': 'primary/middle_enroll_notes',
  // linkage 归位 dist 后，产物 rel 保持历史稳定（前端 import/require 不变）
  'linkage/dist/quota_matrix': 'linkage/quota_matrix',
  'linkage/dist/special_matrix': 'linkage/special_matrix',
  'linkage/dist/batch2_scores': 'linkage/batch2_scores',
  'linkage/dist/district_quota': 'linkage/district_quota',
  'linkage/dist/ranking_middle': 'linkage/ranking_middle',
  'linkage/dist/quota_outcome': 'linkage/quota_outcome',
  // affiliation 归位 registry 后，产物 rel 保持历史稳定（前端 import/require 不变）
  'registry/affiliation/src/levels': 'high/level/src/levels',
};
const relRaw = relative(DATA_SRC, abs); // 真源 rel（含 .json，注释/统计用）
const relPath = (SRC_REMAP[relRaw.replace(/\.json$/, '')] ?? relRaw.replace(/\.json$/, '')) + '.json'; // 输出 rel（remap 后保持历史路径）
  const json = JSON.parse(readFileSync(abs, 'utf8'));
  const spec = DICT_SPEC[file] || {};
  const compact = compileValue(json, {
    dictFields: spec.dicts || [],
    listDictFields: spec.listDicts || [],
    trim: opts.trim || [],
  });
  const literal = jsLiteral(compact);
  const out = join(outDir, relPath.replace(/\.json$/, '.js'));
  mkdirSync(dirname(out), { recursive: true });
  if (fmt === 'cjs') {
    writeFileSync(out, '// 由 scripts/data/compact.mjs 从 data/' + relRaw + ' 编译（紧凑列式），勿手改\nmodule.exports = ' + literal + ';\n', 'utf8');
  } else {
    writeFileSync(out, '// 由 scripts/data/compact.mjs 从 data/' + relRaw + ' 编译（紧凑列式），勿手改\nconst data = ' + literal + ';\nexport default data;\n', 'utf8');
    writeFileSync(out.replace(/\.js$/, '.d.ts'), 'declare const data: unknown;\nexport default data;\n', 'utf8');
  }
  return { file: relPath, jsonKB: readFileSync(abs, 'utf8').length / 1024, jsKB: readFileSync(out, 'utf8').length / 1024 };
}


const stats = [];
for (const file of MP_MAIN_TARGETS) stats.push(emit(file, OUT_CJS_MAIN, 'cjs', { trim: MP_TRIM[file] }));
for (const file of MP_SUB_TARGETS) stats.push(emit(file, OUT_CJS_SUB, 'cjs'));
for (const file of WEB_TARGETS) stats.push(emit(file, OUT_ESM, 'esm'));

// 构建自检：前端 import 的每个输出 rel 必须已生成（WEB_TARGETS 白名单漏登记源文件时在此报错）
for (const rel of WEB_OUTPUT_RELS) {
  if (!existsSync(join(OUT_ESM, rel))) {
    throw new Error(`[compact] 前端消费产物缺失: ${rel} —— WEB_TARGETS 白名单漏登记对应源文件`);
  }
}

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
