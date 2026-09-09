/**
 * 数据加载层：Web 端统一从 data/（JSON 唯一真源）加载数据，类型由 @gz/shared 提供。
 * 小程序端对应实现见 apps/miniprogram/utils/data.js（构建时拷贝同一份 JSON）。
 */
import type {
  SchoolsSnapshot,
  Tier1Snapshot,
  HighLevelsSnapshot,
  EnrollmentSnapshot,
} from '@gz/shared';
import primarySchoolsJson from '../../../../data/primary/schools-gz.json';
import primaryTier1Json from '../../../../data/primary/tier1_schools_all.json';
import middleSchoolsJson from '../../../../data/middle/schools-gz.json';
import middleTier1Json from '../../../../data/middle/tier1_schools_all.json';
import highSchoolsJson from '../../../../data/high/schools-gz.json';
import highLevelsJson from '../../../../data/high/levels.json';
import enrollTianheJson from '../../../../data/primary/enrollments/2026-tianhe.json';
import enrollYuexiuJson from '../../../../data/primary/enrollments/2026-yuexiu.json';
import enrollHaizhuJson from '../../../../data/primary/enrollments/2026-haizhu.json';
import enrollLiwanJson from '../../../../data/primary/enrollments/2026-liwan.json';
import enrollPanyuJson from '../../../../data/primary/enrollments/2026-panyu.json';

/** JSON 推断类型与共享类型不一致处统一断言（字段为数据真源，结构由 scripts/ 保证） */
const cast = <T>(v: unknown): T => v as T;

export const primarySchools = cast<SchoolsSnapshot>(primarySchoolsJson);
export const primaryTier1 = cast<Tier1Snapshot>(primaryTier1Json);
export const middleSchools = cast<SchoolsSnapshot>(middleSchoolsJson);
export const middleTier1 = cast<Tier1Snapshot>(middleTier1Json);
export const highSchools = cast<SchoolsSnapshot>(highSchoolsJson);
export const highLevels = cast<HighLevelsSnapshot>(highLevelsJson);

export const enrollments: EnrollmentSnapshot[] = [
  cast<EnrollmentSnapshot>(enrollTianheJson),
  cast<EnrollmentSnapshot>(enrollYuexiuJson),
  cast<EnrollmentSnapshot>(enrollHaizhuJson),
  cast<EnrollmentSnapshot>(enrollLiwanJson),
  cast<EnrollmentSnapshot>(enrollPanyuJson),
];

/** tier1 学校数组（跨区拍平） */
export const tier1Schools = Object.values(primaryTier1.districts).flatMap((d) => d.schools);
export const middleTier1Schools = Object.values(middleTier1.districts).flatMap((d) => d.schools);
