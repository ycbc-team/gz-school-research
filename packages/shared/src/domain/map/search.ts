/**
 * 地图域搜索：先按校名包含匹配点位；未命中时用实体别名兜底（来源叫法如
 * 「南村中学(初中部)」映射到完中实体对应点位），最多 12 条。
 */
import type { MapPointFull } from './points.js';
import { normName } from '../../support.js';
import { DISTRICTS, STAGE_LABEL, STAGE_PRIORITY, districtByAdcode } from './constants.js';

export function searchSchools(
  points: ReadonlyArray<MapPointFull>,
  kw: string,
  entities?: ReadonlyArray<{ school_id: string; name: string; aliases?: string[] }>,
): MapPointFull[] {
  const k = (kw || '').trim();
  if (!k) return [];
  // 同址多学部合并点的 names 记录各学部 POI 名（如「南武文润学校(小学部)」），任一名命中即返回
  const direct = points.filter((p) => p.names?.some((n) => n.includes(k)) || p.name.includes(k)).slice(0, 12);
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

/* ========== 搜索中间页联想 / 推荐（对齐小程序首页搜索页，2026-09-30 迁移） ========== */

/** 区序：按 DISTRICTS 声明顺序（对齐小程序 DIST_ORDER） */
const DIST_ORDER: Record<string, number> = {};
DISTRICTS.forEach((d, i) => { DIST_ORDER[d.adcode] = i; });

/** 拼音首字母表：覆盖广州校名常见字（与小程序页面实现一致），表外字符跳过 */
const PY: Record<string, string> = {
  广: 'g', 东: 'd', 州: 'z', 省: 's', 实: 's', 验: 'y', 华: 'h', 南: 'n', 师: 's', 范: 'f', 大: 'd', 学: 'x', 附: 'f',
  中: 'z', 第: 'd', 二: 'e', 六: 'l', 执: 'z', 信: 'x', 铁: 't', 一: 'y', 协: 'x', 和: 'h', 仲: 'z', 元: 'y', 真: 'z',
  雅: 'y', 光: 'g', 培: 'p', 英: 'y', 育: 'y', 外: 'w', 国: 'g', 侨: 'q', 天: 't', 河: 'h', 清: 'q', 黄: 'h', 岗: 'g',
  爱: 'a', 群: 'q', 贤: 'x', 正: 'z', 衡: 'h', 维: 'w', 为: 'w', 明: 'm', 邝: 'k', 体: 't', 艺: 'y', 曦: 'x', 市: 's',
  属: 's', 湾: 'w', 语: 'y', 校: 'x', 区: 'q',
};
/** 拼音首字母 key（最多 6 位）：推荐列表按此确定性排序 */
export function pykey(s: string): string {
  let k = '';
  for (const ch of s || '') { if (k.length >= 6) break; const p = PY[ch]; if (p) k += p; }
  return k;
}

export interface AssocResult {
  name: string;
  district: string;
  stages: string[];
}
/**
 * 搜索联想：校名包含匹配优先，实体别名兜底；排序 精确命中 > 区序 > 学段序 > 名称，
 * 最多 20 条，带行政区（含「区」字）与学段标签（多学段按 小学 > 初中 > 高中 拆多枚）。
 */
export function buildAssocResults(
  points: ReadonlyArray<MapPointFull>,
  kw: string,
  entities?: ReadonlyArray<{ school_id: string; name: string; aliases?: string[] }>,
): AssocResult[] {
  const k = (kw || '').trim();
  if (!k) return [];
  const direct = points.filter((p) => p.names?.some((n) => n.includes(k)) || p.name.includes(k));
  const pool = direct.length ? direct : searchSchools(points, k, entities);
  const exact = (p: MapPointFull) => p.names?.some((n) => n === k) || p.name === k;
  pool.sort((a, b) => {
    const ea = exact(a), eb = exact(b);
    if (ea !== eb) return ea ? -1 : 1;
    const da = DIST_ORDER[a.adcode] ?? 9, db = DIST_ORDER[b.adcode] ?? 9;
    if (da !== db) return da - db;
    const sa = STAGE_PRIORITY[a.mainStage] ?? 9, sb = STAGE_PRIORITY[b.mainStage] ?? 9;
    if (sa !== sb) return sa - sb;
    return a.name.localeCompare(b.name);
  });
  return pool.slice(0, 20).map((p) => ({
    name: p.name,
    district: districtByAdcode[p.adcode] || '',
    stages: (p.stages || []).slice().sort((x, y) => STAGE_PRIORITY[x] - STAGE_PRIORITY[y]).map((s) => STAGE_LABEL[s]),
  }));
}

/** 省市属示范高中推荐列表（hM）：多校区按推荐名/点名校名去重，按拼音首字母排序 */
export function buildRecommendList(points: ReadonlyArray<MapPointFull>): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of points) {
    if (p.stages.includes('high') && p.clsOf && p.clsOf.high === 'hM') {
      const base = (p.rec && p.rec.name) || p.name;
      if (!seen.has(base)) { seen.add(base); out.push(base); }
    }
  }
  out.sort((a, b) => pykey(a).localeCompare(pykey(b)) || a.localeCompare(b));
  return out;
}
