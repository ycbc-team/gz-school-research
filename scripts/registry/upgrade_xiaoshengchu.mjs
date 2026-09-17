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
// 点位合并覆盖（实体删除/合并后旧 POI 名须归并到保留实体）：
// 景泰小学柯子岭校区43号A座 gz-440111-8d42bf12 与柯子岭校区同址冗余（2026-09-17 用户确认，
// build_entities DROP_CAMPUS 剔除）→ 归并到柯子岭校区 gz-440111-9e34191e。
const RESOLVE_OVERRIDE = {
  '景泰小学柯子岭校区43号A座': ['gz-440111-9e34191e'],
  // 跨区同名：白云「龙溪小学」(民办, fd1c0f9d) 与 荔湾「西关实验小学龙溪学校」(公办, 53fbb2c8)
  // 别名都含「龙溪小学」；no_feed 记录 group 无区名 → districtOfGroup 为 null，resolveOne
  // fallback 到首个匹配（荔湾）造成错配。显式归位白云实体。
  '龙溪小学': ['gz-440111-fd1c0f9d'],
};
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
  const ov = RESOLVE_OVERRIDE[normName(name)];
  if (ov) return ov[0];
  const list = idx.get(normName(name));
  if (!list || !list.length) return null;
  if (list.length === 1) return list[0].school_id;
  const hit = list.find((e) => entDistrict.get(e.school_id) === district);
  return (hit || list[0]).school_id;
}
// 校区 → 升学归属区 图（quota_matrix 权威）：法人行 school_ids（如越秀七中行含白云桂花校区）
// 与校区限定行 school_id 共同标注「该校区参与哪个区的升学」。
// 判定标准（用户口径）：POI 地理位置 ≠ 升学归属——桂花校区 POI 在白云，但白云升学无它、
// 越秀七中法人行收录 → 归属越秀；广附大学城在番禺校区行 → 归属番禺，越秀派位不含。
const campusDist = new Map(); // school_id -> 归属区（如「越秀区」）
for (const s of (read('data/linkage/quota_matrix.json').schools || [])) {
  if (!s.district) continue;
  if (s.school_id) campusDist.set(s.school_id, s.district);
  for (const sid of s.school_ids || []) campusDist.set(sid, s.district);
}

// 法人名归一：去括号校区/学部后缀 + 去「广州市」前缀；保留「X区」区名前缀——
// 使「育才中学(东校区)」（POI 无广州市前缀）与「广州市育才中学(西校区)」归同一法人，
// 同时隔离不同法人（「广州市从化区第七中学」→「从化区第七中学」≠「第七中学」，不混入）。
// 只去「广州市」不去「广州」：避免「广州中学」→「中学」历史毁名；「广州大学附属中学」保持原样。
function coreOfName(raw) {
  return String(raw || '').replace(/（/g, '(').replace(/）/g, ')')
    .replace(/\([^()]*\)/g, '').replace(/^广州市/, '').replace(/\s+/g, '');
}

