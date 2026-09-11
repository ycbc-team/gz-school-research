/**
 * 地图域搜索：按校名包含匹配点位（最多 12 条）。
 */
import type { MapPointFull } from './points.js';

export function searchSchools(points: ReadonlyArray<MapPointFull>, kw: string): MapPointFull[] {
  const k = (kw || '').trim();
  if (!k) return [];
  return points.filter((p) => p.name.includes(k)).slice(0, 12);
}
