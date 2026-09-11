/**
 * 地图域搜索：先按校名包含匹配点位；未命中时用实体别名兜底（来源叫法如
 * 「南村中学(初中部)」映射到完中实体对应点位），最多 12 条。
 */
import type { MapPointFull } from './points.js';
import { normName } from '../../support.js';

export function searchSchools(
  points: ReadonlyArray<MapPointFull>,
  kw: string,
  entities?: ReadonlyArray<{ school_id: string; name: string; aliases?: string[] }>,
): MapPointFull[] {
  const k = (kw || '').trim();
  if (!k) return [];
  const direct = points.filter((p) => p.name.includes(k)).slice(0, 12);
  if (direct.length) return direct;
  if (entities && entities.length) {
    const kn = normName(k);
    const names = new Set<string>();
    for (const e of entities) {
      if (normName(e.name) === kn || (e.aliases || []).some((a) => normName(a) === kn)) {
        names.add(e.name);
      }
    }
    if (names.size) {
      const out = points.filter((p) => [...names].some((n) => p.name.includes(n))).slice(0, 12);
      if (out.length) return out;
    }
  }
  return direct;
}
