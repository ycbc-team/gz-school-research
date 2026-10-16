/**
 * 地图域筛选状态机（纯 TS，双端共享）：
 * 状态以普通 Set 承载（Web 用 ref 包一层做响应式，小程序 data 同构），
 * 转换与判定逻辑单点维护，避免双端行为漂移。
 */
import type { SchoolStage } from '../../types.js';
import { CLASS_CFG, ALL_DISTRICT_ADCODES, ALL_STAGES, ALL_GRADES, ALL_SCHOOL_NATURES, type ClsKey, type SchoolNature } from './constants.js';

export interface MapFilterState {
  selectedDistricts: Set<string>;
  selectedStages: Set<SchoolStage>;
  selectedGrades: Set<ClsKey>;
  selectedNatures: Set<SchoolNature>;
  /** 地理维度：行政区/板块 与 地铁 互斥单选（UI 04/04B），各自保留已选 */
  regionDim: 'district' | 'metro';
  /** 板块（id 形如 `440113-p1`，前缀即 adcode）选中集合；空 = 不限板块 */
  selectedPlates: Set<string>;
  /** 地铁站点（id 形如 `line-1-s1`）选中集合；空 = 不限地铁 */
  selectedStations: Set<string>;
}

export function initialFilterState(): MapFilterState {
  return {
    selectedDistricts: new Set(ALL_DISTRICT_ADCODES),
    selectedStages: new Set<SchoolStage>(ALL_STAGES),
    selectedGrades: new Set<ClsKey>(ALL_GRADES),
    selectedNatures: new Set<SchoolNature>(ALL_SCHOOL_NATURES),
    regionDim: 'district',
    selectedPlates: new Set<string>(),
    selectedStations: new Set<string>(),
  };
}

/** 不可变 toggle：返回新 Set（Web ref / 小程序 setData 均直接替换） */
export function toggleSet<T>(set: Set<T>, v: T): Set<T> {
  const s = new Set(set);
  if (s.has(v)) s.delete(v);
  else s.add(v);
  return s;
}
export function toggleDistrict(state: MapFilterState, ad: string): MapFilterState {
  return { ...state, selectedDistricts: toggleSet(state.selectedDistricts, ad) };
}
export function toggleStage(state: MapFilterState, v: SchoolStage): MapFilterState {
  return { ...state, selectedStages: toggleSet(state.selectedStages, v) };
}
export function toggleGrade(state: MapFilterState, v: ClsKey): MapFilterState {
  return { ...state, selectedGrades: toggleSet(state.selectedGrades, v) };
}
export function toggleNature(state: MapFilterState, v: SchoolNature): MapFilterState {
  return { ...state, selectedNatures: toggleSet(state.selectedNatures, v) };
}

/** 地理维度切换（行政区/板块 ↔ 地铁），互斥单选、各自保留已选 */
export function setRegionDim(state: MapFilterState, dim: 'district' | 'metro'): MapFilterState {
  return { ...state, regionDim: dim };
}
/** 板块单选：选中时同步把其所属行政区加入 selectedDistricts（板块必落于某区） */
export function togglePlate(state: MapFilterState, plateId: string): MapFilterState {
  const ad = plateId.split('-')[0]!;
  const plates = toggleSet(state.selectedPlates, plateId);
  let districts = state.selectedDistricts;
  if (plates.has(plateId)) {
    districts = new Set(state.selectedDistricts);
    districts.add(ad);
  }
  return { ...state, selectedPlates: plates, selectedDistricts: districts };
}
/** 「全部 xx 区」：确保该区整体选中并清除其下已选板块（= 不限定板块）。
 *  幂等：本就整体选中时仍保持整体选中（不再反转为取消），取消某区由第一列行政区行承担。 */
