/** 首页只需三学段点位统计，避免触发地图/详情/链路数据仓库的全量加载。 */
import { hydrate, type SchoolsSnapshot } from '@gz/shared';
import primaryCompact from './compact/poi/dist/primary_poi.js';
import middleCompact from './compact/poi/dist/middle_poi.js';
import highCompact from './compact/poi/dist/high_poi.js';

const cast = <T>(value: unknown): T => value as T;

export const primarySchools = cast<SchoolsSnapshot>(hydrate(primaryCompact));
export const middleSchools = cast<SchoolsSnapshot>(hydrate(middleCompact));
export const highSchools = cast<SchoolsSnapshot>(hydrate(highCompact));
