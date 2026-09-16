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
  // —— 2026-09-12 第二批人工核对（未命中清单逐条复核：官方名单名 → POI 点位名）——
  // 番禺区（市桥/大石/沙湾/洛浦/石楼等镇街简称差异）
  '广东番禺中学实验学校': '番禺中学实验学校',
  '广州大学附属中学（番禺校区）': '广州大学附属中学(大学城校区)',
  '广州市番禺区剑桥郡加拿达外国语学校': '加拿达外国语学校(剑桥郡校区)',
  '广州市番禺区化龙镇大博学校': '大博学校',
  '广州市番禺区华南碧桂园学校': '华南碧桂园学校(中学部)',
  '广州市番禺区南村镇侨联中学': '南村侨联中学',
  '广州市番禺区博萃德学校': '广州博萃德学校',
  '广州市番禺区大石会江实验学校': '会江实验学校',
  '广州市番禺区大石大山学校': '大山学校',
  '广州市番禺区大石富丽中学': '富丽中学',
  '广州市番禺区市桥东风中学': '东风中学',
  '广州市番禺区市桥侨联中学': '侨联中学',
  '广州市番禺区市桥星海中学': '星海中学',
  '广州市番禺区市桥桥城中学': '桥城中学',
  '广州市番禺区市桥沙头中学': '沙头中学',
  '广州市番禺区市桥象圣中学': '象圣中学',
  '广州市番禺区广铁一中铁英学校': '广州市番禺区广铁一中铁英学校(西校区)',
  '广州市番禺区毓贤学校': '广州番禺区毓贤学校',
  '广州市番禺区沙湾华阳学校': '华阳学校',
  '广州市番禺区沙湾象达中学': '象达中学',
  '广州市番禺区沙湾象骏中学': '象骏中学',
  '广州市番禺区洛浦厦滘学校': '番禺区洛浦厦滘学校中学部',
  '广州市番禺区洛浦沙滘中学': '沙滘中学',
  '广州市番禺区番外外国语学校': '广州番外外国语学校',
  '广州市番禺区祈福新邨学校': '祈福新邨',   // 九年制民办：小学 POI「祈福新邨学校」已独立，初中 POI「祈福新邨」补挂叫法
  '广州市番禺区石楼镇海鸥学校': '海鸥学校',
  '广州市番禺区石楼镇第二中学': '石楼第二中学',
  '广州市番禺区石楼镇莲花山中学': '莲花山中学',
  '广州市番禺区鸿翔学校': '番禺鸿翔学校',
  // 黄埔区
  '广大附中黄埔实验学校': '广大附中黄埔实验学校(东校区)',
  '广州市新侨学校': '广州新侨学校',
  '广州市黄埔东晖学校': '东晖学校',
  '广州市黄埔东联学校': '东联学校',
  '广州市黄埔区中黄外国语实验学校': '中黄外国语实验学校丰巢快递柜',
  // 天河区
  '华南师范大学附属中学（五山校区）': '华南师范大学附属中学初中部',
  '华南理工大学附属实验学校': '华南理工大学附属实验学校(中学部)',
  '广州市天河区同仁天兴学校': '广州市天河同仁天兴学校',
  '广州市天河区明珠中英文学校': '天河明珠中英文学校',
  '广州市天河区大华学校': '广州大华中英文学校',
  '暨南大学附属实验学校': '暨南大学附属中学',
  '广州市第一一三中学': '广州市第一一三中学(乐学校区)',   // 本部=乐学校区（quota入库人工核对；原东方校区为历史误挂）
  // 海珠区
  '广州市九十七中晓园学校': '广州市第九十七中学晓园学校',
  '广州市五中滨江学校': '广州市五中滨江学校(远安校区)',
  '广州市海珠区华洲实验学校': '广州海珠华洲实验学校',
  // 白云区
  '广东华侨中学（白云校区）': '广东华侨中学(金沙洲校区)',
  '广州华联外语实验学校': '广附华联外语实验学校',
  '广州市白云区云雅实验学校': '广州云雅实验学校初中部',
  '广州市白云区六中实验中学（空港校区）': '白云六中实验中学(空港校区)',
  '广州市白云区华赋学校': '广州市白云区华赋学校(北校区)',
  '广州市白云区培英实验学校': '广州市白云区培英实验学校(同和校区)',
  '广州市白云区广大附中实验中学': '广大附中实验中学(星汇金沙校区)',
  '广州市白云区广州培文外国语学校': '广州培文外国语学校初中部',
  '广州市白云区应元颐和实验学校': '应元颐和实验学校初中部',
  '广州市白云区成龙中学': '广州成龙教育集团白云区成龙中学',
  '广州市白云区白云实验学校': '省实白云实验学校',
  '广州市白云区黄石学校': '黄石学校(黄石校区)',
  '广州市白云区龙归学校': '龙归学校（珑璟校区）',
  '广州市白云区东平学校': '东平学校(东平校区)',
  '广州市白云区江高镇第三初级中学': '广州市江高三中',
  '广州市白云区石龙中学': '石龙中学',
  '广州市第六十五中学（明德校区）': '广州市第六十五中学初中部(明德校区)',
  // 越秀区（校区官方叫法 → 越秀路名校区）
  '广东华侨中学（越秀校区）': '广东华侨中学(起义路校区)',
  '广州大学附属中学（越秀校区）': '广州大学附属中学(黄华路校区)',
  '广州大学附属中学': '广州大学附属中学(黄华路校区)',  // 越秀派位裸名→黄华路（完中本部；录取分由 OFFICIAL_HIGH_ALIAS 挂大学城）
  '广州市执信中学（越秀校区）': '广州市执信中学(执信路校区)',
  '广州市第二中学（越秀校区）': '广州市第二中学(应元路校区)',
  // 荔湾区
  '广州市荔湾区博雅中英文学校': '博雅中英文学校(海龙校区)',   // 海中校区不存在，入库=海龙校区（quota人工核对）
  '广州市第四中学': '广州市第四中学(津园校区)',   // 初中配额裸名→初中部津园（四中初中校区；锐园为高中部由 OFFICIAL_HIGH_ALIAS 持有）
  '广州中学': '广州中学(五山校区)',   // 初中配额裸名→初中部五山（凤凰校区为高中部由 OFFICIAL_HIGH_ALIAS 持有）
  '广州市荔湾区博雅实验学校': '荔湾区东沙博雅实验学校',
  '广州市荔湾区新苗学校': '广州荔湾区新苗学校',
  '广州市荔湾区芳华初级中学': '广州市荔湾区芳华中学',
  '广州市荔湾区西关广雅实验学校': '西关广雅实验学校(南岸路校区)',
  // —— 2026-09-14 第三批人工核对（未命中清单逐条复核：官方名单名 → POI 点位名）——
  // 荔湾区（四中校区官方名"初中X园校区"→ POI"X园校区"）
  '广州市第四中学初中逸园校区': '广州市第四中学(逸园校区)',
  '广州市第四中学初中津园校区': '广州市第四中学(津园校区)',
  '广州市第四中学初中雁园校区': '广州市第四中学(虬园校区)',   // 官方招生名"雁园"=地图POI"虬园"（西华路蟠虬南21号，原聚贤虬园校区民转公）
  '广州市荔湾区西关广雅实验学校大坦沙校区': '西关广雅实验学校(大坦沙校区)',
  '广州市荔湾区西关广雅实验学校东风西校区': '西关广雅实验学校(东风西路校区)',
  // 越秀区
  '广州市培正矿泉学校': '广州市培正中学矿泉学校',
  '广州市协和学校': '广州协和学校',
  // 白云区
  '广州市白云区广州空港实验中学（本部）': '广州空港实验中学(校本部)',
  '广州市白云区广州空港实验中学（西校区）': '广州空港实验中学(西校区)',
  '广州市白云区培英实验学校（云景校区）': '培英实验学校(云景校区)初中部',
  '广州市白云区江高镇第二初级中学': '广东技术师范大学白云实验中学',   // 2021年更名，招生文本仍沿用旧名
  // 番禺区
  '番禺区实验中学': '番禺实验中学',
  '广铁一中番禺校区': '广州市铁一中学(番禺校区)',
  '丽江学校': '丽江小学',
};

