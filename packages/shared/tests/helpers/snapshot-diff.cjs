'use strict';
/**
 * 结构化快照 diff（node 测试通用）：基线存「key → value」映射，
 * 对比当前映射输出精确到键的 增(+)/删(-)/改(~) 明细——不再用
 * 数字断言 / sha256 digest（漂移时看不出谁变了）。
 *
 * 用法：
 *   const { diffSnapshots, formatDiff } = require('./helpers/snapshot-diff.cjs');
 *   const { lines } = diffSnapshots(baseMap, curMap);
 *   assert.deepEqual(lines, [], `快照漂移：\n` + lines.join('\n'));
 */
function diffSnapshots(base, cur) {
  const bKeys = base ? Object.keys(base) : [];
  const cKeys = cur ? Object.keys(cur) : [];
  const keys = [...new Set([...bKeys, ...cKeys])].sort();
  const added = [];
  const removed = [];
  const changed = [];
  const lines = [];
  for (const k of keys) {
    const hasB = Object.prototype.hasOwnProperty.call(base || {}, k);
    const hasC = Object.prototype.hasOwnProperty.call(cur || {}, k);
    const b = hasB ? base[k] : undefined;
    const c = hasC ? cur[k] : undefined;
    if (!hasB) {
      added.push(k);
      lines.push(`  + ${k}${c !== undefined ? ': ' + JSON.stringify(c) : ''}`);
    } else if (!hasC) {
      removed.push(k);
      lines.push(`  - ${k}${b !== undefined ? ': ' + JSON.stringify(b) : ''}`);
    } else if (JSON.stringify(b) !== JSON.stringify(c)) {
      changed.push(k);
      lines.push(`  ~ ${k}: ${JSON.stringify(b)} → ${JSON.stringify(c)}`);
    }
  }
  return { added, removed, changed, lines };
}

function formatDiff(d) {
  const head = `新增 ${d.added.length} / 移除 ${d.removed.length} / 变更 ${d.changed.length}`;
  return d.lines.length ? head + '\n' + d.lines.join('\n') : head;
}

module.exports = { diffSnapshots, formatDiff };
