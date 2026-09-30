/**
 * 地图域点位构建：三学段 POI → 合并多学部点（同 school_id）+ 高中分类。
 * 纯逻辑，零地图库依赖；Web Leaflet 与小程序 <map> 共用同一份点集。
 * 注：tier1（口碑补点/梯队挂载）已于 2026-09-30 废弃，点位仅来自 POI 真源。
 */
import { normName } from '../../support.js';
import type { HighLevelSchool, SchoolStage, SchoolsSnapshot } from '../../types.js';
import type { DataLoaders } from '../../data/loader.js';
import type { MapPoint } from './filters.js';
import { districtByAdcode, STAGE_PRIORITY, type ClsKey, type SchoolNature } from './constants.js';

/** 完整点位（含信息卡所需字段） */
export interface MapPointFull extends MapPoint {
  /** 高中分类记录（高中学部） */
  rec: HighLevelSchool | null;
  /** 各学部点位实体 id（同址多 POI 合并为多学部点位时分别记录；单学部 = { [mainStage]: school_id }） */
  ids: Partial<Record<SchoolStage, string>>;
  /** 参与合并的各学部 POI 名（搜索/定位按任意学部名命中） */
  names: string[];
  /** 各学部 POI 名（内部：合并点主名取主学部 POI 名，如九年制小学部/初中部两 POI 同址合并） */
  stageNames: Partial<Record<SchoolStage, string>>;
}

export function buildPoints(loaders: DataLoaders): MapPointFull[] {
  const { primarySchools, middleSchools, highSchools, highLevels } = loaders;

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
  // 办学性质唯一真源：实体表 nature（公办不写字段）；按 school_id 精确
  const entityNatureById = new Map<string, string>();
  for (const e of loaders.entities.entities) {
    if (e.nature) entityNatureById.set(e.school_id, e.nature);
  }
  const schoolNature = (schoolId: string | undefined): SchoolNature =>
    entityNatureById.get(schoolId || '') === '民办' ? 'private' : 'public';

  function addSchool(
    s: { name: string; lat: number; lng: number; adcode: string; school_id?: string },
    stage: SchoolStage,
    cls: ClsKey,
    rec: HighLevelSchool | null,
  ) {
    if (!districtByAdcode[s.adcode]) return;
    // 同 school_id = 同校区多学部；再按同区同坐标合并（同址多 POI 学部，
    // 如九年制学校小学部/初中部两个独立 POI 共用坐标 → 一个多学部点位，避免地图上互相遮挡只点到其一）
    const key = s.school_id || `name:${s.name}`;
    let pt = ptByKey.get(key);
    if (!pt) pt = allPoints.find((q) => q.adcode === s.adcode && q.lat === s.lat && q.lng === s.lng);
    if (!pt) {
      pt = {
        name: s.name, school_id: s.school_id, lat: s.lat, lng: s.lng, adcode: s.adcode,
        stages: [], clsOf: {} as Record<SchoolStage, ClsKey>, natureOf: {} as Record<SchoolStage, SchoolNature>,
        rec: null, mainStage: stage,
        ids: {}, names: [], stageNames: {},
      };
      ptByKey.set(key, pt);
      allPoints.push(pt);
    }
    if (!pt.stages.includes(stage)) {
      pt.stages.push(stage);
      pt.clsOf[stage] = cls;
      pt.natureOf[stage] = schoolNature(s.school_id);
    }
    if (s.school_id) pt.ids[stage] = s.school_id;
    if (!pt.names.includes(s.name)) pt.names.push(s.name);
    pt.stageNames[stage] = s.name;
    if (stage === 'high' && rec) pt.rec = rec;
  }

  for (const s of primarySchools.schools) {
    addSchool(s, 'primary', 'pN', null);
  }
  for (const s of middleSchools.schools) {
    addSchool(s, 'middle', 'mN', null);
  }
  for (const s of highSchools.schools) {
    const rec = highRecord(s);
    addSchool(s, 'high', highCls(rec), rec ?? null);
  }

  // 统一：stages 升序、主学部取最高优先级；合并点主名取主学部 POI 名
  for (const pt of allPoints) {
    pt.stages.sort((a, b) => STAGE_PRIORITY[a] - STAGE_PRIORITY[b]);
    pt.mainStage = pt.stages[pt.stages.length - 1]!;
    if (pt.stageNames[pt.mainStage]) pt.name = pt.stageNames[pt.mainStage]!;
    if (!pt.ids[pt.mainStage] && pt.school_id) pt.ids[pt.mainStage] = pt.school_id;
  }
  return allPoints;
}

/** 数据快照的 district 访问器（类型窄化辅助） */
export type { SchoolsSnapshot };
