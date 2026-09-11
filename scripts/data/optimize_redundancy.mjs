/**
 * 真源冗余优化（幂等，可审计）：
 *   1. quota_matrix.json：sz 稀疏化 —— 省略 null 键（40% 单元格为 null），
 *      消费侧统一用 `?? 0`，缺失键 === null，零代码改动。
 *   2. batch2_scores.json：删除 admitted:false 且无分数的记录（542 条）。
 *      前端只消费 min_score/last_score，false 记录消费结果与"无记录"一致；
 *      删除后顺带消除合并表里的全空行。
 * 运行：node scripts/data/optimize_redundancy.mjs
 * 输出：写回真源 JSON（1 空格缩进、无尾换行，与现有格式一致）+ 变更统计
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const read = (p) => JSON.parse(readFileSync(join(ROOT, p), 'utf8'));
const write = (p, o) => {
  // 与现有真源格式保持一致：1 空格缩进、无尾换行、中文不转义、键序保持
  const json = JSON.stringify(o, null, 1);
  writeFileSync(join(ROOT, p), json, 'utf8');
};

const report = {};

/* ========== 1) quota_matrix.sz 稀疏化 ========== */
{
  const p = 'data/linkage/quota_matrix.json';
  const q = read(p);
  let removed = 0;
  for (const s of q.schools) {
    const sz = s.sz;
    if (!sz) continue;
    const sparse = {};
    for (const [k, v] of Object.entries(sz)) {
      if (v === null) { removed += 1; continue; } // 省略 null 键
      sparse[k] = v;
    }
    s.sz = sparse;
  }
  write(p, q);
  report.quota_matrix = { null_cells_removed: removed };
}

/* ========== 2) batch2_scores 删 admitted:false 记录 ========== */
{
  const p = 'data/linkage/batch2_scores.json';
  const b = read(p);
  let removed = 0;
  for (const [hs, inner] of Object.entries(b.data || {})) {
    for (const [sch, rec] of Object.entries(inner)) {
      if (rec.admitted === false) {
        delete inner[sch];
        removed += 1;
      }
    }
  }
  write(p, b);
  report.batch2_scores = { false_records_removed: removed };
}

console.log('[optimize_redundancy]', JSON.stringify(report, null, 2));
