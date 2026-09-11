/**
 * 地图域常量：区划、七类配色、学段色、筛选 UI 枚举。
 * 颜色值是 Web CSS 与小程序 marker 图标的唯一输入（双端配色一致）。
 */
import type { SchoolStage } from '../../types.js';

/** 七区（2026 数据范围） */
export const DISTRICTS: ReadonlyArray<{ name: string; adcode: string; color: string }> = [
  { name: '荔湾区', adcode: '440103', color: '#C0392B' },
  { name: '越秀区', adcode: '440104', color: '#B7950B' },
  { name: '海珠区', adcode: '440105', color: '#27AE60' },
  { name: '天河区', adcode: '440106', color: '#16A085' },
  { name: '白云区', adcode: '440111', color: '#2980B9' },
  { name: '黄埔区', adcode: '440112', color: '#6C3483' },
  { name: '番禺区', adcode: '440113', color: '#C2185B' },
];
export const districtByAdcode: Record<string, string> = Object.fromEntries(DISTRICTS.map((d) => [d.adcode, d.name]));
export const adcodeByDistrict: Record<string, string> = Object.fromEntries(DISTRICTS.map((d) => [d.name, d.adcode]));
export const ALL_DISTRICT_ADCODES = DISTRICTS.map((d) => d.adcode);

/** 七类点位分类（配色 + 学段 + 展示名） */
export const CLASS_CFG = {
  pN: { stage: 'primary', color: '#94A3B8', label: '小学·普通' },
  pT: { stage: 'primary', color: '#2563EB', label: '小学·口碑' },
  mN: { stage: 'middle', color: '#A8A29E', label: '初中·普通' },
  mT: { stage: 'middle', color: '#DC2626', label: '初中·口碑' },
  hN: { stage: 'high', color: '#64748B', label: '高中·普通' },
  hD: { stage: 'high', color: '#10B981', label: '高中·区属示范' },
  hM: { stage: 'high', color: '#F59E0B', label: '高中·省市属示范' },
} as const;
export type ClsKey = keyof typeof CLASS_CFG;
export const ALL_GRADES = Object.keys(CLASS_CFG) as ClsKey[];

/** 学段点色（用户要求：小学/初中/高中各一色；小学紫避免与品牌蓝撞色） */
export const STAGE_COLOR: Record<SchoolStage, string> = {
  primary: '#8B5CF6', // 小学 · 紫
  middle: '#DC2626', // 初中 · 红
  high: '#10B981', // 高中 · 绿
};
/** 学段优先级：多学部点主学部取最高（信息卡用主学部） */
export const STAGE_PRIORITY: Record<SchoolStage, number> = { primary: 0, middle: 1, high: 2 };

export const STAGE_LABEL: Record<SchoolStage, string> = { primary: '小学', middle: '初中', high: '高中' };
export const STAGE_TABS: Array<{ v: SchoolStage; l: string }> = [
  { v: 'primary', l: '小学' },
  { v: 'middle', l: '初中' },
  { v: 'high', l: '高中' },
];
export const ALL_STAGES: SchoolStage[] = ['primary', 'middle', 'high'];

/** 分级筛选分组（贝壳式浮层） */
export const GRADE_GROUPS: Array<{ title: string; stage: SchoolStage; items: Array<{ v: ClsKey; l: string }> }> = [
  { title: '小学', stage: 'primary', items: [{ v: 'pT', l: '口碑学校' }, { v: 'pN', l: '普通学校' }] },
  { title: '初中', stage: 'middle', items: [{ v: 'mT', l: '口碑学校' }, { v: 'mN', l: '普通学校' }] },
  { title: '高中', stage: 'high', items: [
    { v: 'hM', l: '市重点（省市属示范）' },
    { v: 'hD', l: '区重点（区属示范）' },
    { v: 'hN', l: '普通高中' },
  ]},
];
