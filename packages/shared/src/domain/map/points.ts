/**
 * 地图域点位构建：三学段 POI → 合并多学部点（同 school_id）+ tier/高中分类 + 补点去重。
 * 纯逻辑，零地图库依赖；Web Leaflet 与小程序 <map> 共用同一份点集。
 */
import { buildAliasTable, matchTier1ByPoiName, normName } from '../../support.js';
import type { Tier1School, HighLevelSchool, SchoolStage, SchoolsSnapshot } from '../../types.js';
import type { DataLoaders } from '../../data/loader.js';
import type { MapPoint } from './filters.js';
import { adcodeByDistrict, districtByAdcode, STAGE_PRIORITY, type ClsKey, type SchoolNature } from './constants.js';

/** 完整点位（含信息卡所需字段） */
export interface MapPointFull extends MapPoint {
  /** 各学部梯队记录（小学/初中口碑校） */
  tierOf: Partial<Record<SchoolStage, Tier1School | null>>;
  /** 高中分类记录（高中学部） */
  rec: HighLevelSchool | null;
  /** 主学部梯队记录（= tierOf[mainStage]） */
  tier: Tier1School | null;
  /** 各学部点位实体 id（同址多 POI 合并为多学部点位时分别记录；单学部 = { [mainStage]: school_id }） */
  ids: Partial<Record<SchoolStage, string>>;
  /** 参与合并的各学部 POI 名（搜索/定位按任意学部名命中） */
  names: string[];
  /** 各学部 POI 名（内部：合并点主名取主学部 POI 名，如九年制小学部/初中部两 POI 同址合并） */
  stageNames: Partial<Record<SchoolStage, string>>;
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
  const enrollmentNatureById = new Map(loaders.enrollments.flatMap((x) => x.records).map((r) => [r.school_id, r.nature]));
  const highNatureById = new Map(Object.entries(loaders.highScores2026.by_school_id).map(([id, rows]) => [id, rows[0]?.nature || '']));
  const schoolNature = (stage: SchoolStage, schoolId: string | undefined, tier: Tier1School | null, rec: HighLevelSchool | null): SchoolNature => {
    const raw = stage === 'primary'
      ? enrollmentNatureById.get(schoolId || '')
      : stage === 'high'
        ? (rec?.nature || highNatureById.get(schoolId || ''))
        : undefined;
    const entityType = tier?.legal_entity?.type;
    return [raw, entityType].some((v) => typeof v === 'string' && v && !v.includes('公办')) ? 'private' : 'public';
  };
  function addSchool(
    s: { name: string; lat: number; lng: number; adcode: string; school_id?: string; note?: string },
    stage: SchoolStage,
    cls: ClsKey,
    tier: Tier1School | null,
    rec: HighLevelSchool | null,
  ) {
    if (!districtByAdcode[s.adcode]) return;
    // 同 school_id = 同校区多学部；补点无 school_id 时按名合并；再按同区同坐标合并（同址多 POI 学部，
    // 如九年制学校小学部/初中部两个独立 POI 共用坐标 → 一个多学部点位，避免地图上互相遮挡只点到其一）
    const key = s.school_id || `name:${s.name}`;
    let pt = ptByKey.get(key);
    if (!pt) pt = allPoints.find((q) => q.adcode === s.adcode && q.lat === s.lat && q.lng === s.lng);
    if (!pt) {
      pt = {
        name: s.name, school_id: s.school_id, lat: s.lat, lng: s.lng, adcode: s.adcode,
        stages: [], clsOf: {} as Record<SchoolStage, ClsKey>, natureOf: {} as Record<SchoolStage, SchoolNature>,
        tierOf: {}, rec: null, mainStage: stage, tier: null,
        ids: {}, names: [], stageNames: {},
      };
      ptByKey.set(key, pt);
      allPoints.push(pt);
    }
    if (!pt.stages.includes(stage)) {
      pt.stages.push(stage);
      pt.clsOf[stage] = cls;
      pt.natureOf[stage] = schoolNature(stage, s.school_id, tier, rec);
      pt.tierOf[stage] = tier;
    }
    if (s.school_id) pt.ids[stage] = s.school_id;
    if (!pt.names.includes(s.name)) pt.names.push(s.name);
    pt.stageNames[stage] = s.name;
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

  // 统一：stages 升序、主学部取最高优先级、主学部 tier；合并点主名取主学部 POI 名
  for (const pt of allPoints) {
    pt.stages.sort((a, b) => STAGE_PRIORITY[a] - STAGE_PRIORITY[b]);
    pt.mainStage = pt.stages[pt.stages.length - 1]!;
    pt.tier = pt.tierOf[pt.mainStage] ?? null;
    if (pt.stageNames[pt.mainStage]) pt.name = pt.stageNames[pt.mainStage]!;
    if (!pt.ids[pt.mainStage] && pt.school_id) pt.ids[pt.mainStage] = pt.school_id;
  }
  return allPoints;
}

/** 数据快照的 district 访问器（类型窄化辅助） */
export type { SchoolsSnapshot };
