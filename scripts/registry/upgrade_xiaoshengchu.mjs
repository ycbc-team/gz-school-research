// -*- coding: utf-8 -*-
/**
 * 升学事实表升级：xiaoshengchu_all.json（裸名）→ xiaoshengchu_2026.json（school_id 外键）。
 *
 * 范式：事实表不存学校名，只存 school_id；名字/别名单一存 entities.json。
 *   - 小学 record.name（POI 名）→ primary 实体 school_id
 *   - feed_junior_highs 官方初中名 → middle 实体 school_id（normName 全等别名；未命中=null，即显式缺口，不模糊）
 *   - 跨区同名：用 record.district 精确消歧
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
// 按 stage 建 normAlias -> [entity]
const byStageAlias = { primary: new Map(), middle: new Map(), high: new Map() };
for (const e of entities) {
  for (const a of e.aliases) {
    if (!byStageAlias[e.stage].has(a)) byStageAlias[e.stage].set(a, []);
    byStageAlias[e.stage].get(a).push(e);
  }
}
const AD = {'440103':'荔湾区','440104':'越秀区','440105':'海珠区','440106':'天河区','440111':'白云区','440112':'黄埔区','440113':'番禺区'};
const districtOfGroup = (g) => { if(!g) return null; const m = /(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区/.exec(g); return m ? m[1]+'区' : null; };
function resolve(stage, name, district) {
  const list = byStageAlias[stage].get(normName(name)) || [];
  if (!list.length) return null;
  if (list.length === 1) return list[0].school_id;
  const hit = list.find((e) => e.district === district);
  return (hit || list[0]).school_id; // 消歧不中回退首条（确定性）
}

const src = read('data/primary/xiaoshengchu_all.json');
let feedHit = 0, feedMiss = 0, primaryHit = 0;
const outRecords = src.records.map((r) => {
  const district = districtOfGroup(r.group);
  const primaryId = resolve('primary', r.name, district);
  if (primaryId) primaryHit++;
  const feed = (r.feed_junior_highs || []).map((name) => {
    const sid = resolve('middle', name, district);
    if (sid) feedHit++; else feedMiss++;
    return { official_name: name, school_id: sid };
  });
  return {
    school_id: primaryId,
    district,
    group: r.group,
    feed,
    direct_feed: r.direct_feed ? { official_name: r.direct_feed, school_id: resolve('middle', r.direct_feed, district) } : null,
    source_url: r.source_url, source_note: r.source_note, data_gaps: r.data_gaps,
  };
});
write('data/primary/xiaoshengchu_2026.json', {
  year: 2026,
  note: '2026 小学→初中升学事实表（范式）。学校一律用 school_id 引用，详见 data/registry/entities.json。feed 未解析 school_id 者为官方初中名与初中POI全等未命中（显式缺口，不模糊匹配）。',
  records: outRecords,
});
console.log(`records: ${outRecords.length}`);
console.log(`小学 record 解析到 school_id: ${primaryHit}/${outRecords.length}`);
console.log(`feed 初中名 解析到 school_id: ${feedHit}（未解析 ${feedMiss}，为显式缺口）`);
console.log('天誉:', JSON.stringify(outRecords.find(r=>r.group.includes('亚运城配建'))?.feed));
