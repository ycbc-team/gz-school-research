/**
 * 地图域点位构建：三学段 POI → 合并多学部点（同 school_id）+ tier/高中分类 + 补点去重。
 * 纯逻辑，零地图库依赖；Web Leaflet 与小程序 <map> 共用同一份点集。
 */
import { buildAliasTable, matchTier1ByPoiName, normName } from '../../support.js';
import type { Tier1School, HighLevelSchool, SchoolStage, SchoolsSnapshot } from '../../types.js';
import type { DataLoaders } from '../../data/loader.js';
import type { MapPoint } from './filters.js';
import { adcodeByDistrict, districtByAdcode, STAGE_PRIORITY, type ClsKey } from './constants.js';

/** 完整点位（含信息卡所需字段） */
export interface MapPointFull extends MapPoint {
  /** 各学部梯队记录（小学/初中口碑校） */
  tierOf: Partial<Record<SchoolStage, Tier1School | null>>;
  /** 高中分类记录（高中学部） */
  rec: HighLevelSchool | null;
  /** 主学部梯队记录（= tierOf[mainStage]） */
  tier: Tier1School | null;
}

/** 新开办学校无成绩：不参与口碑/挂牌判定（数据层 note 标记，避免独立法人新校被前缀误判） */
function isNewOpening(note?: string): boolean {
  return !!note && note.includes('新开办');
}

export function buildPoints(loaders: DataLoaders): MapPointFull[] {
  const { primarySchools, middleSchools, highSchools, highLevels } = loaders;

  const tierTables = {
    primary: buildAliasTable(Object.values(loaders.primaryTier1.districts).flatMap((d) => d.schools), loaders.entities.entities),
    middle: buildAliasTable(Object.values(loaders.middleTier1.districts).flatMap((d) => d.schools), loaders.entities.entities),
  };
  function tierOf(stage: 'primary' | 'middle', name: string, note?: string): Tier1School | undefined {
    if (isNewOpening(note)) return undefined;
    const schools = stage === 'primary'
      ? Object.values(loaders.primaryTier1.districts).flatMap((d) => d.schools)
      : Object.values(loaders.middleTier1.districts).flatMap((d) => d.schools);
    return matchTier1ByPoiName(name, schools, tierTables[stage]);
  }
  /** 独立法人挂牌校（tier1_eligible=false，成绩未达标/无证据）不计入口碑学校 */
  function isTierRecord(t?: Tier1School): boolean {
    return !!t && t.tier1_eligible !== false && (t.conclusion === '有支撑' || t.conclusion === '部分支撑');
  }

  const highTable = new Map<string, HighLevelSchool>();
  for (const sc of highLevels.schools) {
    for (const k of [sc.name, ...(sc.aliases || []), ...(sc.campuses || [])]) {
      const nk = normName(k);
      if (nk && !highTable.has(nk)) highTable.set(nk, sc);
    }
  }
  function highRecord(pt: { school?: string; name: string }): HighLevelSchool | undefined {
    const key = normName(pt.school || pt.name);
    const rec = highTable.get(key);
    if (rec) return rec;
    const n = normName(pt.name);
    if (!n) return undefined;
    return highTable.get(n);
  }
  function highCls(rec?: HighLevelSchool): ClsKey {
    if (!rec) return 'hN';
    if (rec.category === '省市属示范') return 'hM';
    if (rec.category === '区属示范') return 'hD';
    return 'hN';
  }

  const allPoints: MapPointFull[] = [];
  const ptByKey = new Map<string, MapPointFull>();
  const tierByName: Record<string, true> = {};
  function addSchool(
    s: { name: string; lat: number; lng: number; adcode: string; school_id?: string; note?: string },
    stage: SchoolStage,
    cls: ClsKey,
    tier: Tier1School | null,
    rec: HighLevelSchool | null,
  ) {
    if (!districtByAdcode[s.adcode]) return;
    // 同 school_id = 同校区多学部；补点无 school_id 时按名合并
    const key = s.school_id || `name:${s.name}`;
    let pt = ptByKey.get(key);
    if (!pt) {
      pt = {
        name: s.name, lat: s.lat, lng: s.lng, adcode: s.adcode,
        stages: [], clsOf: {} as Record<SchoolStage, ClsKey>,
        tierOf: {}, rec: null, mainStage: stage, tier: null,
      };
      ptByKey.set(key, pt);
      allPoints.push(pt);
    }
    if (!pt.stages.includes(stage)) {
      pt.stages.push(stage);
      pt.clsOf[stage] = cls;
      pt.tierOf[stage] = tier;
    }
    if (stage === 'high' && rec) pt.rec = rec;
  }

  for (const s of primarySchools.schools) {
    const t = tierOf('primary', s.name, s.note);
    addSchool(s, 'primary', isTierRecord(t) ? 'pT' : 'pN', t ?? null, null);
    if (t) tierByName[t.name] = true;
  }
  for (const s of middleSchools.schools) {
    const t = tierOf('middle', s.name, s.note);
    addSchool(s, 'middle', isTierRecord(t) ? 'mT' : 'mN', t ?? null, null);
    if (t) tierByName[t.name] = true;
  }
  for (const s of highSchools.schools) {
    const rec = highRecord(s);
    addSchool(s, 'high', highCls(rec), null, rec ?? null);
  }

  // 补点：tier1 内手工坐标（小学 3 所 + 初中 14 所），按名去重
  const addExtra = (snapshot: { districts: Record<string, { schools: Tier1School[] }> }, stage: 'primary' | 'middle') => {
    for (const sc of Object.values(snapshot.districts).flatMap((d) => d.schools)) {
      if (!sc.coords || tierByName[sc.name]) continue;
      addSchool(
        { name: sc.name, lat: sc.coords.lat, lng: sc.coords.lng, adcode: adcodeByDistrict[sc.district ?? ''] || '' },
        stage,
        isTierRecord(sc) ? (stage === 'primary' ? 'pT' : 'mT') : (stage === 'primary' ? 'pN' : 'mN'),
        sc,
        null,
      );
      tierByName[sc.name] = true;
    }
  };
  addExtra(loaders.primaryTier1, 'primary');
  addExtra(loaders.middleTier1, 'middle');

  // 统一：stages 升序、主学部取最高优先级、主学部 tier
  for (const pt of allPoints) {
    pt.stages.sort((a, b) => STAGE_PRIORITY[a] - STAGE_PRIORITY[b]);
    pt.mainStage = pt.stages[pt.stages.length - 1]!;
    pt.tier = pt.tierOf[pt.mainStage] ?? null;
  }
  return allPoints;
}

/** 数据快照的 district 访问器（类型窄化辅助） */
export type { SchoolsSnapshot };
