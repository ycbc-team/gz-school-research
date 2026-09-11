/**
 * 徽章域：学校徽章（区域 · 学段 · 口碑 · 省/市示范）+ 口碑支撑度 badge。
 * 详情页 / 地图搜索 / 地图点选浮层三处共用。
 */
import { normName } from '../support.js';
import type { DataLoaders } from './loader.js';
import type { SchoolBadge } from './types.js';

export function createBadgesApi(loaders: DataLoaders) {
  const { primarySchools, middleSchools, highSchools } = loaders;

  /**
   * 学校徽章组：区域 · 学段 · 口碑 · 省/市示范。
   */
  function schoolBadges(
    stage: 'primary' | 'middle' | 'high',
    opts: { district?: string; tier?: any; rec?: any; name?: string; singleStage?: boolean },
  ): SchoolBadge[] {
    const out: SchoolBadge[] = [];
    if (opts.district) out.push({ text: opts.district, cls: 'b-district' });
    // 该校名实际出现在哪些学段（POI 全等）：覆盖完中(middle+high)与九年一贯(primary+middle)
    const name = opts.name || '';
    const stagesHere: ('primary' | 'middle' | 'high')[] = [];
    if (name) {
      if (primarySchools.schools.some((s) => normName(s.name) === normName(name))) stagesHere.push('primary');
      if (middleSchools.schools.some((s) => normName(s.name) === normName(name))) stagesHere.push('middle');
      if (highSchools.schools.some((s) => normName(s.name) === normName(name))) stagesHere.push('high');
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
    const t = opts.tier;
    if (t) {
      if (t.tier1_eligible === false) out.push({ text: '挂牌', cls: 'b-license' });
      else out.push({ text: '口碑', cls: 'b-tier' });
    }
    // 省/市示范是高中部级别，只在高中 tab 显示（初中 tab 不显示高中 badge）
    if (stage === 'high' && opts.rec) {
      if (opts.rec.category === '省市属示范') out.push({ text: '省示范', cls: 'b-hcity' });
      else if (opts.rec.category === '区属示范') out.push({ text: '市示范', cls: 'b-hdist' });
    }
    return out;
  }

  /** 口碑支撑度 badge（仅口碑信号卡内使用）：有支撑/部分支撑/无支撑 */
  function supportBadge(tier?: any): SchoolBadge | null {
    if (!tier) return null;
    if (tier.tier1_eligible === false) return { text: '未计入口碑校', cls: 'b-license' };
    const c = tier.conclusion;
    if (c === '有支撑') return { text: '有支撑', cls: 'b-full' };
    if (c === '部分支撑') return { text: '部分支撑', cls: 'b-part' };
    return { text: '无支撑', cls: 'b-none' };
  }

  return { schoolBadges, supportBadge };
}
