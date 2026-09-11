// -*- coding: utf-8 -*-
/**
 * 学校注册表构建（范式：POI 点位表 — Entity 实体表 — Fact 事实表 三分离）。
 *
 * 三表职责（无冗余）：
 *   POI 点位表 data/<stage>/schools-gz.json
 *     { name(地图标签), lng, lat, adcode, school_id }   —— 点位固有属性：坐标、所在区
 *   Entity 实体表 data/registry/entities.json
 *     { school_id, name(标准名), stage, aliases[] }      —— 身份：标准名 + 全部叫法
 *   Fact 事实表 data/primary/xiaoshengchu_2026.json
 *     { school_id, group, feed_school_ids[], direct_feed_school_id, source_url, source_note, data_gaps }
 *
 * 粒度：每个 POI（校区/学部）= 一个 Entity，1:1，school_id 即主键。
 *   多校区不是父子实体，而是平级实体；集团/教育集团关系由 brand_groups / education_groups 另表承载。
 *   district 不在 entity 存（由 POI.adcode join 得到）；fact 不存 official_name/district（官方原文在 source_note）。
 *
 * 别名（全等，非模糊）：实体 aliases 收齐该 POI 在官方文件/口碑表中的所有叫法。
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
function idKey(adcode, poiNameNorm) {
  return 'gz-' + adcode + '-' + crypto.createHash('sha1').update(adcode + '|' + poiNameNorm).digest('hex').slice(0, 8);
}
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
// POI 名 → 别名变体：自身 norm 名 + 带区名前缀 + 去区名前缀（官方文件常不带区名，如「石楼中学」对应 POI「番禺区石楼中学」）
const DIST = /^(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区/;
function poiNameAliases(poiName, adcode) {
  const base = normName(poiName);
  const out = [base];
  const dist = AD_DISTRICT[adcode];
  if (dist) {
    if (DIST.test(base)) out.push(base.replace(DIST, ''));        // 去区名
    else out.push(dist + base);                                    // 加区名
  }
  return out;
}
const stageFiles = {
  primary: 'data/primary/schools-gz.json',
  middle: 'data/middle/schools-gz.json',
  high: 'data/high/schools-gz.json',
};

// 官方初中名 → 对应 POI 名（人工核对 2026-09-11，全等别名；存疑/无POI 的不入表）
const OFFICIAL_MIDDLE_ALIAS = {
  '广州市西关外国语学校校本部': '广州市西关外国语学校(初中部)',
  '广州市西关外国语学校彩虹桥校区': '西关外国语学校初中部(彩虹桥校区)',
  '广州市西关外国语学校文昌南校区': '广州市西关外国语学校(初中部)',
  '广州市江南外国语学校': '广州市江南外国语学校(北校区)',
  '广州市海珠区六中珠江中学（万胜围校区）': '海珠区六中珠江中学',
  '广州市海珠区六中珠江中学（逸景校区）': '海珠区六中珠江中学',
  '广州市真光中学初中部芳花校区': '广州市真光中学(芳花校区)',
  '广州市真光中学初中部岭南校区': '广州市真光中学(岭南校区)',
  '中国教育科学研究院荔湾实验学校': '中国教育科学研究院荔湾实验学校·禾园',
  '广东实验中学荔湾学校广钢新城校区': '广东实验中学荔湾学校(初中部)',
  '广东实验中学荔湾学校花地湾校区': '广东实验中学荔湾学校(初中部)',
  '广州市绿翠现代实验学校': '广州市绿翠现代实验学校滨江校区',
  '广州市南武第二实验学校': '广州市南武第二实验学校(南校区)',
  '广州市八一实验学校': '广州市八一实验学校(南校区)',
  '广州市真光学校': '广州市真光学校(长堤校区)',
  '石化中学': '广州石化中学',
  '广州市华侨外国语学校': '广州市华侨外国语学校(华侨新村校区)',
  '广州奥林匹克中学（含智谷校区）': '广州奥林匹克中学(智谷校区)',
  '广东省教育研究院黄埔实验学校': '广东省教育研究院黄埔实验学校初中部',
  '开元学校': '广州开元学校',
  '广州市第一一四中学': '广州市第一一四中学(亭石南路)',
  '广州市白云区景泰中学': '广州市白云区景泰中学白云湖校区',
  '广州市白云区景泰中学分校区（原广州市白云区南悦中学）': '广州市白云区景泰中学白云湖校区',
  '广州市白云区竹料第一中学': '广州市白云区竹料第一中学北校区',
  '广州大同中学': '广州大同中学(初中部)',
  '毓贤学校': '广州番禺区毓贤学校',
  '广州市第一一三中学陶育实验学校': '广州市第一一三中学陶育实验学校(暨南校区)',
  '广州市白云区民航学校': '广州市白云区民航学校(初中部)',
  '广东仲元中学一校区（初中部）': '广东仲元中学',
  '广东仲元中学二校区（初中部）': '广东仲元中学(第二校区)',
  '清华附中湾区学校（智谷校区）': '清华附中湾区学校',
  '华南理工大学附属实验学校（初中部）': '华南理工大学附属实验学校(中学部)',
  '华南师范大学附属黄埔实验学校': '华南师范大学附属黄埔实验学校(南校区)',
  '湖南师范大学附属黄埔实验学校': '湖南师范大学附属黄埔实验学校北校区',
  '广州市白云区白云外国语中学': '广州市白云区白云外国语中小学',
  '广州市华颖外国语学校（广州市华颖中学）': '广州市华颖外国语学校',
  '广州市南国学校': '南国学校(中学部)',
  '暨南大学附属实验学校（初中部）': '暨南大学附属中学',
  '广大附中高新区实验学校': '广大附中高新区实验学校(初中部)',
  '广州市六十五中学（江府校区）': '广州市第六十五中学(江府校区)',
  '广州市第六十五中学（明德校区、同德校区）': '广州市第六十五中学初中部(明德校区)',
  '广州市黄埔军校纪念中学（南校区）': '黄埔军校纪念中学',
  '番广附万博学校': '广州市番禺区番广附万博学校（东校区）',
  '广东第二师范学院实验中学': '广东第二师范学院实验中学(初中部)',
  '广东第二师范学院番禺附属初中': '广东第二师范学院番禺附属初级中学',
};

// 被删点位名（来源叫法）→ stage|base POI 名；点位删除后保留叫法映射到完中实体（防搜索/来源文件失配）
const REMOVED_POI_ALIAS = {
  'middle|南村中学(初中部)': '南村中学',
  'middle|广州市铁一中学白云校区(初中部)': '广州市铁一中学(白云校区)',
  'middle|广东华侨中学起义路校区初中部': '广东华侨中学(起义路校区)',
  'high|广州市南海中学(高中部)': '广州市南海中学',
};

// 官方录取表名（2025/2026 第三、四批及第一批外语艺术类，逐字取招考办原文）→ 项目 POI 名（levels campuses）。
// 桥接「官方招生单位名」与「POI 点位名」，供 scores 事实表按 school_id 引用。
// 仅列 norm 全等无法自动命中的；值为数组表示该官方条目同时挂到多个校区实体（如 2025 按学校整体招生的校区）。
const OFFICIAL_HIGH_ALIAS = {
  // 荔湾
  '广东实验中学（荔湾校区）': '广东实验中学(高中部)',
  '广州市真光中学（校本部）': '广州市真光中学(本部校区)',
  '广州市第四中学': '广州市第四中学(高中部锐园校区)',
  '广州市第一中学': '广州市第一中学(高中部)',
  // 越秀
  '广州市执信中学（执信路校区）': '广州市执信中学(执信路校区)',
  '广州市执信中学（天河校区）': '执信中学(天河校区)',
  '广州市第二中学': '广州市第二中学(应元路校区)',
  '广州大学附属中学': '广州大学附属中学(黄华路校区)',
  '广州市第七中学（校本部）': '广州市第七中学(高中部)',
  '广州市第十六中学（校本部）': '广州市第十六中学',
  '广州市培正中学': '培正中学',
  '广州市育才中学': '广州市育才中学(西校区)',
  '广州市第十三中学': '广州市第十三中学(文德校区)',
  '广东实验中学越秀学校': '广东实验中学越秀学校(天胜校区)',
  '广东华侨中学': ['广东华侨中学(起义路校区)', '广东华侨中学(金沙洲校区)'],
  // 海珠
  '广州市第六中学（海珠校区）': '广州市第六中学',
  '广州市南武中学（校本部）': '广州市南武中学(高中部)',
  '广州市第五中学（校本部）': '广州市第五中学',
  '广州市第九十七中学（校本部）': '广州市第九十七中学',
  '广州市海珠外国语实验中学（校本部）': '广州市海珠外国语实验中学',
  '广州市为明学校': '广州市为明学校罗马校区(高中部)',
  '广州市为明学校（盛景校区）': '广州市为明学校罗马校区(高中部)',
  // 荔湾/其他区
  '广州市西关外国语学校': '广州市西关外国语学校(高中部)',
  '广州市番禺区实验中学': '番禺实验中学',
  '广州市耀华学校': '耀华中学',
  '广州思源学校': '广州思源学校高中部',
  // 天河
  '广州中学': '广州中学(凤凰校区)',
  '广州市天河中学': '广州市天河中学(珠江新城校区)',
  '广州市第七十五中学': '广州市第七十五中学(天平架校区)',
  '广州市第一一三中学': ['广州市第一一三中学(金融城校区)', '广州市第一一三中学(元岗校区)'],
  '清华附中湾区学校': ['清华附中湾区学校（智谷校区）', '清华附中湾区学校（智慧城校区）'],
  '广州奥林匹克中学': ['广州奥林匹克中学(高中部)', '广州奥林匹克中学(智谷校区)'],
  // 白云
  '广州市培英中学（白云新城校区）': '广州市培英中学(云城校区)',
  '广州大同中学': '广州大同中学(高中部)',
  '广州市白云区广东第二师范学院实验中学': '广东第二师范学院实验中学(高中部)',
  '广州市白云区广州空港实验中学': ['广州空港实验中学(校本部)', '广州空港实验中学(东校区)'],
  // 黄埔
  '广州市玉岩中学': '玉岩中学',
  '广州知识城中学': '广州知识城中学(南校区)',
  '广州市明珠高级中学有限公司': '广州市明珠高级中学',
  '北京师范大学广州实验学校': '北京师范大学广州实验学校-中学部',
  // 番禺
  '广州市番禺区祈福英语实验学校（国内班）': '祈福英语实验学校',
  '广州市番禺区祈福英语实验学校（港澳台班）': '祈福英语实验学校',
  '广州市衡美高级中学有限公司': '广州市衡美高级中学',
  // 艺术类（第一批）
  '广州市艺术中学（越秀校区）（美术类）': '广州市艺术中学',
  '广州市艺术中学（越秀校区）（美术）': '广州市艺术中学',
  '广州市艺术中学（黄埔校区）（美术类）': '广州市艺术中学黄埔校区',
  '广州市艺术中学（黄埔校区）（传媒）': '广州市艺术中学黄埔校区',
  '广州市艺术中学（黄埔校区）（美术）': '广州市艺术中学黄埔校区',
  '广州市艺术中学（黄埔校区）（书法）': '广州市艺术中学黄埔校区',
  '广州市艺术中学（黄埔校区）（播音主持）': '广州市艺术中学黄埔校区',
  '广州市艺术中学（黄埔校区）（舞蹈）': '广州市艺术中学黄埔校区',
  '广州市艺术中学（黄埔校区）（音乐）': '广州市艺术中学黄埔校区',
};

// ---- 1) 每个 POI 建一个实体；school_id 即 POI 主键 ----
const entities = [];           // {school_id, name, stage, aliases:Set(norm)}
const poiIdByKey = new Map();   // "stage|poiName" -> school_id
const entByStagePoiName = new Map(); // "stage|norm(poiName)" -> entity

for (const [stage, file] of Object.entries(stageFiles)) {
  const j = read(file);
  const pois = j.schools || j;
  for (const p of pois) {
    const sn = normName(p.name);
    const schoolId = idKey(p.adcode, sn);
    const ent = { school_id: schoolId, name: p.name, stage, aliases: new Set(poiNameAliases(p.name, p.adcode)) };
    entities.push(ent);
    poiIdByKey.set(stage + '|' + p.name, schoolId);
    entByStagePoiName.set(stage + '|' + sn, ent);
  }
}

// ---- 2) 把 tier1 / sites 的别名挂到对应 POI 实体 ----
function attachAlias(stage, poiName, aliasName) {
  const ent = entByStagePoiName.get(stage + '|' + normName(poiName));
  if (!ent) return false;
  for (const v of withDistrictVariants(normName(aliasName))) ent.aliases.add(v);
  return true;
}
// tier1：本部通用名挂到其名下各 POI 实体（school_ids 直接关联；孤儿记录按 aliases 兜底）
for (const [stage, file] of [['primary', 'data/primary/tier1_schools_all.json'], ['middle', 'data/middle/tier1_schools_all.json']]) {
  const j = read(file);
  for (const blk of Object.values(j.districts || {}))
    for (const s of blk.schools || []) {
      const common = normName(s.name); // 官方通用名/本部名
      const attached = new Set();
      for (const sid of (s.school_ids || [])) {
        const ent = entities.find((e) => e.school_id === sid);
        if (!ent) continue;
        for (const v of withDistrictVariants(common)) ent.aliases.add(v);
        attached.add(sid);
      }
      // 孤儿记录：保留的 aliases 仍尝试挂载（防漏）
      if (attached.size === 0) {
        for (const poi of (s.aliases || [])) {
          const ent = entByStagePoiName.get(stage + '|' + normName(poi));
          if (!ent) continue;
          for (const v of withDistrictVariants(common)) ent.aliases.add(v);
        }
      }
    }
}
// sites.json：31 所高中，sites[].poi_name 命中的，挂 sites 别名
const sites = read('data/registry/sites.json');
for (const ent of sites.schools || []) {
  const stage = (ent.stages && ent.stages[0]) || 'high';
  const common = normName(ent.name);
  for (const poi of (ent.sites || [])) {
    const e = entByStagePoiName.get(stage + '|' + normName(poi.poi_name));
    if (!e) continue;
    for (const v of withDistrictVariants(common)) e.aliases.add(v);
    for (const a of (ent.aliases || [])) for (const v of withDistrictVariants(normName(a))) e.aliases.add(v);
  }
}
// 人工核对的官方初中名 → POI 实体
let aliasHit = 0;
for (const [official, poi] of Object.entries(OFFICIAL_MIDDLE_ALIAS)) {
  if (attachAlias('middle', poi, official)) aliasHit++;
  else console.log('  [别名未命中POI]', official, '->', poi);
}
for (const [k, poi] of Object.entries(REMOVED_POI_ALIAS)) {
  const [stage, official] = k.split('|');
  if (attachAlias(stage, poi, official)) aliasHit++;
  else console.log('  [被删点位别名未命中POI]', official, '->', poi);
}
// 官方高中录取表名 → POI 实体（2025/2026 录取分数表逐字原文；值可为数组=挂多个校区）
for (const [official, poi] of Object.entries(OFFICIAL_HIGH_ALIAS)) {
  for (const p of (Array.isArray(poi) ? poi : [poi])) {
    if (attachAlias('high', p, official)) aliasHit++;
    else console.log('  [高中别名未命中POI]', official, '->', p);
  }
}

// ---- 3) 落盘实体（排序、aliases 去重排序）----
for (const e of entities) e.aliases = [...e.aliases].sort((a, b) => b.length - a.length);
entities.sort((a, b) => (a.stage + a.name).localeCompare(a.stage + a.name, 'zh'));
write('data/registry/entities.json', {
  year: 2026,
  note: '学校实体表（维度表）。一个 POI 点位=一个实体（校区/学部独立）；school_id 即主键。事实表用 school_id 引用；district 由 POI.adcode join。集团关系见 brand_groups/education_groups。',
  entities,
});

// ---- 4) 回写 POI school_id ----
for (const [stage, file] of Object.entries(stageFiles)) {
  const j = read(file);
  for (const p of (j.schools || j)) p.school_id = poiIdByKey.get(stage + '|' + p.name) || null;
  write(file, j);
}

// ---- 统计 ----
const noId = { primary: 0, middle: 0, high: 0 };
for (const [stage, file] of Object.entries(stageFiles))
  for (const p of (read(file).schools || read(file))) if (!p.school_id) noId[stage]++;
console.log(`实体数: ${entities.length}（=POI 数，1:1）`);
console.log(`  primary: ${entities.filter(e=>e.stage==='primary').length} | POI未配id: ${noId.primary}`);
console.log(`  middle : ${entities.filter(e=>e.stage==='middle').length} | POI未配id: ${noId.middle}`);
console.log(`  high   : ${entities.filter(e=>e.stage==='high').length} | POI未配id: ${noId.high}`);
console.log(`  人工初中别名挂载: ${aliasHit}/${Object.keys(OFFICIAL_MIDDLE_ALIAS).length}`);
const df = entities.find(e => e.name.includes('东风东路小学(东风广场'));
console.log('  东风东(东风广场) aliases:', df.aliases);