// 官方初中裸名 → 初中部校区实体（force 绕过纯名先占）：
// 这些学校的官方名（无校区）在实体表里只挂在高中部/完中本部（high）上，初中表按
// 「区+名+学段」匹配时命中 high 或唯一候选跨学段引用，锚不到初中部校区。
// 数据层把裸名挂到初中部校区实体后，初中表 stage 过滤即唯一命中（高中表仍命中 high，
// 跨 stage 共用同一裸名合法——别名非主键）。同区同 stage 仍歧义的（完中本部自身有
// middle 行）不在此表，由 backfill MATCH_OVERRIDES 显式兜底。
const FORCED_MIDDLE_ALIAS = {
  '广州奥林匹克中学': '广州市奥林匹克中学(黄村西路校区)',   // 奥中初中部=黄村西路（高中部由 OFFICIAL_HIGH_ALIAS 持裸名）
  '广州市华美英语实验学校': '广州华美英语实验学校',        // 华美初中（middle）；高中实体 a6394a7a 持官方名
  '广州市天河中学': '广州市天河中学(天河东路校区)',        // 天河中学初中部=天河东路（高中=珠江新城 high）
  '广州市第七十五中学': '广州市第七十五中学(燕塘西校区)',  // 七十五中初中部=燕塘西（高中=天平架 high）
  '广州市天河区华实学校': '广州市天河区华实学校初中部',    // 华实初中部（primary 实体持官方裸名，初中表 stage 过滤后唯一）
  '广州知识城中学': '广州知识城中学(北校区)',              // 初中配额锚北校区（南校区为 high）
  '广州市黄埔区开元学校': '广州开元学校',                  // 开元初中（middle）；高中实体 203c6d64 持官方名
  '广州市黄埔区苏元学校': '广州市黄埔区苏元学校(西校区)',  // 苏元初中=西校区（高中实体 8bf29a28 持官方名）
  '广州市番禺区北正华学校': '番禺区北新正华学校',          // 官方名 vs 实体名（更名后实体未同步旧名）
};

