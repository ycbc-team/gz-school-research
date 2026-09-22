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

/**
 * 小学招生 C 层合并产物还原：dist/2026-all.json（{year, districts: {区名: meta},
 * records/minban 每行带 district}，无 school 名——按 school_id 联查实体表/POI 表）。
 * 此处按 district 还原为 EnrollmentSnapshot[]（区元数据 + 该区 records/minban）。
 */
export interface MergedEnrollments {
  year: number;
  districts: Record<string, Record<string, unknown>>;
  records: CompactArray;
  minban: CompactArray;
}
export function splitEnrollments<T>(merged: MergedEnrollments): T[] {
  const districts = hydrate(merged.districts) as Record<string, Record<string, unknown>>;
  const records = hydrate(merged.records) as unknown as Array<Record<string, unknown>>;
  const minban = hydrate(merged.minban) as unknown as Array<Record<string, unknown>>;
  // 按 adcode 分组（records.district 保留原值：番禺为片区名），还原后删除 adcode 过滤列
  const adToDistrict = new Map<string, string>();
  for (const [district, m] of Object.entries(districts)) {
    const ad = m.adcode as string;
    if (ad) adToDistrict.set(ad, district);
  }
  return Object.entries(districts).map(([district, m]) => ({
    ...m,
    district,
    records: records.filter((r) => adToDistrict.get(r.adcode as string) === district)
      .map(({ adcode: _a, ...rest }) => rest),
    minban: minban.filter((r) => adToDistrict.get(r.adcode as string) === district)
      .map(({ adcode: _a, ...rest }) => rest),
  })) as unknown as T[];
}
