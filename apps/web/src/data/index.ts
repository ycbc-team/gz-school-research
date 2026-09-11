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
import { matchBrandByPoiName, normName, ADCODE_TO_DISTRICT, type BrandGroupLite, type XiaoshengchuRecord, type XiaoshengchuSnapshot } from '@gz/shared';
import primarySchoolsJson from '../../../../data/primary/schools-gz.json';
import primaryTier1Json from '../../../../data/primary/tier1_schools_all.json';
import xiaoshengchuAllJson from '../../../../data/primary/xiaoshengchu_all.json';
import middleSchoolsJson from '../../../../data/middle/schools-gz.json';
import middleTier1Json from '../../../../data/middle/tier1_schools_all.json';
import highSchoolsJson from '../../../../data/high/schools-gz.json';
import highLevelsJson from '../../../../data/high/levels.json';
import enrollTianheJson from '../../../../data/primary/enrollments/2026-tianhe.json';
import enrollYuexiuJson from '../../../../data/primary/enrollments/2026-yuexiu.json';
import enrollHaizhuJson from '../../../../data/primary/enrollments/2026-haizhu.json';
import enrollLiwanJson from '../../../../data/primary/enrollments/2026-liwan.json';
import enrollPanyuJson from '../../../../data/primary/enrollments/2026-panyu.json';
import enrollBaiyunJson from '../../../../data/primary/enrollments/2026-baiyun.json';
import enrollHuangpuJson from '../../../../data/primary/enrollments/2026-huangpu.json';
import quotaMatrixJson from '../../../../data/linkage/quota_matrix.json';
import specialMatrixJson from '../../../../data/linkage/special_matrix.json';
import batch2ScoresJson from '../../../../data/linkage/batch2_scores.json';
import sitesRegistryJson from '../../../../data/registry/sites.json';
import brandGroupsJson from '../../../../data/registry/brand_groups.json';

/** JSON 推断类型与共享类型不一致处统一断言（字段为数据真源，结构由 scripts/ 保证） */
const cast = <T>(v: unknown): T => v as T;

export const primarySchools = cast<SchoolsSnapshot>(primarySchoolsJson);
export const primaryTier1 = cast<Tier1Snapshot>(primaryTier1Json);
/** 小学小升初升学路线全量真源（7 区，2026） */
export const xiaoshengchuAll = cast<XiaoshengchuSnapshot>(xiaoshengchuAllJson);
export const middleSchools = cast<SchoolsSnapshot>(middleSchoolsJson);
export const middleTier1 = cast<Tier1Snapshot>(middleTier1Json);
export const highSchools = cast<SchoolsSnapshot>(highSchoolsJson);
export const highLevels = cast<HighLevelsSnapshot>(highLevelsJson);

/** 完中判定：去括号 base 名同时出现在 middle 与 high POI 列表 → 初高中一体 */
function baseName(n: string): string {
  return n.replace(/（[^）]*）/g, '').replace(/\([^)]*\)/g, '').replace(/(初中部|高中部|小学部)$/, '').trim();
}
const middleBases = new Set(middleSchools.schools.map((s) => baseName(s.name)));
const highBases = new Set(highSchools.schools.map((s) => baseName(s.name)));
/** 判断某 POI 名是否为完全中学（初高中同法人同校区） */
export function isComprehensive(name: string): boolean {
  const b = baseName(name);
  return middleBases.has(b) && highBases.has(b);
}

