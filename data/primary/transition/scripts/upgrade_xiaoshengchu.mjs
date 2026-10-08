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
 *   feed_school_ids_by_mechanism  对口/派位初中实体 id 按机制分组（机制→[id]，纯外键；
 *                                 全量列表由消费方并集派生——2026-10-08 字段精简，扁平字段已删）
 *   feed_unresolved_by_mechanism  未解析到 POI 的官方初中名按机制分组（显式缺口，可审计）
 *   direct_feed_school_id 直升初中实体 id
 *   source_url / data_gaps（source_note 仅保留在 parsed 审计层，不带入 dist、不展示前端）
 * district 由 school_id → POI.adcode join 得到，不存。
 *
 * 用法：node scripts/registry/upgrade_xiaoshengchu.mjs [--src <输入 all.json> --out <输出 2026.json>]
 *       （路径为项目根相对或绝对；缺省走正式 dist。快照测试用临时目录，不碰正式产物）
 */
import fs from 'node:fs';
import path from 'node:path';
const ROOT = path.resolve(import.meta.dirname, '..', '..', '..', '..');
const _argv = process.argv.slice(2);
let _src = 'data/primary/transition/dist/xiaoshengchu_all.json';
let _out = 'data/primary/transition/dist/xiaoshengchu_2026.json';
{
  const i = _argv.indexOf('--src');
  if (i >= 0 && i + 1 < _argv.length) _src = _argv[i + 1];
  const j = _argv.indexOf('--out');
  if (j >= 0 && j + 1 < _argv.length) _out = _argv[j + 1];
}
const read = (p) => JSON.parse(fs.readFileSync(path.isAbsolute(p) ? p : path.join(ROOT, p), 'utf8'));
const write = (p, o) => fs.writeFileSync(path.isAbsolute(p) ? p : path.join(ROOT, p), JSON.stringify(o, null, 2) + '\n');

const src = read(_src);
// 机制枚举输出顺序（对齐初中 MECH_ORDER；数据层已固化，这里仅保序去重）
const XS_MECH_ORDER = ['zhi_sheng', 'single_zone', 'group_paidui', 'single_chouqian', 'single_paidui', 'min_zi_zhu'];
let primaryHit = 0, feedHit = 0, feedMiss = 0;
const outRecords = src.records.map((r) => {
  // school_id / feed_school_ids_by_mechanism / direct_feed_school_id 由 Python xs_resolver 解析
  // （见 build_xiaoshengchu_all.py merge_all → scripts/primary/xs_resolver.py）
  if (r.school_id) primaryHit++;
  for (const ids of Object.values(r.feed_school_ids_by_mechanism || {})) feedHit += (ids || []).length;
  for (const names of Object.values(r.feed_unresolved_by_mechanism || {})) feedMiss += (names || []).length;
  return {
    school_id: r.school_id,
    group: r.group,
    mechanisms: r.mechanisms || [],
    direct_feed_school_id: r.direct_feed_school_id,
    source_url: r.source_url, data_gaps: r.data_gaps,
    // 2026-10-08（天河双机制拆分）：feed 按机制分组（机制→[初中 id] / [未解析名]），
    // 由 Python xs_resolver 解析，前端按机制块渲染各自 feed；
    // 2026-10-08（字段精简）：不再输出全量扁平 feed_school_ids/feed_unresolved。
    feed_school_ids_by_mechanism: r.feed_school_ids_by_mechanism || {},
    feed_unresolved_by_mechanism: r.feed_unresolved_by_mechanism || {},
  };
});
// 同 (group, school_id) 去重：同一小学多源名/多条源记录（更名残留、实体合并、源表重复行）
// 解析到同一实体时，feed 并集——产物层单条，避免前端同校重复展示。
// （school_id 为空的历史缺口记录不合并，保持逐条可排查。）
const deduped = [];
{
  const byKey = new Map();
  for (const r of outRecords) {
    if (!r.school_id) { deduped.push(r); continue; }
    const k = `${r.group || ''}\u0000${r.school_id}`;
    const prev = byKey.get(k);
    if (!prev) { byKey.set(k, r); continue; }
    prev.mechanisms = XS_MECH_ORDER.filter((m) => (prev.mechanisms || []).includes(m) || (r.mechanisms || []).includes(m));
    // 机制分组 feed 并集（同机制跨源记录合并；全量列表由消费方并集派生）
    for (const m of Object.keys(r.feed_school_ids_by_mechanism || {})) {
      prev.feed_school_ids_by_mechanism[m] = [...new Set([
        ...(prev.feed_school_ids_by_mechanism[m] || []),
        ...(r.feed_school_ids_by_mechanism[m] || []),
      ])];
    }
    for (const m of Object.keys(r.feed_unresolved_by_mechanism || {})) {
      prev.feed_unresolved_by_mechanism[m] = [...new Set([
        ...(prev.feed_unresolved_by_mechanism[m] || []),
        ...(r.feed_unresolved_by_mechanism[m] || []),
      ])];
    }
  }
  deduped.push(...byKey.values());
}
// 重复的分组元数据提为维表，事实记录仅保留 group_id，保持与 DataLoaders 契约一致。
// 机制（初中枚举）在数据层固化解析，dist group 维表携带，运行时零文本匹配。
const groups = [];
const groupIdByKey = new Map();
const records = deduped.map(({ group, source_url, data_gaps, mechanisms, ...fact }) => {
  const name = group || '';
  const sourceUrl = source_url || '';
  const dataGaps = data_gaps ?? null;
  const key = `${name}\u0000${sourceUrl}\u0000${dataGaps || ''}`;
  let groupId = groupIdByKey.get(key);
  if (groupId === undefined) {
    groupId = groups.length;
    groupIdByKey.set(key, groupId);
    groups.push({ id: groupId, name, source_urls: sourceUrl ? [sourceUrl] : [], data_gaps: dataGaps, mechanism: [...(mechanisms || [])] });
  } else {
    const g = groups[groupId];
    g.mechanism = [...new Set([...(g.mechanism || []), ...(mechanisms || [])])];
  }
  // 记录级机制（初中反推/官方解析）保留在事实记录——组级并集会混入同组不同小学的机制，记录级才精确
  return { ...fact, mechanism: mechanisms || [], group_id: groupId, data_gaps: dataGaps };
});
// 机制顺序统一对齐初中 MECH_ORDER
for (const g of groups) g.mechanism = XS_MECH_ORDER.filter((m) => (g.mechanism || []).includes(m));
write(_out, {
  year: 2026,
  note: '2026 小学→初中升学事实表。学校一律用 school_id 引用（见 entities.json）；feed_school_ids_by_mechanism 为对口初中实体 id 按机制分组（全量列表由消费方并集派生），feed_unresolved_by_mechanism 为 POI 未收录的官方名（显式缺口，不模糊）。district 由 POI join。',
  groups,
  records,
});
console.log(`records: ${records.length} | groups: ${groups.length}`);
console.log(`小学 record 解析 school_id: ${primaryHit}/${records.length}`);
console.log(`feed 初中名 解析: ${feedHit}（未解析 ${feedMiss}）；未解析唯一名: ${new Set(records.flatMap((r) => Object.values(r.feed_unresolved_by_mechanism || {}).flat())).size}`);
