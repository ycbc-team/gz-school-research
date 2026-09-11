/**
 * 紧凑数据水合层（compact ↔ 原对象结构双向一致）。
 *
 * 小程序包体积治理：真源 JSON 在构建期由 scripts/data/compact.mjs 编译为紧凑结构
 * （列式 rows + 字段字典），本模块在运行时还原为与原 JSON 完全一致的对象。
 * Web 端不经过本层（直接 import 真源 JSON）。
 *
 * 紧凑结构约定（与 compact.mjs 保持一致）：
 * - 记录数组 → { $cols: string[], $rows: unknown[][] }
 *   - $cols 为全部键的并集（按首次出现顺序）；行内按 $cols 顺序存值，缺失键省略
 *     （行长度 < $cols 长度即缺键，还原时不设该键）；显式 null 保留。
 *   - 可选字段字典：{ $cols, $rows, $dicts: { 字段: 唯一值数组 } }
 *     字典字段行内存索引（null 不索引，行内直接存 null）。
 *   - 可选列表元素字典：{ $cols, $rows, $listDicts: { 字段: 唯一元素数组 } }
 *     列表字段（如 feed_school_ids 实体 id 数组）行内存元素索引。
 * - 其余结构原样保留，递归水合。
 */
export interface CompactArray {
  $cols: string[];
  $rows: unknown[][];
  $dicts?: Record<string, unknown[]>;
  $listDicts?: Record<string, unknown[]>;
}

function isCompactArray(x: unknown): x is CompactArray {
  return (
    typeof x === 'object' &&
    x !== null &&
    Array.isArray((x as CompactArray).$cols) &&
    Array.isArray((x as CompactArray).$rows)
  );
}

/** 递归还原紧凑结构为原对象（数组/对象/标量） */
export function hydrate<T>(x: T): T {
  if (Array.isArray(x)) return x.map((v) => hydrate(v)) as unknown as T;
  if (typeof x !== 'object' || x === null) return x;
  const obj = x as Record<string, unknown>;
  if (isCompactArray(obj)) {
    const { $cols, $rows, $dicts, $listDicts } = obj;
    return $rows.map((row) => {
      const out: Record<string, unknown> = {};
      for (let i = 0; i < $cols.length; i += 1) {
        const col = $cols[i] as string;
        if (i >= row.length) continue; // 缺失列（行短）：不设键
        const v = row[i];
        if (v === undefined) continue; // 稀疏空位：不设键
        const dict = $dicts?.[col];
        const listDict = $listDicts?.[col];
        if (v === null) out[col] = null;
        else if (dict) out[col] = dict[v as number];
        else if (listDict && Array.isArray(v)) out[col] = v.map((e) => (typeof e === 'number' ? listDict[e] : hydrate(e)));
        else out[col] = hydrate(v);
      }
      return out;
    }) as unknown as T;
  }
  const out: Record<string, unknown> = {};
  for (const k of Object.keys(obj)) out[k] = hydrate(obj[k]);
  return out as T;
}