/** linkage 升学通道数据（2026 官方） */
export interface QuotaSchool {
  page: number;
  row: number;
  school: string;
  kaosheng: number | null; // 名额考生数 m_j
  sheng_quota: number | null; // 省市属名额
  qu_quota: number | null; // 区属名额
  sz: Record<string, number | null>; // 21 省市属校区指标数 n_ji
  sz_sum: number;
  district: string | null;
}
export interface QuotaMatrix {
  schools: QuotaSchool[];
  districts: string[];
}
export interface SpecialMatrix {
  high_schools: string[];
  matrix: Record<string, Record<string, { sports?: number; arts?: number; autonomy?: number }>>;
}
export interface Batch2Record {
  admitted?: boolean;
  min_score?: number | null;
  last_score?: number | null;
}
export interface Batch2Scores {
  data: Record<string, Record<string, Batch2Record>>;
}
export const quotaMatrix = cast<QuotaMatrix>(quotaMatrixJson);
export const specialMatrix = cast<SpecialMatrix>(specialMatrixJson);
export const batch2Scores = cast<Batch2Scores>(batch2ScoresJson);

/** 21 省市属校区简称（quota_matrix.sz 键序） */
export const CAMPUS_SHORT = [
  '华附石牌', '华附知识城', '省实荔湾', '省实白云', '广雅荔湾', '广雅花都',
  '执信越秀', '执信天河', '二中', '六中海珠', '六中从化', '六中花都', '侨中',
  '协和', '广附', '铁一越秀', '铁一番禺', '铁一白云', '广州外国语', '清湾智谷', '清湾智慧城',
] as const;

/** 校区简称 → 归属高中（用于高中详情聚合） */
export const CAMPUS_SCHOOL: Record<string, string> = {
  华附石牌: '华南师范大学附属中学',
  华附知识城: '华南师范大学附属中学',
  省实荔湾: '广东实验中学',
  省实白云: '广东实验中学',
  广雅荔湾: '广东广雅中学',
  广雅花都: '广东广雅中学',
  执信越秀: '广州市执信中学',
  执信天河: '广州市执信中学',
  二中: '广州市第二中学',
  六中海珠: '广州市第六中学',
  六中从化: '广州市第六中学',
  六中花都: '广州市第六中学',
  侨中: '广东华侨中学',
  协和: '广州协和学校',
  广附: '广州大学附属中学',
  铁一越秀: '广州市铁一中学',
  铁一番禺: '广州市铁一中学',
  铁一白云: '广州市铁一中学',
  广州外国语: '广州市外国语学校',
  清湾智谷: '清华附中湾区学校',
  清湾智慧城: '清华附中湾区学校',
};

/** 校区简称 → special_matrix 键（全称） */
export const CAMPUS_TO_SPECIAL: Record<string, string> = {
  华附石牌: '华南师范大学附属中学（石牌）',
  华附知识城: '华南师范大学附属中学（知识城）',
  省实荔湾: '广东实验中学（荔湾）',
  省实白云: '广东实验中学（白云）',
  广雅荔湾: '广东广雅中学（荔湾）',
  广雅花都: '广东广雅中学（花都）',
  执信越秀: '广州市执信中学（执信路）',
  执信天河: '广州市执信中学（天河）',
  二中: '广州市第二中学',
  六中海珠: '广州市第六中学（海珠）',
  六中从化: '广州市第六中学（从化）',
  六中花都: '广州市第六中学（花都）',
  侨中: '广东华侨中学',
  协和: '',
  广附: '广州大学附属中学',
  铁一越秀: '广州市铁一中学（越秀）',
  铁一番禺: '广州市铁一中学（番禺）',
  铁一白云: '广州市铁一中学（白云）',
  广州外国语: '',
  清湾智谷: '清华附中湾区学校（智谷）',
  清湾智慧城: '清华附中湾区学校（智慧城）',
};

