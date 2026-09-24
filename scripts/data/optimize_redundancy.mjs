/**
 * 真源冗余优化（幂等，可审计）：
 *   1. dist/quota_matrix.json：sz 稀疏化 —— 省略 null 键（40% 单元格为 null），
 *      消费侧统一用 `?? 0`，缺失键 === null，零代码改动。
 *   2.（原 batch2 删 admitted:false + middle_school_ids 裁剪已并入 C 层 backfill，
 *      此脚本不再处理 batch2。）
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
  const p = 'data/linkage/dist/quota_matrix.json';
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


console.log('[optimize_redundancy]', JSON.stringify(report, null, 2));
