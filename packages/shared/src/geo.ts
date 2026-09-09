/**
 * 地理工具 —— GCJ-02 平面距离、范围判断等纯函数。
 * 所有点位为 GCJ-02（高德），无需与 WGS-84 互转。
 */

/** 两点球面距离（Haversine），单位：米。输入 GCJ-02 经纬度即可（同坐标系内距离不受投影影响）。 */
export function distanceMeters(
  a: { lng: number; lat: number },
  b: { lng: number; lat: number },
): number {
  const R = 6371000;
  const rad = (d: number) => (d * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

/** 点是否落在矩形视野内（用于地图视野筛选，lng/lat 边界含等号） */
export function inBounds(
  p: { lng: number; lat: number },
  bounds: { north: number; south: number; east: number; west: number },
): boolean {
  return (
    p.lat <= bounds.north &&
    p.lat >= bounds.south &&
    p.lng <= bounds.east &&
    p.lng >= bounds.west
  );
}

/** 数字坐标规整（去掉浮点噪声，保留指定位数） */
export function roundCoord(v: number, digits = 5): number {
  const f = 10 ** digits;
  return Math.round(v * f) / f;
}

/** 按 adcode 统计学校数量 */
export function countByAdcode(schools: ReadonlyArray<{ adcode: string }>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const s of schools) out[s.adcode] = (out[s.adcode] ?? 0) + 1;
  return out;
}
