/**
 * 徽章域：学校徽章（区域 · 学段 · 民办 · 省/市示范）。
 * 详情页 / 地图搜索 / 地图点选浮层三处共用。
 * 民办身份唯一真源：实体表（entities.nature='民办'，公办不写字段）；优先按 school_id 精确，
 * 无 school_id（详情页按名打开等）时按 norm 校名/别名兜底。
 */
import { normName } from '../support.js';
import type { DataLoaders } from './loader.js';
import type { SchoolBadge } from './types.js';

export function createBadgesApi(loaders: DataLoaders) {
  const { primarySchools, middleSchools, highSchools, entities } = loaders;

  /** 民办实体索引：school_id → true；norm(名称/别名) → true */
  const minbanById = new Map<string, true>();
  const minbanByName = new Map<string, true>();
  for (const e of entities.entities) {
    if (e.nature !== '民办') continue;
    minbanById.set(e.school_id, true);
    const put = (k: string) => { if (k) minbanByName.set(k, true); };
    put(normName(e.name));
    for (const a of e.aliases || []) put(normName(a));
  }
  function isMinban(opts: { schoolId?: string; name?: string }): boolean {
    if (opts.schoolId && minbanById.has(opts.schoolId)) return true;
    const name = opts.name || '';
    return !!name && !!minbanByName.get(normName(name));
  }

  /**
   * 学校徽章组：区域 · 学段 · 民办 · 省/市示范。
   */
  function schoolBadges(
    stage: 'primary' | 'middle' | 'high',
    opts: { district?: string; tier?: any; rec?: any; name?: string; schoolId?: string; singleStage?: boolean; stages?: ('primary' | 'middle' | 'high')[] },
  ): SchoolBadge[] {
    const out: SchoolBadge[] = [];
    if (opts.district) out.push({ text: opts.district, cls: 'b-district' });
    // 该校名实际出现在哪些学段（POI 全等）：覆盖完中(middle+high)与九年一贯(primary+middle)。
    // 优先用点位实际 stages（同址多学部合并点主名只等于主学部 POI 名，按名全等会漏非主学部）；
    // 无 stages（详情页等按 name 推断）时回退校名全等。
    let stagesHere: ('primary' | 'middle' | 'high')[] = [];
    if (opts.stages && opts.stages.length) {
      stagesHere = [...opts.stages];
    } else {
      const name = opts.name || '';
      if (name) {
        if (primarySchools.schools.some((s) => normName(s.name) === normName(name))) stagesHere.push('primary');
        if (middleSchools.schools.some((s) => normName(s.name) === normName(name))) stagesHere.push('middle');
        if (highSchools.schools.some((s) => normName(s.name) === normName(name))) stagesHere.push('high');
      }
    }
    const has = (s: 'primary' | 'middle' | 'high') => stagesHere.includes(s);
    if (!opts.singleStage) {
      // 地图浮层：该点位所属学段全标
      if (has('primary')) out.push({ text: '小学', cls: 'b-stage' });
      if (has('middle')) out.push({ text: '初中', cls: 'b-stage' });
      if (has('high')) out.push({ text: '高中', cls: 'b-stage' });
    } else {
      out.push({ text: stage === 'primary' ? '小学' : stage === 'middle' ? '初中' : '高中', cls: 'b-stage' });
    }
    // 民办：办学性质唯一真源=实体表 nature（公办不写字段）；优先 school_id，按名兜底
    if (isMinban(opts)) out.push({ text: '民办', cls: 'b-minban' });
    // 省/市示范是高中部级别，只在高中 tab 显示（初中 tab 不显示高中 badge）
    if (stage === 'high' && opts.rec) {
      if (opts.rec.category === '省市属示范') out.push({ text: '省示范', cls: 'b-hcity' });
      else if (opts.rec.category === '区属示范') out.push({ text: '市示范', cls: 'b-hdist' });
    }
    return out;
  }

  return { schoolBadges };
}
