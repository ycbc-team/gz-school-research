// -*- coding: utf-8 -*-
/**
 * 升学事实表升级：xiaoshengchu_all.json（裸名）→ xiaoshengchu_2026.json（school_id 外键，范式）。
 *
 * 事实表只存事实与来源，不存维度：
 *   school_id            小学实体（=POI 点位实体）
 *   group                派位/对口分组文本（事实）
 *   feed_school_ids[]    对口/派位初中实体 id（纯外键）
 *   feed_unresolved[]    未解析到 POI 的官方初中名（显式缺口，可审计，不做模糊匹配）
 *   direct_feed_school_id 直升初中实体 id
 *   source_url / source_note / data_gaps
 * district 由 school_id → POI.adcode join 得到，不存。
 *
 * 用法：node scripts/registry/upgrade_xiaoshengchu.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
const ROOT = path.resolve(import.meta.dirname, '..', '..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const write = (p, o) => fs.writeFileSync(path.join(ROOT, p), JSON.stringify(o, null, 2) + '\n');
const normName = (s) => !s ? '' : String(s).replace(/（/g,'(').replace(/）/g,')').replace(/^广州市/,'').replace(/[()]/g,'').replace(/\s+/g,'');

const entities = read('data/registry/entities.json').entities;
// norm alias -> entity（按 stage）
function aliasIndex(stage) {
  const m = new Map();
  for (const e of entities) if (e.stage === stage) for (const a of e.aliases) {
    const k = normName(a); if (!k) continue;
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(e);
  }
  return m;
}
const primaryAlias = aliasIndex('primary');
const middleAlias = aliasIndex('middle');
const AD = {'440103':'荔湾区','440104':'越秀区','440105':'海珠区','440106':'天河区','440111':'白云区','440112':'黄埔区','440113':'番禺区'};
const districtOfGroup = (g) => { if(!g) return null; const m=/(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区/.exec(g); return m ? m[1]+'区' : null; };
function resolve(idx, name, district) {
  const list = idx.get(normName(name));
  if (!list || !list.length) return null;
  if (list.length === 1) return list[0].school_id;
  const hit = list.find((e) => e.district_adhoc === district); // district 已不在 entity，用 POI join
  return (hit || list[0]).school_id;
}

// entity -> district（从 POI join）
const poiByStageName = {};
for (const [stage, file] of [['primary','data/primary/schools-gz.json'],['middle','data/middle/schools-gz.json'],['high','data/high/schools-gz.json']]) {
  poiByStageName[stage] = read(file).schools || [];
}
const entDistrict = new Map();
for (const e of entities) {
  const poi = (poiByStageName[e.stage]||[]).find(p => p.school_id === e.school_id);
  if (poi) entDistrict.set(e.school_id, AD[poi.adcode] || '');
}
// 小学 record 定位：跨区同名时按 district 取唯一实体（fact 主表外键必须唯一）
function resolveOne(idx, name, district) {
  const list = idx.get(normName(name));
  if (!list || !list.length) return null;
  if (list.length === 1) return list[0].school_id;
  const hit = list.find((e) => entDistrict.get(e.school_id) === district);
  return (hit || list[0]).school_id;
}
// feed 初中解析：同区多校区全收（如「广铁一中铁英学校」→ 东/西两校区），跨区同名按 district 过滤
function resolveMany(idx, name, district) {
  const list = idx.get(normName(name));
  if (!list || !list.length) return [];
  let picked = list;
  if (district) {
    const f = list.filter((e) => entDistrict.get(e.school_id) === district);
    if (f.length) picked = f;
  }
  return [...new Set(picked.map((e) => e.school_id))];
}

const src = read('data/primary/xiaoshengchu_all.json');
let primaryHit = 0, feedHit = 0, feedMiss = 0;
const outRecords = src.records.map((r) => {
  const district = districtOfGroup(r.group);
  const primaryId = resolveOne(primaryAlias, r.name, district);
  if (primaryId) primaryHit++;
  const feed_ids = [], feed_unresolved = [];
  for (const name of (r.feed_junior_highs || [])) {
    const ids = resolveMany(middleAlias, name, district);
    if (ids.length) feed_ids.push(...ids); else feed_unresolved.push(name);
  }
  return {
    school_id: primaryId,
    group: r.group,
    feed_school_ids: feed_ids,
    feed_unresolved,
    direct_feed_school_id: r.direct_feed ? resolveOne(middleAlias, r.direct_feed, district) : null,
    source_url: r.source_url, source_note: r.source_note, data_gaps: r.data_gaps,
  };
});
write('data/primary/xiaoshengchu_2026.json', {
  year: 2026,
  note: '2026 小学→初中升学事实表。学校一律用 school_id 引用（见 entities.json）；feed_school_ids 为对口初中实体 id，feed_unresolved 为 POI 未收录的官方名（显式缺口，不模糊）。district 由 POI join。',
  records: outRecords,
});
console.log(`records: ${outRecords.length}`);
console.log(`小学 record 解析 school_id: ${primaryHit}/${outRecords.length}`);
console.log(`feed 初中名 解析: ${feedHit}（未解析 ${feedMiss + 0}）；未解析唯一名: ${new Set(outRecords.flatMap(r=>r.feed_unresolved)).size}`);
console.log('天誉:', JSON.stringify(outRecords.find(r=>r.group.includes('亚运城配建'))?.feed_school_ids));