// feed 初中解析：
// 1) alias 精确优先（校区限定名与官方别名都走这，如「广铁一中番禺校区」「广铁一中铁英学校」）
//    → 按 POI 区过滤；区过滤为空（跨区命中如白云桂花持裸名）→ 清空
// 2) alias 空/被滤后：
//    - 校区限定名（带括号）→ unresolved（宁缺，不模糊匹配）
//    - 法人裸名（无括号）→ 按法人 core 聚合全部同 stage 校区，再按「升学归属区」
//      （quota 法人行收录，如越秀七中行含白云桂花校区/越秀十六中行含天河水荫校区）过滤——
//      跨区法人校区按归属收录（桂花归越秀），别区法人校区（广附大学城归番禺）排除；
//      无归属信息时按 POI 区兜底合并（育才东 quota 未挂但 POI 在越秀），宁缺不跨区。
function resolveMany(idx, name, district, stage) {
  const ov = RESOLVE_OVERRIDE[normName(name)];
  if (ov) return [...ov];
  const hasCampus = /[（(]/.test(name);
  let picked = idx.get(normName(name)) || [];
  if (district) {
    const f = picked.filter((e) => entDistrict.get(e.school_id) === district);
    if (f.length) picked = f;
    else picked = [];
  }
  if (picked.length) return [...new Set(picked.map((e) => e.school_id))];
  if (hasCampus) return [];
  const core = coreOfName(name);
  const all = entities.filter((e) => e.stage === stage && coreOfName(e.name) === core);
  if (district) {
    const byOwn = all.filter((e) => campusDist.get(e.school_id) === district);
    if (byOwn.length) {
      // 归属区命中 → 同法人未挂 quota 的校区按 POI 区兜底合并（如育才东校区 quota 未挂但 POI 在越秀）
      const rest = all.filter((e) => !campusDist.has(e.school_id) && entDistrict.get(e.school_id) === district);
      return [...new Set([...byOwn, ...rest].map((e) => e.school_id))];
    }
    const byPoi = all.filter((e) => entDistrict.get(e.school_id) === district);
    if (byPoi.length) return [...new Set(byPoi.map((e) => e.school_id))];
  }
  return [...new Set(all.map((e) => e.school_id))];
}

const src = read('data/primary/xiaoshengchu_all.json');
let primaryHit = 0, feedHit = 0, feedMiss = 0;
const outRecords = src.records.map((r) => {
  const district = districtOfGroup(r.group);
  const primaryId = resolveOne(primaryAlias, r.name, district);
  if (primaryId) primaryHit++;
  const feed_ids = [], feed_unresolved = [];
  for (const name of (r.feed_junior_highs || [])) {
    const ids = resolveMany(middleAlias, name, district, 'middle');
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
// 同 (group, school_id) 去重：同一小学多源名/多条源记录（更名残留、实体合并、源表重复行）
// 解析到同一实体时，feed 并集、保留较完整 note——产物层单条，避免前端同校重复展示。
// （school_id 为空的历史缺口记录不合并，保持逐条可排查。）
const deduped = [];
{
  const byKey = new Map();
  for (const r of outRecords) {
    if (!r.school_id) { deduped.push(r); continue; }
    const k = `${r.group || ''}\u0000${r.school_id}`;
    const prev = byKey.get(k);
    if (!prev) { byKey.set(k, r); continue; }
    prev.feed_school_ids = [...new Set([...(prev.feed_school_ids || []), ...(r.feed_school_ids || [])])];
    prev.feed_unresolved = [...new Set([...(prev.feed_unresolved || []), ...(r.feed_unresolved || [])])];
    if (!(prev.feed_school_ids || []).length && (r.feed_school_ids || []).length) prev.source_note = r.source_note;
  }
  deduped.push(...byKey.values());
}
// 重复的分组元数据提为维表，事实记录仅保留 group_id，保持与 DataLoaders 契约一致。
const groups = [];
const groupIdByKey = new Map();
const records = deduped.map(({ group, source_url, data_gaps, ...fact }) => {
  const name = group || '';
  const sourceUrl = source_url || '';
  const dataGaps = data_gaps ?? null;
  const key = `${name}\u0000${sourceUrl}\u0000${dataGaps || ''}`;
  let groupId = groupIdByKey.get(key);
  if (groupId === undefined) {
    groupId = groups.length;
    groupIdByKey.set(key, groupId);
    groups.push({ id: groupId, name, source_urls: sourceUrl ? [sourceUrl] : [], data_gaps: dataGaps });
  }
  return { ...fact, group_id: groupId, data_gaps: dataGaps };
});
write('data/primary/xiaoshengchu_2026.json', {
  year: 2026,
  note: '2026 小学→初中升学事实表。学校一律用 school_id 引用（见 entities.json）；feed_school_ids 为对口初中实体 id，feed_unresolved 为 POI 未收录的官方名（显式缺口，不模糊）。district 由 POI join。',
  groups,
  records,
});
console.log(`records: ${records.length} | groups: ${groups.length}`);
console.log(`小学 record 解析 school_id: ${primaryHit}/${records.length}`);
console.log(`feed 初中名 解析: ${feedHit}（未解析 ${feedMiss + 0}）；未解析唯一名: ${new Set(records.flatMap(r=>r.feed_unresolved)).size}`);
console.log('天誉:', JSON.stringify(records.find(r => groups[r.group_id]?.name.includes('亚运城配建'))?.feed_school_ids));
