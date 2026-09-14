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
}

export function initialFilterState(): MapFilterState {
  return {
    selectedDistricts: new Set(ALL_DISTRICT_ADCODES),
    selectedStages: new Set<SchoolStage>(ALL_STAGES),
    selectedGrades: new Set<ClsKey>(ALL_GRADES),
    selectedNatures: new Set<SchoolNature>(ALL_SCHOOL_NATURES),
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
}

/** 点位可见性：区域必选 + 多学部任一学段满足「学段×分级」双选 */
export function isVisible(state: MapFilterState, pt: MapPoint): boolean {
  if (!state.selectedDistricts.has(pt.adcode)) return false;
  return pt.stages.some((s) => state.selectedStages.has(s) && state.selectedGrades.has(pt.clsOf[s]) && state.selectedNatures.has(pt.natureOf[s]));
}