/** 校区简称 → batch2_scores 键（全称） */
export const CAMPUS_TO_BATCH2: Record<string, string> = {
  华附石牌: '华南师范大学附属中学（石牌校区）',
  华附知识城: '华南师范大学附属中学（知识城校区）',
  省实荔湾: '广东实验中学（荔湾校区）',
  省实白云: '广东实验中学（白云校区）',
  广雅荔湾: '广东广雅中学（荔湾校区）',
  广雅花都: '广东广雅中学（花都校区）',
  执信越秀: '广州市执信中学（执信路校区）',
  执信天河: '广州市执信中学（天河校区）',
  二中: '广州市第二中学',
  六中海珠: '广州市第六中学（海珠校区）',
  六中从化: '广州市第六中学（从化校区）',
  六中花都: '广州市第六中学（花都校区）',
  侨中: '广东华侨中学',
  协和: '广州协和学校',
  广附: '广州大学附属中学',
  铁一越秀: '广州市铁一中学（越秀校区）',
  铁一番禺: '广州市铁一中学（番禺校区）',
  铁一白云: '广州市铁一中学（白云校区）',
  广州外国语: '',
  清湾智谷: '清华附中湾区学校（智谷校区）',
  清湾智慧城: '清华附中湾区学校（智慧城校区）',
};

/** 初中名归一查找：POI 简称/变体 → quota_matrix 标准全称（精确→归一→包含兜底） */
const middleByNorm = new Map<string, string>();
for (const s of quotaMatrix.schools) {
  const nk = normSchoolName(s.school);
  if (nk && !middleByNorm.has(nk)) middleByNorm.set(nk, s.school);
}
/** 新开办待成绩初中（note 含「新开办」）：无成绩亦无升学通道数据，禁止模糊匹配到本部链路数据 */
const newOpeningMiddles = new Set<string>();
for (const s of middleSchools.schools) {
  if (s.note && s.note.includes('新开办')) newOpeningMiddles.add(s.name);
}
function resolveMiddle(poiName: string): string | null {
  if (newOpeningMiddles.has(poiName)) return null;
  if (quotaMatrix.schools.some((s) => s.school === poiName)) return poiName;
  const nk = normSchoolName(poiName);
  if (nk && middleByNorm.has(nk)) return middleByNorm.get(nk)!;
  for (const s of quotaMatrix.schools) {
    const sk = normSchoolName(s.school);
    if (sk.length >= 3 && (sk.includes(nk) || nk.includes(sk))) return s.school;
  }
  return null;
}

/** 按初中名查升学通道汇总 */
export function linkageOf(schoolName: string): QuotaSchool | undefined {
  const canon = resolveMiddle(schoolName);
  return canon ? quotaMatrix.schools.find((s) => s.school === canon) : undefined;
}

/** 按初中名查特殊通道（special_matrix 键 = 初中名） */
export function specialOf(schoolName: string): Record<string, { sports?: number; arts?: number; autonomy?: number }> | undefined {
  const canon = resolveMiddle(schoolName);
  return canon ? specialMatrix.matrix[canon] : undefined;
}

/** 按初中名查第二批次录取分数（值 = 校区 → 记录） */
export function batch2Of(schoolName: string): Record<string, Batch2Record> {
  const out: Record<string, Batch2Record> = {};
  const canon = resolveMiddle(schoolName);
  if (!canon) return out;
  for (const [campus, rows] of Object.entries(batch2Scores.data)) {
    if (rows[canon]) out[campus] = rows[canon];
  }
  return out;
}

/** 反查：某校区 n_ji>0 的初中（名额分配覆盖，按 n_ji 降序） */
export function quotaCoverage(campusShort: string, top?: number): { school: string; n: number; district: string | null }[] {
  const arr = quotaMatrix.schools
    .filter((s) => (s.sz[campusShort] ?? 0) > 0)
    .map((s) => ({ school: s.school, n: s.sz[campusShort] as number, district: s.district }))
    .sort((a, b) => b.n - a.n);
  return top ? arr.slice(0, top) : arr;
}