// 被删点位名（来源叫法）→ stage|base POI 名；点位删除后保留叫法映射到完中实体（防搜索/来源文件失配）
const REMOVED_POI_ALIAS = {
  'middle|南村中学(初中部)': '南村中学',
  'middle|广州市铁一中学白云校区(初中部)': '广州市铁一中学(白云校区)',
  'middle|广东华侨中学起义路校区初中部': '广东华侨中学(起义路校区)',
  'high|广州市南海中学(高中部)': '广州市南海中学',
};

// 教育集团成员官方名/旧名 → POI 点位名（P3 覆盖清单 2026-09-14 查证：更名/并入/承继）。
// 与 OFFICIAL_MIDDLE_ALIAS 同机制（全等别名桥接），供匹配器按成员名找回 POI；
// 值可为数组 = 挂多个校区实体（多校区由 merge_groups 锚点表承载，别名侧同时桥接保证匹配器自洽）。
const GROUP_MEMBER_ALIAS = {
  // —— 2024 黄埔集团化整合（南方+ 2024-04-30）：九佛系并入广州知识城中学 ——
  'middle|九佛中学': '广州知识城中学(东校区)',
  'middle|九佛第二中学': '广州知识城中学(南校区)',
  // —— 越秀通称：越秀区「培正小学」= 东山培正小学（法人通称；海印苑校区 POI 名省略「东山」）。
  // 荔湾「西关培正小学」为独立法人，norm 不同不撞车。 ——
  'primary|培正小学': '东山培正小学',
  // —— 白云区更名承继（P3 逐校查证）——
  'primary|广州市白云区凤凰小学': '广州市白云区培英中学附属第三小学',      // 2024-06-19 更名
  'primary|广州市白云区江高镇中心小学': '广东技术师范大学白云实验小学',    // 2021-08-11 更名
  'primary|越秀天悦金沙配建小学': '白云广附金悦实验小学',                 // = 金广附系配建（2024-09 开学）
  'middle|白云湖数字科技城八方物流地块配建学校': '广州市培英中学科技城校区', // = 培英科技城校区（2025-09 开学；多校区由锚点表承载）
  'middle|广州市白云区南悦中学': '广州市白云区景泰中学白云湖校区',          // 更名景泰中学白云湖校区
  // —— 集团成员官方名 → 校区/实体 POI（2026-09-16 锚点表瘦身迁移：单校区锚定全部下沉 entities 别名，产物确定性由测试保证）——
  // 多校区成员（广州中学/新滘/龙口西/天河外/省实荔湾/知识城/培英/六十五中/空港实验/铁铮/八方物流）由锚点表 members 一对多承载，不在此列
  'primary|广州市海珠区瑞宝小学': '海珠区瑞宝小学(北校区)',
  'primary|广州市海珠区晓港湾小学': '晓港湾小学(晓港湾校区)',            // 同区海珠校区已确认（防跨区落黄埔）
  'primary|广州市海珠区新民六街小学': '新民六街小学(北校区)',
  'primary|五山小学': '五山小学(西校区)',
  'primary|华康小学': '华康小学(海欣校区)',
  'primary|广州市真光中学附属小学': '广州市真光中学附属小学(滘口校区)',
  'middle|广州市第四中学丰宁学校': '广州市第四中学丰宁学校',               // 越秀丰宁路（荔湾四中集团托管，跨区真实）
  'middle|广州市西关外国语嘉庚学校': '广州市陈嘉庚纪念中学',
  'primary|广州市西关外国语学校附属流花小学': '广州市流花路小学',
  'primary|广州市西关外国语学校附属西华小学': '西华路小学',
  'primary|广州市荔湾区蒋光鼐纪念小学文昌学校': '广州市荔湾区文昌小学',
  'primary|广州市荔湾区芳村小学实验学校': '芳村小学',
  'primary|广州市荔湾区西关实验小学龙溪学校': '广州市荔湾区龙溪小学',
  'primary|广州市白云区汇侨第一小学': '汇侨第一小学(汇侨校区)',
  'primary|广州市白云区棠溪小学': '白云区棠溪小学(棠溪校区)',
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
  '广州大学附属中学': '广州大学附属中学(大学城校区)',  // 录取分/高中表按学校整体招生 → 大学城（high）
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

// 纯名判定：与 data_quality_test.py [3] 检查口径一致（无校区/学部/括号/“学校”字样的别名才参与纯名先占；
// 「广铁一中铁英学校」含“学校”是共享别名，东/西校区都挂，不参与先占）
function isPlainAlias(s) {
  if (/校区|本部|、|初中部|高中部|小学部|年级|教学|楼|\(|（/.test(s)) return false;
  if (/学校/.test(s.split('（')[0].split('(')[0])) return false;
  return true;
}
// 纯名先占表：区|纯名 → 已持有该纯名的实体 school_id（实体名自身 norm 优先占位；同区跨 stage 也拦截）
const plainOwner = new Map();

// ---- 1) 每个 POI 建一个实体；school_id 即 POI 主键 ----
const entities = [];           // {school_id, name, stage, aliases:Set(norm)}
const poiIdByKey = new Map();   // "stage|adcode|poiName" -> school_id（同名跨区必须独立）
const entByStagePoiName = new Map(); // "stage|norm(poiName)" -> entity

for (const [stage, file] of Object.entries(stageFiles)) {
  const j = read(file);
  const pois = j.schools || j;
  for (const p of pois) {
    const sn = normName(p.name);
    // 幂等：POI 已有 school_id 时保留（历史算法产出，事实表已按此引用），无 id 才新算
    const schoolId = p.school_id || idKey(p.adcode, sn);
    const ent = { school_id: schoolId, name: p.name, stage, aliases: new Set(poiNameAliases(p.name, p.adcode)) };
    // 实体名自身 norm 的纯名变体先占位（「景泰中学」实体名 = 纯名，别名表不得再挂同区其他实体）
    for (const v of poiNameAliases(p.name, p.adcode)) {
      if (isPlainAlias(v)) {
        const key = p.adcode + '|' + v;
        if (!plainOwner.has(key)) plainOwner.set(key, schoolId);
      }
    }
    entities.push(ent);
    poiIdByKey.set(stage + '|' + p.adcode + '|' + p.name, schoolId);
    entByStagePoiName.set(stage + '|' + sn, ent);
  }
}

// ---- 0) 民办学校实体名单（办学性质唯一真源，2026-09-14 统一） ----
// 民办身份统一由此表生产到 entities.json（nature='民办'）；POI 点位表 / tier1 口碑表 /
// levels 高中表 / 2026 招生文件不再各自携带民办标识。
// 名单来源（按 school_id / 名称别名匹配实体并去重，共 62 个）：
//   ① data/primary/enrollments/2026-panyu.json 民办招生计划 sheet（38 个）
//   ② data/high/levels.json nature=民办（19 所，按名称/别名/校区匹配，含同址初高中两实体）
//   ③ data/middle/tier1_schools_all.json 口碑校法人类型=民办非企业单位（8 条，含 3 个补点按别名解析）
// 公办为默认性质，不写字段；新增民办学校时在此追加 school_id。
const MINBAN_IDS = new Set([
  'gz-440103-3ea667b1', 'gz-440103-4935332a', 'gz-440103-4ab42b76', 'gz-440103-5143f5a1', 'gz-440103-6c3ca7d0',
  'gz-440103-815371aa', 'gz-440103-821faa89', 'gz-440103-84d436cd', 'gz-440103-957da59e', 'gz-440103-aa6cf7d7',
  'gz-440103-b2c7aafd', 'gz-440103-b894cbeb', 'gz-440103-c5a0baa6', 'gz-440103-cc2ff923', 'gz-440103-e7a8679d',
  'gz-440103-f5593d98', 'gz-440104-1f2d5df9', 'gz-440104-737bb916', 'gz-440104-cc4aa5b8', 'gz-440104-db01d10e',
  'gz-440105-067354f4', 'gz-440105-0b2bc8c5', 'gz-440105-0b52e48d', 'gz-440105-0bb7bcc4', 'gz-440105-0c78a8e1',
  'gz-440105-12dcb841', 'gz-440105-25137088', 'gz-440105-2e535171', 'gz-440105-33928ddd', 'gz-440105-443b73e7',
  'gz-440105-47f6ec47', 'gz-440105-4d41d915', 'gz-440105-5a8bf708', 'gz-440105-6d9709b2', 'gz-440105-8371ce9c',
  'gz-440105-88e4d95e', 'gz-440105-9a6566db', 'gz-440105-a1ae8780', 'gz-440105-a630438a', 'gz-440105-ae968480',
  'gz-440105-b43b0c72', 'gz-440105-baa048f9', 'gz-440105-d30140a6', 'gz-440105-e038f3fb', 'gz-440105-e778fd4e',
  'gz-440105-f0a0a476', 'gz-440105-f6b48b9e', 'gz-440105-fde335b7', 'gz-440106-01fd3a87', 'gz-440106-02473a1e',
  'gz-440106-0a2c7178', 'gz-440106-0c83a9b2', 'gz-440106-0d03d513', 'gz-440106-118c9e6b', 'gz-440106-11f65b1a',
  'gz-440106-1b9f7e62', 'gz-440106-23e66d3b', 'gz-440106-24ff78f9', 'gz-440106-3d7736c5', 'gz-440106-42297c28',
  'gz-440106-429b917e', 'gz-440106-4534dc1a', 'gz-440106-4775be07', 'gz-440106-4fac106a', 'gz-440106-540006ea',
  'gz-440106-682a616f', 'gz-440106-72c4c319', 'gz-440106-77787b4a', 'gz-440106-7abd2786', 'gz-440106-8d124051',
  'gz-440106-989fdd47', 'gz-440106-9abdc5fd', 'gz-440106-a6394a7a', 'gz-440106-ae248365', 'gz-440106-b52cb528',
  'gz-440106-b9eb24f9', 'gz-440106-bd07878c', 'gz-440106-c77276d3', 'gz-440106-c7779946', 'gz-440106-c8bf2650',
  'gz-440106-cc1c335f', 'gz-440106-e3bbd1e0', 'gz-440106-e7f10219', 'gz-440106-eda909f7', 'gz-440106-f0ba06c2',
  'gz-440106-fd03e039', 'gz-440111-020c5253', 'gz-440111-03ca4bd7', 'gz-440111-03e2f01b', 'gz-440111-0901ed40',
  'gz-440111-0d08ab54', 'gz-440111-0d379efe', 'gz-440111-0fe2a45d', 'gz-440111-11210d19', 'gz-440111-13575da4',
  'gz-440111-148947c8', 'gz-440111-15953ece', 'gz-440111-15a27204', 'gz-440111-17aab34c', 'gz-440111-2018bd49',
  'gz-440111-2667c5ae', 'gz-440111-2abc753d', 'gz-440111-2dbed89a', 'gz-440111-2ec509e7', 'gz-440111-3028b238',
  'gz-440111-32bb2663', 'gz-440111-381929f4', 'gz-440111-39672288', 'gz-440111-3a82b572', 'gz-440111-43281bfc',
  'gz-440111-43437f78', 'gz-440111-43d37a48', 'gz-440111-44cd0b7c', 'gz-440111-4af73d54', 'gz-440111-50cbf803',
  'gz-440111-565db7e9', 'gz-440111-5b14a4f5', 'gz-440111-6782d2c7', 'gz-440111-69cc1cd1', 'gz-440111-6b8ac68f',
  'gz-440111-7137dd14', 'gz-440111-71bacd5a', 'gz-440111-7360ff6d', 'gz-440111-7b531bd6', 'gz-440111-7d12a21e',
  'gz-440111-7e63cbbd', 'gz-440111-81f3c313', 'gz-440111-83b47043', 'gz-440111-87790ad3', 'gz-440111-87a92ab6',
  'gz-440111-88e467ba', 'gz-440111-8ea6750c', 'gz-440111-919c20e3', 'gz-440111-9688546a', 'gz-440111-9bd31440',
  'gz-440111-9f6fc18e', 'gz-440111-a1459fb9', 'gz-440111-a7294ae4', 'gz-440111-aca6656a', 'gz-440111-ad38690f',
  'gz-440111-b3d8d324', 'gz-440111-b4e0e849', 'gz-440111-b5b26ace', 'gz-440111-b694e3ef', 'gz-440111-bcf22267',
  'gz-440111-be9e574f', 'gz-440111-bf9d18d3', 'gz-440111-c03b19f7', 'gz-440111-c0e812a2', 'gz-440111-c1662288',
  'gz-440111-c4a9b707', 'gz-440111-c5445d0e', 'gz-440111-c8ae0a7c', 'gz-440111-c9b1916c', 'gz-440111-cd94e05f',
  'gz-440111-ce7a2db7', 'gz-440111-d3f7ac89', 'gz-440111-dad3339a', 'gz-440111-df409e86', 'gz-440111-e194def0',
  'gz-440111-e85f7f8a', 'gz-440111-ed17a272', 'gz-440111-ed25f5e3', 'gz-440111-f08e9c24', 'gz-440111-f335b626',
  'gz-440111-fd1c0f9d', 'gz-440111-feec64ce', 'gz-440111-ff8918f3', 'gz-440111-ff902ce9', 'gz-440112-202efa5a',
  'gz-440112-2132c84e', 'gz-440112-21d0cd90', 'gz-440112-4517600f', 'gz-440112-4b58e8ec', 'gz-440112-4ed867c7',
  'gz-440112-673fa2c9', 'gz-440112-705844f8', 'gz-440112-93566bfa', 'gz-440112-bffde68d', 'gz-440112-ccdabd8f',
  'gz-440112-e085f4fa', 'gz-440112-fb457bd7', 'gz-440113-000bd12e', 'gz-440113-0670cc0e', 'gz-440113-0b94ed9c',
  'gz-440113-166b5b5c', 'gz-440113-1963cc5e', 'gz-440113-1b3be909', 'gz-440113-23835acf', 'gz-440113-28a853f8',
  'gz-440113-2a299f65', 'gz-440113-2b7d85fc', 'gz-440113-2ca37b61', 'gz-440113-337c0524', 'gz-440113-39879bc6',
  'gz-440113-3b338135', 'gz-440113-3b63e590', 'gz-440113-3cc636b8', 'gz-440113-3d006240', 'gz-440113-611fa8ce',
  'gz-440113-62cbe194', 'gz-440113-6426397c', 'gz-440113-6bf19a4c', 'gz-440113-70ea7542', 'gz-440113-757ae826',
  'gz-440113-7997c707', 'gz-440113-7b27f226', 'gz-440113-7b2b848a', 'gz-440113-827f636b', 'gz-440113-82bf431a',
  'gz-440113-86cfc8c7', 'gz-440113-89b309cd', 'gz-440113-8ef59a4c', 'gz-440113-8efab2cd', 'gz-440113-999fb9c0',
  'gz-440113-a36980e5', 'gz-440113-a45e4a1a', 'gz-440113-a6aa9fb0', 'gz-440113-a6ae517b', 'gz-440113-a93513f2',
  'gz-440113-ad8632f5', 'gz-440113-b33076d3', 'gz-440113-c181d193', 'gz-440113-c40a06e1', 'gz-440113-c5dec315',
  'gz-440113-c9f8740e', 'gz-440113-cf01b95f', 'gz-440113-d4aecd66', 'gz-440113-d7e3e576', 'gz-440113-db326e94',
  'gz-440113-e946f7f3'
]);

// ---- 2) 把 tier1 / sites 的别名挂到对应 POI 实体 ----
function attachAlias(stage, poiName, aliasName, force = false) {
  const ent = entByStagePoiName.get(stage + '|' + normName(poiName))
    // 跨 stage fallback：官方名指向完中实体（如广附黄华路 stage=middle，但官方录取表
    // 按「广州大学附属中学」招生，应把别名挂到该实体，由匹配器按实体全量索引命中）
    ?? [...entByStagePoiName.entries()].find(([k, e]) => k.endsWith('|' + normName(poiName)))?.[1];
  if (!ent) return false;
  for (const v of withDistrictVariants(normName(aliasName))) {
    // 纯名变体先占先得：已被同 stage 同名主校区实体持有则跳过，避免同区纯名被多实体共用
    // （官方主名「广州市白云区景泰中学」的纯名变体「景泰中学」属于主校区实体，不再挂到白云湖校区）
    if (isPlainAlias(v)) {
      const key = ent.school_id.split('-')[1] + '|' + v;
      const owner = plainOwner.get(key);
      if (owner && owner !== ent.school_id) {
        // force=显式人工配置（OFFICIAL_HIGH_ALIAS 官方录取表名等）：绕过纯名拦截。
        // 官方录取分数表用裸名招生（如「广州市第一一三中学」「广州大学附属中学」），
        // 纯名拦截会阻止其挂到 high 实体（如一一三中金融城/元岗两校区、广大附大学城），导致录取分落 unmapped。
        // 显式配置表达"该裸名属于这些实体"的明确意图，不受纯名先占规则约束。
        if (!force) continue;
      }
      plainOwner.set(key, ent.school_id);
    }
    ent.aliases.add(v);
  }
  return true;
}
// tier1：本部通用名挂到其名下各 POI 实体（school_ids 直接关联；孤儿记录按 aliases 兜底）
for (const [stage, file] of [['primary', 'data/primary/tier1_schools_all.json'], ['middle', 'data/middle/tier1_schools_all.json']]) {
  const j = read(file);
  for (const blk of Object.values(j.districts || {}))
    for (const s of blk.schools || []) {
      const common = normName(s.name); // 官方通用名/本部名
      const sids = s.school_ids || [];
      // 多校区纯名通用名（如「京溪小学」4 分校区）：不挂 common，避免同区纯名被多实体共用
      // （匹配器层宁可缺失，多校区由锚点表 members 一对多承载；搜索场景走 tier1 文件直连 school_ids）
      // 与 data_quality [3] 口径一致：含"学校"的共享泛名（如铁英学校合并招生）允许挂多校区
      if (sids.length > 1 && isPlainAlias(common)) continue;
      const attached = new Set();
      for (const sid of sids) {
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
  // 多校区纯名通用名（如「执信中学」→ 执信路/天河/水荫多校区）：不挂 common，避免同区纯名被多实体共用
  // （多校区由锚点表/搜索 sites 列表承载；校区专属别名照挂）
  const isPlainCommon = isPlainAlias(common);
  for (const poi of (ent.sites || [])) {
    const e = entByStagePoiName.get(stage + '|' + normName(poi.poi_name));
    if (!e) continue;
    if (!(ent.sites.length > 1 && isPlainCommon)) {
      for (const v of withDistrictVariants(common)) e.aliases.add(v);
    }
    for (const a of (ent.aliases || [])) for (const v of withDistrictVariants(normName(a))) e.aliases.add(v);
  }
}
// 人工核对的官方初中名 → POI 实体
let aliasHit = 0;
for (const [official, poi] of Object.entries(OFFICIAL_MIDDLE_ALIAS)) {
  if (attachAlias('middle', poi, official)) aliasHit++;
  else console.log('  [别名未命中POI]', official, '->', poi);
}
// 官方初中裸名 → 初中部校区实体（force=true 绕过纯名先占，见 FORCED_MIDDLE_ALIAS 注释）
for (const [official, poi] of Object.entries(FORCED_MIDDLE_ALIAS)) {
  if (attachAlias('middle', poi, official, true)) aliasHit++;
  else console.log('  [强制初中别名未命中POI]', official, '->', poi);
}
for (const [k, poi] of Object.entries(REMOVED_POI_ALIAS)) {
  const [stage, official] = k.split('|');
  if (attachAlias(stage, poi, official)) aliasHit++;
  else console.log('  [被删点位别名未命中POI]', official, '->', poi);
}
// 教育集团成员旧名/官方名 → POI 实体（P3 查证更名承继；值可为数组=挂多校区实体）
for (const [k, poi] of Object.entries(GROUP_MEMBER_ALIAS)) {
  const [stage, official] = k.split('|');
  for (const p of (Array.isArray(poi) ? poi : [poi])) {
    if (attachAlias(stage, p, official)) aliasHit++;
    else console.log('  [集团成员别名未命中POI]', official, '->', p);
  }
}
// 官方高中录取表名 → POI 实体（2025/2026 录取分数表逐字原文；值可为数组=挂多个校区）
// force=true：官方录取裸名（如「广州市第一一三中学」「广州大学附属中学」）显式配置，绕过纯名先占
for (const [official, poi] of Object.entries(OFFICIAL_HIGH_ALIAS)) {
  const list = Array.isArray(poi) ? poi : [poi];
  for (let i = 0; i < list.length; i++) {
    // 数组=官方条目挂多个校区（2025 按学校整体招生）：纯名（裸名）只归首校区，
    // 其余校区仅挂校区限定名，避免同区同 stage 多实体抢同一纯名（检查 [3]）。
    if (i > 0 && isPlainAlias(official)) {
      if (attachAlias('high', list[i], official, false)) aliasHit++;
      else console.log('  [高中别名未命中POI]', official, '->', list[i]);
    } else {
      if (attachAlias('high', list[i], official, true)) aliasHit++;
      else console.log('  [高中别名未命中POI]', official, '->', list[i]);
    }
  }
}

// ---- 3) 落盘实体（排序、aliases 去重排序）----
// 办学性质唯一真源：仅民办写 nature='民办'（公办为默认不写字段），由 MINBAN_IDS 生产
for (const e of entities) if (MINBAN_IDS.has(e.school_id)) e.nature = '民办';
for (const e of entities) e.aliases = [...e.aliases].sort((a, b) => b.length - a.length);
entities.sort((a, b) => (a.stage + a.name).localeCompare(a.stage + a.name, 'zh'));
write('data/registry/entities.json', {
  year: 2026,
  note: '学校实体表（维度表）。一个 POI 点位=一个实体（校区/学部独立）；school_id 即主键。事实表用 school_id 引用；district 由 POI.adcode join。集团关系见 brand_groups/education_groups。nature=民办 为办学性质唯一真源（公办不写字段），由本脚本 MINBAN_IDS 生产。',
  entities,
});

// ---- 4) 回写 POI school_id ----
for (const [stage, file] of Object.entries(stageFiles)) {
  const j = read(file);
  for (const p of (j.schools || j)) p.school_id = poiIdByKey.get(stage + '|' + p.adcode + '|' + p.name) || null;
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
