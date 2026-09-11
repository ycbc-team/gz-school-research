// -*- coding: utf-8 -*-
/**
 * 学校实体注册表构建（范式：实体—点位—事实 三分离）。
 *
 * 单一真相：data/registry/entities.json
 *   - 每个"学校法人实体"一行，带稳定 school_id（不随改名/校区增减变化）
 *   - aliases[] 收齐：所有 POI 点位名 + tier1 别名 + sites.json 别名（normName 后去重）
 *   - 事实表（xiaoshengchu_2026 等）一律用 school_id 外键引用，不再裸名
 *
 * 归组策略（用户红线：只用全等/显式别名，不做模糊）：
 *   1) 显式别名优先：POI 名 normName 后命中 tier1/sites 的 alias 表 → 归入该实体
 *   2) 未命中的 POI：按 (adcode, canonical) 归组新建实体（canonical 去括号/校区后缀）
 *
 * 用法：node scripts/registry/build_entities.mjs   （幂等，可重复跑）
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const write = (p, obj) => fs.writeFileSync(path.join(ROOT, p), JSON.stringify(obj, null, 2) + '\n');

function normName(s) {
  if (!s) return '';
  return String(s).replace(/（/g, '(').replace(/）/g, ')')
    .replace(/^广州市/, '').replace(/[()]/g, '').replace(/\s+/g, '');
}
// canonical：剥括号内容 + 尾部校区/分校后缀；同区归组用
function canonicalOf(poiName) {
  return poiName
    .replace(/（/g, '(').replace(/）/g, ')')
    .replace(/^广州市/, '')
    .replace(/\([^)]*\)/g, '')                       // 括号内容整体去掉
    .replace(/[一-龥]{1,8}(校区|分校|分校区)/g, '')     // 括号外的“XX校区/分校”
    .replace(/\s+/g, '');
}
function idKey(adcode, canonicalNorm) {
  return 'gz-' + adcode + '-' + crypto.createHash('sha1').update(adcode + '|' + canonicalNorm).digest('hex').slice(0, 8);
}
// 派生别名：去掉开头的“XX区”前缀，使 POI 名「番禺区石楼中学」与官方组表名「石楼中学」全等
const DISTRICT_PREFIX = /^(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区/;
function withDistrictVariants(normAlias) {
  const out = [normAlias];
  if (DISTRICT_PREFIX.test(normAlias)) out.push(normAlias.replace(DISTRICT_PREFIX, ''));
  return out;
}

const AD_DISTRICT = {
  '440103': '荔湾区', '440104': '越秀区', '440105': '海珠区',
  '440106': '天河区', '440111': '白云区', '440112': '黄埔区', '440113': '番禺区',
};
const stageFiles = {
  primary: 'data/primary/schools-gz.json',
  middle: 'data/middle/schools-gz.json',
  high: 'data/high/schools-gz.json',
};

// ---- 1) 收集已知实体种子（tier1 别名 + sites.json）----
// seed: {canonicalRaw, stage, district, aliases:Set(norm), legacyId, poiSet:Set(norm)}
const seeds = [];
function addSeed(stage, district, canonicalRaw, aliases, legacyId) {
  if (!normName(canonicalRaw)) return;
  let e = seeds.find((x) => x.cNorm === normName(canonicalRaw) && x.stage === stage);
  if (!e) { e = { cNorm: normName(canonicalRaw), stage, district, aliases: new Set(), poiSet: new Set(), legacyId, canonicalRaw }; seeds.push(e); }
  for (const a of [canonicalRaw, ...aliases]) { const n = normName(a); if (n) e.aliases.add(n); }
}
for (const [stage, file] of [['primary', 'data/primary/tier1_schools_all.json'], ['middle', 'data/middle/tier1_schools_all.json']]) {
  const j = read(file);
  for (const [dist, blk] of Object.entries(j.districts || {}))
    for (const s of blk.schools || []) addSeed(stage, dist, s.name, s.aliases || []);
}
const sites = read('data/registry/sites.json');
for (const ent of sites.schools || []) {
  const stage = (ent.stages && ent.stages[0]) || 'high';
  addSeed(stage, '', ent.name, [...(ent.sites || []).map((x) => x.poi_name), ...(ent.aliases || [])], ent.id);
}
// 显式别名索引（norm alias -> seed），长名优先由查询端取；这里同名只取一个
const seedAlias = new Map();
for (const s of seeds) for (const a of s.aliases) { if (!seedAlias.has(a)) seedAlias.set(a, s); }

// ---- 2) 按学段遍历 POI：先命中显式别名，否则按 (adcode, canonical) 归组 ----
const entities = [];
const poiToId = new Map();
function pushEntity({ schoolId, canonicalRaw, stage, adcode, district, aliases, poiCount }) {
  entities.push({
    school_id: schoolId, canonical_name: canonicalRaw, stage, adcode, district,
    aliases: [...aliases].sort((a, b) => b.length - a.length), poi_count: poiCount,
  });
}
for (const [stage, file] of Object.entries(stageFiles)) {
  const pois = read(file).schools || read(file);
  // 2a. 命中显式别名的 POI 归入 seed
  const seedPoi = new Map(); // seed cNorm -> {aliases:Set, pois:[], district}
  const rest = [];
  for (const p of pois) {
    const sn = seedAlias.get(normName(p.name));
    if (sn) {
      if (!seedPoi.has(sn.cNorm)) seedPoi.set(sn.cNorm, { sn, aliases: new Set(sn.aliases), pois: [] });
      const bucket = seedPoi.get(sn.cNorm);
      bucket.pois.push(p); bucket.aliases.add(normName(p.name));
    } else rest.push(p);
  }
  for (const { sn, aliases, pois } of seedPoi.values()) {
    const adcode = pois[0].adcode;
    pushEntity({
      schoolId: sn.legacyId || idKey(adcode, sn.cNorm),
      canonicalRaw: sn.canonicalRaw, stage, adcode,
      district: sn.district || AD_DISTRICT[adcode] || '',
      aliases, poiCount: pois.length,
    });
    for (const p of pois) poiToId.set(stage + '|' + p.name, sn.legacyId || idKey(adcode, sn.cNorm));
  }
  // 2b. 未命中的 POI 按 (adcode, canonical) 归组
  const buckets = new Map();
  for (const p of rest) {
    const key = p.adcode + '|' + canonicalOf(p.name);
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(p);
  }
  for (const [, group] of buckets) {
    const adcode = group[0].adcode;
    const cNorm = canonicalOf(group[0].name);
    const schoolId = idKey(adcode, cNorm);
    const aliases = new Set(group.map((p) => normName(p.name)));
    pushEntity({ schoolId, canonicalRaw: group[0].name, stage, adcode, district: AD_DISTRICT[adcode] || '', aliases, poiCount: group.length });
    for (const p of group) poiToId.set(stage + '|' + p.name, schoolId);
  }
}

// ---- 3) 回写 POI school_id ----
for (const [stage, file] of Object.entries(stageFiles)) {
  const j = read(file);
  for (const p of (j.schools || j)) p.school_id = poiToId.get(stage + '|' + p.name) || null;
  write(file, j);
}
// 别名补充：为每个实体加“去区名前缀”派生别名（显式、全等，非模糊）
for (const e of entities) {
  const exp = new Set();
  for (const a of e.aliases) for (const v of withDistrictVariants(a)) exp.add(v);
  e.aliases = [...exp].sort((a, b) => b.length - a.length);
}
write('data/registry/entities.json', {
  year: 2026,
  note: '学校法人实体注册表（维度表，跨年稳定）。事实表一律用 school_id 外键；别名见各实体 aliases。',
  entities: entities.sort((a, b) => (a.district + a.canonical_name).localeCompare(b.district + b.canonical_name, 'zh')),
});

// ---- 统计 ----
const noId = { primary: 0, middle: 0, high: 0 };
for (const [stage, file] of Object.entries(stageFiles))
  for (const p of (read(file).schools || read(file))) if (!p.school_id) noId[stage]++;
console.log(`实体数: ${entities.length}`);
console.log(`  primary: ${entities.filter(e=>e.stage==='primary').length} | POI未配id: ${noId.primary}`);
console.log(`  middle : ${entities.filter(e=>e.stage==='middle').length} | POI未配id: ${noId.middle}`);
console.log(`  high   : ${entities.filter(e=>e.stage==='high').length} | POI未配id: ${noId.high}`);
const df = entities.find(e => e.canonical_name.includes('东风东路'));
console.log('  东风东路:', df.school_id, '| aliases:', df.aliases);