/** 反查：某校区在 special_matrix 有记录的初中（自招/体育/艺术） */
export function specialCoverage(campusShort: string): { school: string; sports: number; arts: number; autonomy: number }[] {
  const spKey = CAMPUS_TO_SPECIAL[campusShort];
  if (!spKey) return [];
  const arr: { school: string; sports: number; arts: number; autonomy: number }[] = [];
  for (const [school, hs] of Object.entries(specialMatrix.matrix)) {
    const rec = hs[spKey];
    if (rec) arr.push({ school, sports: rec.sports ?? 0, arts: rec.arts ?? 0, autonomy: rec.autonomy ?? 0 });
  }
  return arr.sort((a, b) => b.autonomy + b.sports + b.arts - (a.autonomy + a.sports + a.arts));
}

export const enrollments: EnrollmentSnapshot[] = [
  cast<EnrollmentSnapshot>(enrollTianheJson),
  cast<EnrollmentSnapshot>(enrollYuexiuJson),
  cast<EnrollmentSnapshot>(enrollHaizhuJson),
  cast<EnrollmentSnapshot>(enrollLiwanJson),
  cast<EnrollmentSnapshot>(enrollPanyuJson),
  cast<EnrollmentSnapshot>(enrollBaiyunJson),
  cast<EnrollmentSnapshot>(enrollHuangpuJson),
];

/* ========== 小学 2026 招生计划匹配（含校名变体归一） ========== */
const ENROLL_FLAT = enrollments.flatMap((e) => e.records);
/** 归一：去 广州市/广州 前缀、去括号及括号内容、去 小学/学校/校区 后缀 */
function normSchoolName(s: string): string {
  return s
    .replace(/^(广州市|广州)/, '')
    .replace(/（[^）]*）/g, '')
    .replace(/\([^)]*\)/g, '')
    .replace(/(小学|学校|校区|中学|初中)$/, '')
    .trim();
}
const enrollByExact = new Map<string, (typeof ENROLL_FLAT)[number]>();
const enrollByNorm = new Map<string, (typeof ENROLL_FLAT)[number]>();
for (const r of ENROLL_FLAT) {
  if (!enrollByExact.has(r.school)) enrollByExact.set(r.school, r);
  if (r.school_id && !enrollByExact.has(r.school_id)) enrollByExact.set(r.school_id, r);
  const nk = normSchoolName(r.school);
  if (nk && !enrollByNorm.has(nk)) enrollByNorm.set(nk, r);
  if (r.school_id) {
    const nk2 = normSchoolName(r.school_id);
    if (nk2 && !enrollByNorm.has(nk2)) enrollByNorm.set(nk2, r);
  }
}
/** 按小学名（POI 名）匹配 2026 招生计划：精确 → 归一 → 包含兜底 */
export function matchEnrollment(schoolName: string): { school: string; plan_classes?: number | null; nature?: string; zone?: string; note?: string; district?: string; source?: string; matchedBy: string } | null {
  const exact = enrollByExact.get(schoolName);
  if (exact) return { ...exact, matchedBy: 'exact' };
  const nk = normSchoolName(schoolName);
  if (nk) {
    const n = enrollByNorm.get(nk);
    if (n) return { ...n, matchedBy: 'norm' };
  }
  // 包含兜底：归一后互为子串（如 POI「沙面小学(凯粤湾校区)」↔ 计划「沙面小学凯粤湾校区」）
  const core = nk || schoolName;
  for (const [k, r] of enrollByNorm) {
    if (k.length >= 4 && (k.includes(core) || core.includes(k))) return { ...r, matchedBy: 'fuzzy' };
  }
  return null;
}

/** 初中名 → 名额分配摘要（模糊匹配 quota_matrix，用于小学出口列表轻量展示） */
export function middleQuotaSummary(name: string): { kaosheng: number | null; sheng_quota: number | null; qu_quota: number | null } | null {
  const find = (s: QuotaSchool) => ({ kaosheng: s.kaosheng, sheng_quota: s.sheng_quota, qu_quota: s.qu_quota });
  const exact = quotaMatrix.schools.find((s) => s.school === name);
  if (exact) return find(exact);
  const nk = normSchoolName(name);
  const normHit = quotaMatrix.schools.find((s) => normSchoolName(s.school) === nk);
  if (normHit) return find(normHit);
  const core = nk || name;
  for (const s of quotaMatrix.schools) {
    const sk = normSchoolName(s.school);
    if (sk.length >= 4 && (sk.includes(core) || core.includes(sk))) return find(s);
  }
  return null;
}