export function selectAllPlatesInDistrict(state: MapFilterState, adcode: string): MapFilterState {
  const districts = new Set(state.selectedDistricts);
  districts.add(adcode);
  const plates = new Set([...state.selectedPlates].filter((pid) => pid.split('-')[0] !== adcode));
  return { ...state, selectedDistricts: districts, selectedPlates: plates };
}
/** 地铁站点单选（维度内独立，线由 focus 单独控制） */
export function toggleStation(state: MapFilterState, stationId: string): MapFilterState {
  return { ...state, selectedStations: toggleSet(state.selectedStations, stationId) };
}

/** 全选/全不选翻转 */
export function flipAll<T>(set: Set<T>, all: readonly T[]): Set<T> {
  return set.size === all.length ? new Set<T>() : new Set(all);
}
export function flipDistricts(state: MapFilterState): MapFilterState {
  return { ...state, selectedDistricts: flipAll(state.selectedDistricts, ALL_DISTRICT_ADCODES) };
}
export function flipStages(state: MapFilterState): MapFilterState {
  return { ...state, selectedStages: flipAll(state.selectedStages, ALL_STAGES) };
}
export function flipGrades(state: MapFilterState): MapFilterState {
  return { ...state, selectedGrades: flipAll(state.selectedGrades, ALL_GRADES) };
}
export function flipNatures(state: MapFilterState): MapFilterState {
  return { ...state, selectedNatures: flipAll(state.selectedNatures, ALL_SCHOOL_NATURES) };
}

/** 全选判定 */
export function districtAll(state: MapFilterState): boolean {
  return state.selectedDistricts.size === ALL_DISTRICT_ADCODES.length;
}
export function stageAll(state: MapFilterState): boolean {
  return state.selectedStages.size === ALL_STAGES.length;
}
export function gradeAll(state: MapFilterState): boolean {
  return state.selectedGrades.size === ALL_GRADES.length;
}
export function natureAll(state: MapFilterState): boolean {
  return state.selectedNatures.size === ALL_SCHOOL_NATURES.length;
}

export interface MapPoint {
  name: string;
  /** 实体主键；同名学校的详情跳转与回图定位必须以此消歧。 */
  school_id?: string;
  lat: number;
  lng: number;
  adcode: string;
  /** 该点位覆盖的学部（升序：小学→初中→高中，决定垂直分色顺序） */
  stages: SchoolStage[];
  /** 各学部自己的分级类（口碑/普通、示范/普通） */
  clsOf: Record<SchoolStage, ClsKey>;
  /** 各学部的办学性质；无明确非公办记录时按公办 POI 处理。 */
  natureOf: Record<SchoolStage, SchoolNature>;
  /** 主学部：stages 中优先级最高的（信息卡/描边/晕光判定用） */
  mainStage: SchoolStage;
  /** 所属板块 id（同区内最近板块中心，id 前缀即 adcode）；无板块数据时为 undefined */
  plateId?: string;
  /** 半径内地铁站点 id 集合（04B 地铁维度过滤用）；无地铁数据时为 [] */
  stationIds: string[];
}

/** 点位可见性：学段×分级×性质（属性维度，与地理维度正交，始终生效）
 *  + 地理维度（行政区 / 板块 / 地铁，互斥）：
 *    - **只有行政区维度执行过滤**（按 adcode 剔除区外点位）；
 *    - 板块 / 地铁站为「仅定位、不过滤」：选中后地图只切到该选项及其邻域，
 *      学校点位保持全量展示，不再因plateId/半径映射吞掉周边学校。 */
export function isVisible(state: MapFilterState, pt: MapPoint): boolean {
  if (!pt.stages.some((s) => state.selectedStages.has(s) && state.selectedGrades.has(pt.clsOf[s]) && state.selectedNatures.has(pt.natureOf[s]))) return false;
  // 板块 / 地铁站选中 → 纯定位，不做任何地理过滤（点位全量保留）
  if (state.selectedPlates.size > 0 || state.selectedStations.size > 0) return true;
  if (state.regionDim === 'metro') return true; // 地铁维度未选任何站点 → 全量
  return state.selectedDistricts.has(pt.adcode);
}
