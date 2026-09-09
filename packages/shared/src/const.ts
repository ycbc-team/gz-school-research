/**
 * 共享常量 —— 与 data/ 口径保持一致。
 */

/** 七区范围（与 scripts/ 采集口径一致，排除远郊南沙/花都/从化/增城） */
export const GZ_DISTRICTS: ReadonlyArray<{ name: string; adcode: string }> = [
  { name: '荔湾区', adcode: '440103' },
  { name: '越秀区', adcode: '440104' },
  { name: '海珠区', adcode: '440105' },
  { name: '天河区', adcode: '440106' },
  { name: '白云区', adcode: '440111' },
  { name: '黄埔区', adcode: '440112' },
  { name: '番禺区', adcode: '440113' },
];

export const ADCODE_TO_DISTRICT: Readonly<Record<string, string>> = Object.freeze(
  Object.fromEntries(GZ_DISTRICTS.map((d) => [d.adcode, d.name])),
);

/** 支撑度结论 → 展示语义（民间口径标签，非官方评价） */
export const VERDICT_LABEL: Readonly<Record<'有支撑' | '部分支撑' | '不支撑', string>> = {
  有支撑: '有支撑',
  部分支撑: '部分支撑',
  不支撑: '不支撑',
};

/** 高中分类 → 展示文案（levels.json category 口径） */
export const HIGH_CATEGORY_LABEL: Readonly<Record<string, string>> = {
  省市属示范: '省市属示范',
  区属示范: '区属示范',
  普通: '普通',
};

/** 坐标参考：GCJ-02，高德坐标系（无需转换即可用于高德瓦片与微信小程序 <map>） */
export const COORD_SYSTEM = 'GCJ-02';