/** tier1 学校数组（跨区拍平） */
export const tier1Schools = Object.values(primaryTier1.districts).flatMap((d) => d.schools);
export const middleTier1Schools = Object.values(middleTier1.districts).flatMap((d) => d.schools);

/* ========== 小学升学路线（xiaoshengchu_all 全量真源，仅归一化全等，不做包含/前缀匹配） ========== */
/** 从 group 文本解析区名（如「番禺区小升初对口（单校）」→「番禺区」），无区前缀返回 null */
function districtOfGroup(group: string | null): string | null {
  if (!group) return null;
  const m = /(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区/.exec(group);
  return m ? `${m[1]}区` : null;
}
type XsRecord = XiaoshengchuRecord & { district: string | null };
const xsRecords: XsRecord[] = xiaoshengchuAll.records.map((r) => ({ ...r, district: districtOfGroup(r.group) }));
/** 归一化校名 → 记录列表（全等；跨区同名学校如「赤岗小学」保留多条，查询时按区消歧） */
const xsByNorm = new Map<string, XsRecord[]>();
for (const r of xsRecords) {
  const nk = normName(r.name);
  if (!nk) continue;
  if (!xsByNorm.has(nk)) xsByNorm.set(nk, []);
  xsByNorm.get(nk)!.push(r);
}
/**
 * 按 POI 名查小学升学路线：仅做 normName 归一化全等，不做任何部分/包含匹配。
 * district 可选（传「番禺区」区名或 6 位 adcode 均可），仅在跨区同名时精确消歧；
 * 不传或消歧不中时回退首条（确定性，不猜测）。
 */
export function xiaoshengchuOf(poiName: string, district?: string | null): XiaoshengchuRecord | null {
  const nk = normName(poiName);
  if (!nk) return null;
  const list = xsByNorm.get(nk);
  if (!list || !list.length) return null;
  if (list.length === 1) return list[0]!;
  const want = district && /^\d{6}$/.test(district) ? ADCODE_TO_DISTRICT[district] : district;
  if (want) {
    const hit = list.find((r) => r.district === want);
    if (hit) return hit;
  }
  return list[0]!;
}

/**
 * 反查：某初中的生源小学（全量小学的对口/派位名单包含本校）。
 * 键为对口初中名的 normName 归一化全等，不做包含匹配。
 */
const primaryFeedByMiddleNorm = new Map<string, { primary: string; group: string | null; direct_feed: string | null }[]>();
for (const p of xsRecords) {
  if (!p.feed_junior_highs?.length) continue;
  for (const mid of p.feed_junior_highs) {
    const nk = normName(mid);
    if (!nk) continue;
    if (!primaryFeedByMiddleNorm.has(nk)) primaryFeedByMiddleNorm.set(nk, []);
    primaryFeedByMiddleNorm.get(nk)!.push({ primary: p.name, group: p.group, direct_feed: p.direct_feed });
  }
}
export function middlePrimaryFeed(middleName: string): { primary: string; group: string | null; direct_feed: string | null }[] {
  const nk = normName(middleName);
  if (!nk) return [];
  return primaryFeedByMiddleNorm.get(nk) ?? [];
}

/**
 * 学校徽章组（详情页/地图搜索/地图点选浮层三处共用）：
 * 区域 · 学段 · 口碑 · 省/市示范。
 */
export interface SchoolBadge { text: string; cls: string }
export function schoolBadges(
  stage: 'primary' | 'middle' | 'high',
  opts: { district?: string; tier?: any; rec?: any; name?: string },
): SchoolBadge[] {
  const out: SchoolBadge[] = [];
  if (opts.district) out.push({ text: opts.district, cls: 'b-district' });
  // 学段 badge：完中同时标初中+高中
  const comprehensive = !!opts.name && isComprehensive(opts.name);
  if (stage === 'primary') out.push({ text: '小学', cls: 'b-stage' });
  else if (stage === 'middle') {
    out.push({ text: '初中', cls: 'b-stage' });
    if (comprehensive) out.push({ text: '高中', cls: 'b-stage' });
  } else {
    out.push({ text: '高中', cls: 'b-stage' });
    if (comprehensive) out.push({ text: '初中', cls: 'b-stage' });
  }
  const t = opts.tier;
  if (t) {
    if (t.tier1_eligible === false) out.push({ text: '挂牌', cls: 'b-license' });
    else out.push({ text: '口碑', cls: 'b-tier' });
  }
  if ((stage === 'high' || comprehensive) && opts.rec) {
    if (opts.rec.category === '省市属示范') out.push({ text: '省示范', cls: 'b-hcity' });
    else if (opts.rec.category === '区属示范') out.push({ text: '市示范', cls: 'b-hdist' });
  }
  // 注：demonstration_high 是高中示范级别，初中/小学不展示该 badge（避免把完中高中部级别误标成初中"省示范"）
  return out;
}
/** 口碑支撑度 badge（仅口碑信号卡内使用）：有支撑/部分支撑/无支撑 */
export function supportBadge(tier?: any): SchoolBadge | null {
  if (!tier) return null;
  if (tier.tier1_eligible === false) return { text: '未计入口碑校', cls: 'b-license' };
  const c = tier.conclusion;
  if (c === '有支撑') return { text: '有支撑', cls: 'b-full' };
  if (c === '部分支撑') return { text: '部分支撑', cls: 'b-part' };
  return { text: '无支撑', cls: 'b-none' };
}

/* ========== 学校身份注册表（site 粒度，统一匹配入口） ========== */
export interface Site {
  id: string;
  poi_name: string;
  district: string;
  stage: string;
  gov_names?: string[];
  aliases?: string[];
}
const registrySites: Site[] = (sitesRegistryJson as { schools: { sites: Site[] }[] }).schools.flatMap((s) => s.sites);
/** 任意来源名 → site（poi_name / gov_names / aliases 全量精确匹配） */
export function resolveSite(anyName: string): Site | null {
  if (!anyName) return null;
  for (const s of registrySites) {
    if (s.poi_name === anyName) return s;
    if ((s.gov_names || []).includes(anyName)) return s;
    if ((s.aliases || []).includes(anyName)) return s;
  }
  return null;
}

/* ========== 品牌关联表（同品牌多校区/多法人，详情页「品牌关联」板块） ========== */
export interface BrandUnit {
  name: string;
  role: string;
  /** same=与品牌核心同法人（计入口碑）；independent=独立法人（借用品牌→挂牌） */
  legal: 'same' | 'independent';
  /** 该单位的 POI 名覆盖（tier1 aliases 未覆盖其点位名时使用，如白云铁一=铁一中学白云校区） */
  poi_names?: string[];
}
export interface BrandGroup {
  brand: string;
  brand_note?: string;
  units: BrandUnit[];
}
export const brandGroups = cast<{
  title: string;
  verified_date: string;
  scope?: string;
  brands: BrandGroup[];
}>(brandGroupsJson);

/** 按任意校名（详情页当前学校名）匹配所属品牌组；未收录返回 null（仅全等匹配，POI 变体见 unit.poi_names） */
export function brandGroupOf(name: string): BrandGroup | null {
  if (!name) return null;
  const brand = matchBrandByPoiName(name, brandGroups.brands as unknown as BrandGroupLite[]);
  if (!brand) return null;
  return brandGroups.brands.find((g) => g.brand === brand) || null;
}
