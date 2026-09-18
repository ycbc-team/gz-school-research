// -*- coding: utf-8 -*-
/**
 * 升学事实表组装：xiaoshengchu_all.json（school_id 已由 Python 数据层 xs_resolver.py 解析）
 * → xiaoshengchu_2026.json（去重 + 分组维表）。
 *
 * 名字→school_id 的匹配已全部下沉到数据层（scripts/primary/xs_resolver.py，Python）：
 * 本脚本只做确定性组装（同 group+school_id 去重合并 feed、分组元数据提为维表），
 * 不再做任何名字匹配——运行时只依赖 school_id。
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

const src = read('data/primary/xiaoshengchu_all.json');
let primaryHit = 0, feedHit = 0, feedMiss = 0;
const outRecords = src.records.map((r) => {
  // school_id/feed_school_ids/direct_feed_school_id 由 Python xs_resolver 解析
  // （见 build_xiaoshengchu_all.py merge_all → scripts/primary/xs_resolver.py）
  if (r.school_id) primaryHit++;
  feedHit += (r.feed_school_ids || []).length;
  feedMiss += (r.feed_unresolved || []).length;
  return {
    school_id: r.school_id,
    group: r.group,
    feed_school_ids: r.feed_school_ids || [],
    feed_unresolved: r.feed_unresolved || [],
    direct_feed_school_id: r.direct_feed_school_id,
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
console.log(`feed 初中名 解析: ${feedHit}（未解析 ${feedMiss}）；未解析唯一名: ${new Set(records.flatMap(r=>r.feed_unresolved)).size}`);
