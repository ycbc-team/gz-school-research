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
// --out-dir <dir>：产物重定向到指定目录（check_groups_drift 产物一致性重跑用，不污染工作区）
let OUT_ROOT = ROOT;
const _arg = process.argv.indexOf('--out-dir');
if (_arg >= 0 && process.argv[_arg + 1]) OUT_ROOT = path.resolve(process.argv[_arg + 1]);
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const write = (p, obj) => {
  const fp = path.join(OUT_ROOT, p);
  fs.mkdirSync(path.dirname(fp), { recursive: true });
  fs.writeFileSync(fp, JSON.stringify(obj, null, 2) + '\n');
};

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
  const out = [];
  const dist = AD_DISTRICT[adcode];
  if (dist) {
    if (DIST.test(base)) out.push(base.replace(DIST, ''));        // 去区名
    else out.push(dist + base);                                    // 加区名
  }
  // 自身 norm（== name）不入 aliases：索引侧（upgrade aliasIndex / SchoolMatcher /
  // 前端 registry 等）均已 name+aliases 双索引，自身名冗余只会增大实体表体积
  // （entities.json 会打进小程序包）。区名变体才是真实别名，保留。
  return out;
}
const stageFiles = {
  primary: 'data/primary/schools-gz.json',
  middle: 'data/middle/schools-gz.json',
  high: 'data/high/schools-gz.json',
};

// 纯高中校区（初中不办学）：middle 表不得保留（业务事实，人工/官方核对后固化）。
// 例：广州市第十六中学(水荫校区)——原恒福中学高中部并入 16 中，只有高中；
// 越秀区初中招生（法人「广州市第十六中学」）只覆盖东湖/本部。这类校区若留在
// middle 表，会生成多余 middle 实体并污染孤儿判定（「无招生」实为「该学段不办学」）。
// 命中 → 不建 middle 实体，并从中表 POI 表中删除；high 表不受影响。
const NON_MIDDLE_CAMPUS = [
  '广州市第十六中学(水荫校区)',  // 2026-09-17 用户+官方确认：原恒福中学高中部，纯高中
  // —— 2026-09-17 联网核实（outputs/campus_middle_webverify_20260917.md），
  //    完中同 id 有 high 的校区：删 middle 留 high ——
  '广州市真光中学(本部校区)',    // 培真路17号=高中本部；初中部本部在鹤洞路98号（另一 POI）
  '广州市真光中学(广钢校区)',    // 崇文五路 2025 新办纯高中
  '广州市真光中学(汾水校区)',    // 芬芳街47号 纯高中（独立招生代码）
  '广州市第六十五中学(江高校区)',// 2024/2026 初中 plan 无此行，仅高中名额分配；江高片初中由江府承接
  '广州市培英中学(云城校区)',    // 官方「培英白云新城校区」公办普通高中 48 班
  '广州市第七中学(麓湖校区)',    // 2026-08-31 揭牌「优质公办高中新阵地」首年高一 540 人；初中在本部东山
  '广州中学(凤凰校区)',          // 官方：凤凰全部为高中
  '广州市第一一三中学(金融城校区)', // 高中部；2026 市招考办以金融城校区招高中 430 人
  '广州市第一一三中学(元岗校区)', // 2026-09 启用面向高中阶段招 500 人
  '广州市天河中学(珠江新城校区)', // 官方表：珠江新城=高中部（华成路7号）
  '华南师范大学附属中学(石牌校区)', // 石牌=纯高中（自招简章面向中考应届生）；初中部在五山校区
  '广州市第五中学(金碧校区)',    // 金恒路66号 2022 秋起只招高一；2026 初中表五中仅列本部南村路32号
];
const isNonMiddleCampus = (stage, name) => stage === 'middle' && NON_MIDDLE_CAMPUS.some((s) => name === s);

// 冗余实体剔除（跨 stage / 同 stage 同址冗余）：高德查询到的重复/冗余点位，实体表有主实体即可。
// 89中(北区) gz-440106-f94ad54a：2026-09-17 用户确认「北区」仅为配套扩建、无独立办学，
// 有 89中(8f55ab34) 实体即够——不建实体后 POI 自动按「无 id 假学校」清出点位表。
// 2026-09-17 第二批（同 stage 同址冗余，见 data_quality_test [12]）：
//  - 省实荔湾(初中部一期) gz-440103-1d99218d：与初中部 gz-440103-53cac770 同址北文街2号
//    （官方「广钢新城校区」），初中部一期并入初中部（别名经 OFFICIAL_MIDDLE_ALIAS 挂到 53cac770）
//  - 十三中初中部 gz-440104-2213d9b3：= 禺山校区 gz-440104-9b88f912（禺山路14号），并入
//  - 景泰小学柯子岭校区43号A座 gz-440111-8d42bf12：与柯子岭校区 29m 同址，非学校/重复点位，
//    类似停车场等非学校 POI 剔除（用户口径：43号A座是同一 POI 的重复记录）
const DROP_CAMPUS = [
  '广州市第八十九中学(北区)',
  '广东实验中学荔湾学校(初中部一期)',
  '广州市第十三中学初中部',
  '景泰小学柯子岭校区43号A座',
  '陶育路小学',  // 旧名（更名承继）：现为 广州市第一一三中学陶育实验学校小学部（REMOVED_POI_ALIAS 挂旧名别名）
  '君诚博雅实验学校',  // 法人名冗余：官方只有山村/滘口两校区（2021-2026 荔湾民办一览表），无后缀 POI 0m 同址滘口校区（gz-440103-b2c7aafd），小学/初中侧由滘口校区实体承载
  '广州市君诚博雅实验学校(广佛新城校区)',  // 高德误名：官方无此校区，地址=滘口村377（官方滘口校区地址）→ 并入滘口校区（gz-440103-3ea667b1）
];
const isDropCampus = (name) => DROP_CAMPUS.includes(name);

// POI 坐标修正（school_id → 正确坐标）：高德采集个别 POI 坐标错挂（如省实荔湾花地湾校区
// 被定位到初中部北文街2号）。官方地址见 data/linkage/official_rosters/liwan_gongban_cz_2025.json
// （花地湾校区=花地大道北320号）。本表在实体构建回写 POI 表时应用（幂等：fetch 重跑后再建即恢复）。
const POI_COORD_FIX = {
  'gz-440103-ff7538dc': { lng: 113.232802, lat: 23.085100 },  // 省实荔湾花地湾校区：花地大道北320号（高德花地湾校区公交站点位）
  'gz-440103-6b0e7dbd': { lng: 113.232802, lat: 23.085100 },  // 花地湾校区（小学部）同址
};

// 校区学段修正（school_id → 正确 stage）：middle 表误建、实际为高中/小学的校区实体。
// 与 NON_MIDDLE_CAMPUS 的区别：NON_MIDDLE 是「同 id 有 high」删 middle 留 high；
// 本表是「实体只有 middle stage」——删除即丢失学校，须改为正确学段实体（POI 记录迁至对应表）。
// 依据：outputs/campus_middle_webverify_20260917.md 联网核实。
const CAMPUS_STAGE_FIX = {
  'gz-440111-15fa03a9': 'high',    // 白云中学(南区) 藤业一路366号=官方高中部（金沙洲）
  'gz-440111-5849b586': 'high',    // 白云中学(北区) 藤业一路365号=高中部校园北半
  'gz-440111-3405d87e': 'primary', // 省实(云城校区) 萧岗明珠北路45号=小学部（官网）；初中在白云校区
  'gz-440104-089a2a5b': 'high',    // 省实越秀(盘福校区)=高中（高三）部；初中招生仅列天胜校区
  'gz-440104-63c59c98': 'high',    // 执信(二沙岛国际校区)=高中国际合作办学（AP/A-Level）
  'gz-440112-b56cfdce': 'high',    // 二中(科学城校区) 水西路11号=高中部；初中在应元路21号
  'gz-440106-5b430017': 'high',    // 75中(燕塘东校区) 燕岭路151号=高中部（官方表）
  'gz-440105-13585057': 'high',    // 41中(南校区) 2026 初中已集中校本部，东/南转高中
  'gz-440105-b210556b': 'high',    // 41中(东校区) 2024-12 官方扩建(1.4亿)转高中部
  'gz-440104-0a17f1eb': 'high',    // 十三中(文德校区) 文德路83号=高中/北校；初中部在禺山校区
                                    // （禺山路14号，9b88f912）——历史 OFFICIAL_ALIAS 曾将官方
                                    // 「广州市第十三中学」初中行桥接到本校区（错误），此处修正防再建 middle
};
const stageFixOf = (stage, p) => (stage === 'middle' && CAMPUS_STAGE_FIX[p.school_id]) || stage;

// 非学校 POI 剔除（命中即不建实体，POI 点位表原样保留）。
// 复用项目既有词表：build_high_levels_js.JUNK（楼栋/设施）、school_match._NON_SCHOOL、
// backfill_xiaoshengchu_missing 非学校词。注意：地名/校区名含「楼」（石楼镇/九楼校区/新楼村）
// 与附属中小学名含「大学/学院」（广州大学附属中学等）不可泛杀，故「楼」用精确词、
// 高校本体用前缀精确匹配。命中数有测试固化（脏实体清单漂移防线）。
const NON_SCHOOL_POI = [
  /停车场/, /充电站/, /便利店/, /咏春/, /外籍人员子女/,
  /后门/, /宿舍/, /游泳馆/, /文体楼/, /号楼$/, /总站/,
  /地铁/, /公交/, /路口/, /门卫室/, /正门/, /招生办/, /招生处/, /创意园/,
  /高三教学区/, /商务中心/, /发展中心/, /12栋/, /南教学楼/,
  /雅政楼$/, /行雅楼$/, /卓凡楼$/, /仁爱楼$/, /尚学搂$/,
  /思博教育/,  // 天河同仁学校-思博教育：高德把培训机构（思博教育咨询）混入校名，非学校实体
  /^广州中医药大学/, // 高校本体（三元里校区）；附属中小学以「附属」开头不受影响
];
const isNonSchoolPoi = (name) => NON_SCHOOL_POI.some((re) => re.test(String(name || '')));

// 官方初中名 → 对应 POI 名（人工核对 2026-09-11，全等别名；存疑/无POI 的不入表）
const OFFICIAL_MIDDLE_ALIAS = {
  '广州市西关外国语学校校本部': '广州市西关外国语学校(初中部)',
  '广州市西关外国语学校彩虹桥校区': '西关外国语学校初中部(彩虹桥校区)',
  '广州市西关外国语学校文昌南校区': '广州市西关外国语学校(初中部)',
  '广州市第一中学中宏校区': '广州市第一中学(姜中宏校区)',  // 2026-09-17 荔湾公办初中名录：中宏=姜中宏(蓬莱路3-5号)
  '广州市江南外国语学校': '广州市江南外国语学校(北校区)',
  '广州市海珠区六中珠江中学（万胜围校区）': '海珠区六中珠江中学',
  '广州市海珠区六中珠江中学（逸景校区）': '海珠区六中珠江中学',
  '广州市真光中学初中部芳花校区': '广州市真光中学(芳花校区)',
  '广州市真光中学初中部岭南校区': '广州市真光中学(岭南校区)',
  '中国教育科学研究院荔湾实验学校': '中国教育科学研究院荔湾实验学校·禾园',
  '广东实验中学荔湾学校广钢新城校区': '广东实验中学荔湾学校(初中部)',  // 2026-09-17 核实：一期=广钢新城校区(北文街2号)，初中部一期并入初中部
  '广东实验中学荔湾学校初中部一期': '广东实验中学荔湾学校(初中部)',    // 初中部一期=广钢新城校区=初中部（同址北文街2号）
  // 花地湾校区是独立校区（花地大道北320号，ff7538dc），不再 alias 到初中部——官方名由
  // poiNameAliases 命中花地湾实体自身；此处删掉历史错误挂接（曾致初中部别名含花地湾）
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
  '广州市第十三中学初中部': '广州市第十三中学(禺山校区)',  // 2026-09-17：初中部=禺山校区（禺山路14号），初中部实体并入禺山校区
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
  '广州市第四中学初中雁园校区': '广州市第四中学(虬园校区)',  // 2025名录雁园(蟠虬南21号)=2021百科虬园，同一校区
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
  'primary|陶育路小学': '广州市第一一三中学陶育实验学校小学部',  // 旧名→更名承继（2026-09-17 用户确认）
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

// 官方小学名（2026 小升初划片表原文）→ POI 实体（多校区挂多个实体）。
// 与 FORCED_MIDDLE_ALIAS 同机制（force=true 显式配置，绕过纯名先占）：
// 官方划片表按小学法人名（裸名）公布，同区多校区共享官方名是业务事实（如「华阳小学」4 校区），
// 检查 [3] 已按 OFFICIAL_PRIMARY_ALIAS 共享裸名集合豁免；build_xiaoshengchu_all 由实体表别名解析，不再自建映射。
const OFFICIAL_PRIMARY_ALIAS = {
  "前进小学": "前进小学",
  "车陂小学": "车陂小学",
  "东圃小学": "东圃小学",
  "羊城花园小学": "羊城花园小学",
  "盈彩美居小学": "盈彩美居小学",
  "华康小学": ["广州市天河区华康小学(华文校区)", "华康小学(海欣校区)"],
  "华阳小学": ["华阳小学(天河东校区)", "华阳小学(林和东校区)", "华阳小学(华成校区)", "广州市天河区华阳小学(天润校区)"],
  "龙口西小学": ["龙口西小学(龙口校区)", "龙口西小学(瑞安校区)", "广州市天河区龙口西小学(帝景校区)", "龙口西小学(穗园校区)", "龙口西小学(天阳校区)"],
  "长征小学": "暨南大学华文学院-长征小学",
  "华南师范大学附属小学": "华南师范大学附属小学",
  "华景小学": ["华景小学(北校区)", "华景小学(南校区)"],
  "天府路小学": ["天府路小学", "广州市天河区天府路小学建业校区", "天府路小学翠湖校区"],
  "员村小学": ["员村小学", "员村小学(美林分校)"],
  "石东小学": "天河区石东小学",
  "昌乐小学": ["广州市天河区昌乐小学", "昌乐小学(旭日校区)"],
  "华融小学": "广州市天河区华融小学",
  "五山小学": ["五山小学(西校区)", "天河区五山小学(东校区)"],
  "五一小学": ["五一小学", "五一小学红英校区"],
  "华南农业大学附属小学": "华南农业大学附属小学",
  "汇景实验学校（小学部）": "汇景实验学校（小学部）",
  "先烈东小学": "广州市天河区先烈东小学(沙河校区)",
  "沙河小学": "沙河小学",
  "银河小学": ["银河小学", "银河小学(橡树园校区)"],
  "四海小学": "广州市天河区四海小学",
  "侨乐小学": ["天河区侨乐小学", "广州华阳集团侨乐小学(北校区)"],
  "渔沙坦小学": "渔沙坦小学",
  "龙洞小学": ["龙洞小学", "龙洞小学(宝翠园校区)", "龙洞小学世纪绿洲校区"],
  "高塘石小学": "广州市天河区华阳教育集团高塘石小学",
  "柯木塱小学": "广州市天河区柯木塱小学",
  "广东生态工程职业学院附属小学": "广东生态工程职业学院附属小学",
  "黄村小学": "广州市天河区黄村小学",
  "珠村小学": "珠村小学",
  "吉山小学": "吉山小学",
  "新元小学": "天河区新元小学",
  "中海康城小学": "中海康城小学",
  "旭景小学": "旭景小学",
  "灵秀小学": "灵秀小学",
  "奥体东小学": "奥体东小学",
  "体育东教育集团均和小学": "均和小学",
  "体育东路小学": "体育东路小学",
  "体育东路小学兴国学校": "体育东路小学兴国学校",
  "体育东路小学海明学校": "体育东路小学海明学校",
  "冼村小学": "冼村小学",
  "天河第一实验小学": "广州市天河区第一实验小学",
  "石牌小学": "石牌小学",
  "天河第一小学": ["广州市天河第一小学(华穗校区)", "天河第一小学(华利校区)"],
  "龙岗路小学": "龙岗路小学",
  "体育西路小学": ["体育西路小学(东校区)", "体育西路小学(西校区)"],
  "元岗小学": ["广州市天河区元岗小学(东校区)", "元岗小学(西校区)"],
  "长湴小学": "长湴小学",
  "岑村小学": "广州市天河区岑村小学",
  "长兴小学": "长兴小学",
  "御景小学": "御景小学",
  "志远小学": "志远小学",
  "棠下小学": "棠下小学",
  "骏景小学": "骏景小学",
  "棠德南小学": ["广州市天河区棠德南小学(北校区)", "棠德南小学南校区"],
  "泰安小学": "广州市天河区泰安小学",
  "棠东小学": "棠东小学",
  "新塘小学": "新塘小学",
  "沐陂小学": "沐陂小学",
  "凌塘小学": "天河区凌塘小学",
  "华颖外国语学校（小学部）": "广州市华颖外国语学校",
  "南国学校（小学部）": "南国学校(小学部)",
  "天河中学猎德实验学校（小学部）": "广州市天河中学猎德实验学校",
  "一一三中学陶育实验学校（小学部）": "广州市第一一三中学陶育实验学校小学部",
  "天英小学": "广州市天河区天英小学",
  "天河智慧城第一小学": "天河智慧城第一小学",
  "智谷第一实验学校（小学部）": "天河区智谷第一实验学校",
  "广州奥林匹克中学（智谷校区）小学部": "广州奥林匹克中学（智谷校区）小学部",
  "广东实验中学天河学校（小学部）": "广东实验中学天河学校",
  "天河外国语智谷学校（小学部）": "广州市天河外国语智谷学校",
  "广州中学天河燕园学校（小学部）": "广州中学天河燕园学校",
  "清华附中湾区学校（小学部）": ["清华附中湾区学校", "清华附中湾区学校（智慧城校区）"],
  "华南理工大学附属实验学校（小学部）": ["华南理工大学附属实验学校(小学部)", "华工附小"],
  "暨南大学附属实验学校（小学部）": "暨南大学附属小学",
  // ---- 番禺民办计划表官方名 → 实体（build_minban_official 精确 norm 用；原 SPECIAL 关键词映射下沉）----
  // 官方名作为别名挂实体：命中 school_id 即标民办；多校区实体（小学部/中学部同 id 或同官方名）全部带出。
  "金星小学": "金星学校",
  "同心小学": "番禺同心小学",
  "名智小学": "番禺名智小学",
  "南村华立小学": "华立学校",
  "剑桥郡加拿达学校": "加拿达外国语学校(剑桥郡校区)",
  "洛浦厦滘学校": "厦滘学校(小学部)",
  "博萃德学校": "广州博萃德学校小学部",
  "广州市星执学校": "执信中学附属小学",  // 星执附小（民办）；999fb9c0 name 已为官方名
  "化龙镇大博学校": "化龙大博学校(小学部)",
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

// POI 名规范化（仅实体层，不改源 POI 名）：同 school_id 跨 stage 实体名括号写法不一致
// （如「广州市第十三中学文德校区」middle 无括号 / high 带括号），会致 backfill 法人聚合
// core 失配、该校区无升学仍孤儿。此处统一为规范写法（实体名=括号版，school_id 幂等保留）。
const POI_NAME_FIX = { '广州市第十三中学文德校区': '广州市第十三中学(文德校区)' };

// 核心裸名归一：去括号、去「广州市」前缀；「广州奥林匹克中学」vs「广州市奥林匹克中学」这类
// 「广州」/「广州市」混写也归一到同一核心（防计数/挂载分歧）。仅当去「广州」后剩余为泛词
// （如「广州中学」→「中学」）时保留前缀，避免泛词毁名（历史多次踩坑）。
const BARE_GENERIC = new Set(['中学', '小学', '学校', '幼儿园', '实验中学', '实验学校', '中心小学', '第一小学', '实验小学', '附属小学', '附属中学']);
const BARE_DISTRICT = /^(荔湾|越秀|海珠|天河|白云|黄埔|番禺)区/;
function bareCoreOf(rawNorm) {
  let bc = rawNorm.replace(/\([^()]*\)/g, '').replace(/^广州市/, '').replace(BARE_DISTRICT, '');
  if (bc.startsWith('广州') && !BARE_GENERIC.has(bc.slice(2))) bc = bc.slice(2);
  return bc;
}

// 先统计「同区同学段核心裸名」出现次数：只有独苗才挂裸名别名
// （多校区/多学部同区同段共用一个核心名 → resolve 无法收敛，宁缺毋滥，由锚定表/显式映射兜底）。
const bareCoreCount = new Map();  // "stage|adcode|bareCore" -> count
for (const [stage, file] of Object.entries(stageFiles)) {
  const j = read(file);
  const pois = j.schools || j;
  for (const p of pois) {
    if (isNonSchoolPoi(p.name) || isNonMiddleCampus(stage, p.name) || isDropCampus(p.name)) continue;
    const _st = stageFixOf(stage, p);  // 学段修正：middle 误建 → 按正确 stage 统计
    const pn0 = POI_NAME_FIX[p.name] || p.name;  // 规范化实体名（统计与建实体口径一致）
    const rawNorm = String(pn0).replace(/（/g, '(').replace(/）/g, ')').replace(/\s+/g, '');
    const bareCore = bareCoreOf(rawNorm);
    if (bareCore) {
      const k = _st + '|' + p.adcode + '|' + bareCore;
      bareCoreCount.set(k, (bareCoreCount.get(k) || 0) + 1);
    }
  }
}

const seenSchoolIdByStage = new Set();  // "stage|school_id" 已建实体（同 id 多 POI 点位去重）
for (const [stage, file] of Object.entries(stageFiles)) {
  const j = read(file);
  const pois = j.schools || j;
  for (const p of pois) {
    if (isNonSchoolPoi(p.name) || isNonMiddleCampus(stage, p.name) || isDropCampus(p.name)) continue;
    const pn = POI_NAME_FIX[p.name] || p.name;  // 规范化实体名（POI 原名仅用于 idKey/回写查表）
    const _st = stageFixOf(stage, p);  // 学段修正：middle 误建 → 按正确 stage 建实体（POI 数据随迁）
    const sn = normName(pn);
    // 幂等：POI 已有 school_id 时保留（历史算法产出，事实表已按此引用），无 id 才新算
    const schoolId = p.school_id || idKey(_st, sn);
    // 同 id 去重：POI 表可能对同一 school_id 存在多条点位（如「广州市第十三中学文德校区」与
    // 「广州市第十三中学(文德校区)」两个高德 POI）——同 (stage, school_id) 只建一个实体，
    // 后续点位 aliases 并入首个（否则实体表同 id 双实体、by_id 反查被覆盖导致聚合失配）
    const _dupKey = _st + '|' + schoolId;
    if (seenSchoolIdByStage.has(_dupKey)) {
      const _existing = entities.find((e) => e.stage === _st && e.school_id === schoolId);
      if (_existing) for (const v of poiNameAliases(pn, p.adcode)) _existing.aliases.add(v);
      continue;
    }
    seenSchoolIdByStage.add(_dupKey);
    const ent = { school_id: schoolId, name: pn, stage: _st, aliases: new Set(poiNameAliases(pn, p.adcode)) };
    // 学部/校区括号 → 核心裸名别名（如「广东番禺中学实验学校(小学部)」→「广东番禺中学实验学校」）。
    // 仅当同区同学段该核心名为独苗时挂载（如小学部唯一实体），保证 resolve「区+学段」可唯一收敛；
    // 多校区共用核心名（万松园小学松园/云桂校区）不挂裸名 → resolve 宁缺毋滥，build 靠 _anchors 锚定。
    const rawNorm = String(pn).replace(/（/g, '(').replace(/）/g, ')').replace(/\s+/g, '');
    const bareCore = bareCoreOf(rawNorm);
    if (bareCore && bareCore !== sn && bareCoreCount.get(_st + '|' + p.adcode + '|' + bareCore) === 1) {
      ent.aliases.add(bareCore);
    }
    // 实体名自身 norm 的纯名变体先占位（「景泰中学」实体名 = 纯名，别名表不得再挂同区其他实体）
    for (const v of poiNameAliases(pn, p.adcode)) {
      if (isPlainAlias(v)) {
        const key = p.adcode + '|' + v;
        if (!plainOwner.has(key)) plainOwner.set(key, schoolId);
      }
    }
    entities.push(ent);
    poiIdByKey.set(_st + '|' + p.adcode + '|' + p.name, schoolId);
    entByStagePoiName.set(_st + '|' + sn, ent);
  }
}

// ---- 1.4) 九年制校区派生 middle ----
// 官方九年制校区高德只有 primary POI（未单采初中 POI），但初中侧数据（配额/排位/录取）
// 需要 middle 实体承载（school_id 主键，primary+middle 双 stage 副本，初中消费方按 id 查实体）。
// 依据：荔湾区政府 2021-2026 民办一览表（君诚博雅山村/滘口校区均九年制；山村 POI 缺失宁缺，
// 不派生——无 primary POI 兜底坐标，宁可缺失不造点位）。
const DERIVE_MIDDLE_FROM_PRIMARY = {
  'gz-440103-3ea667b1': { poiName: '君诚博雅实验学校(滘口校区)', adcode: '440103' },
};
for (const [sid, cfg] of Object.entries(DERIVE_MIDDLE_FROM_PRIMARY)) {
  const pri = entities.find((e) => e.stage === 'primary' && e.school_id === sid);
  if (!pri) {
    console.log('  [派生middle未找到primary]', sid);
    continue;
  }
  const priPoi = (read(stageFiles.primary).schools || []).find((x) => x.school_id === sid);
  const m = { school_id: sid, name: cfg.poiName, stage: 'middle', aliases: new Set(pri.aliases) };
  // 法人名双变体（官方民办名单名「广州市荔湾区君诚博雅实验学校」：含区名/裸名两形，
  // backfill_school_ids 的 norm 去「广州市」后按「荔湾区君诚博雅实验学校」命中）
  for (const v of ['荔湾区君诚博雅实验学校', '君诚博雅实验学校']) {
    pri.aliases.add(v);
    m.aliases.add(v);
  }
  entities.push(m);
  poiIdByKey.set('middle|' + cfg.adcode + '|' + cfg.poiName, sid);
  entByStagePoiName.set('middle|' + normName(cfg.poiName), m);
  // 同步注入 middle POI 表（实体=POI 1:1；坐标沿用 primary，回写段按 poiIdByKey 配 school_id）
  const _mj = read(stageFiles.middle);
  if (priPoi && !_mj.schools.some((x) => x.name === cfg.poiName)) {
    _mj.schools.push({ name: cfg.poiName, adcode: cfg.adcode, lng: priPoi.lng, lat: priPoi.lat });
    write(stageFiles.middle, _mj);
  }
}

// ---- 0) 民办学校实体名单（办学性质唯一真源）----
// 民办身份统一由 data/registry/minban_schools.json（官方文件汇总的民办名单表：各区教育局
// 年检结论/招生计划/积分入学计划等，source_urls 可追溯）生产到 entities.json（nature='民办'）；
// 公办为默认性质不写字段。不在表中的实体若有历史 nature 残留会被清除（表驱动，
// 防"手写 id 列表"式误标扩散——如 2026-09-18 修复的剑桥郡小学被误标民办）。
const MINBAN_IDS = new Set(
  read('data/registry/minban_schools.json').schools.map((s) => s.school_id),
);

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
    if (v === normName(ent.name)) continue;  // 自身归一名不入 aliases（索引侧 name 已覆盖）
    ent.aliases.add(v);
  }
  return true;
}
// tier1（网传口碑表）已于 2026-09-17 判定为废弃信息：只服务详情页「学校信号」模块（即将重构），
// 不得被数据管线依赖——别名挂载段已移除（历史：tier1 school_ids 曾把「广州市第十六中学(水荫校区)」
// 挂上「第十六中学本部」别名，属网传数据错误；本部限定名改由 OFFICIAL_HIGH_ALIAS/
// OFFICIAL_MIDDLE_ALIAS 官方录取表桥接，多校区承载走锚点表/显式映射）
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
      for (const v of withDistrictVariants(common)) if (v !== normName(e.name)) e.aliases.add(v);
    }
    for (const a of (ent.aliases || [])) for (const v of withDistrictVariants(normName(a))) if (v !== normName(e.name)) e.aliases.add(v);
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
// 官方划片表小学名（OFFICIAL_PRIMARY_ALIAS）：force=true 全挂（含多校区共享裸名）。
// 与高中录取表不同——划片表按小学法人名公布，多校区是并列关系（如「华阳小学」4 校区都招生），
// build_tianhe 需按官方名解析出全部校区实体；检查 [3] 已按共享裸名集合豁免。
for (const [official, poi] of Object.entries(OFFICIAL_PRIMARY_ALIAS)) {
  const list = Array.isArray(poi) ? poi : [poi];
  for (const p of list) {
    if (attachAlias('primary', p, official, true)) aliasHit++;
    else console.log('  [官方小学别名未命中POI]', official, '->', p);
  }
}

// ---- 3) 落盘实体（排序、aliases 去重排序）----
// 办学性质唯一真源：仅民办写 nature='民办'（公办为默认不写字段），由 minban_schools.json 联表生产
for (const e of entities) {
  if (MINBAN_IDS.has(e.school_id)) e.nature = '民办';
  else delete e.nature; // 表驱动：不在民办名单 = 公办，清历史残留
}
for (const e of entities) e.aliases = [...e.aliases].sort((a, b) => b.length - a.length);
entities.sort((a, b) => (a.stage + a.name).localeCompare(a.stage + a.name, 'zh'));
write('data/registry/entities.json', {
  year: 2026,
  note: '学校实体表（维度表）。一个 POI 点位=一个实体（校区/学部独立）；school_id 即主键。事实表用 school_id 引用；district 由 POI.adcode join。集团关系见 brand_groups/education_groups。nature=民办 为办学性质唯一真源（公办不写字段），由 data/registry/minban_schools.json（官方文件汇总表）生产。',
  entities,
});

// ---- 4) 回写 POI school_id；无实体关联的假 POI 完全删除 ----
// 匹配失败的 POI（school_id 为 null，如「广州市第三中学仁爱楼」「全家便利店(陶育店)」
// 「港湾中学-港湾咏春」等楼栋/设施/后门/便利店）都是假学校点位：不建实体、
// 不在地图/列表展示，直接从点位表删除（用户口径：无需展示），脚本可复现。
const stageMoved = {};  // 学段修正：从 middle 表迁出的 POI 记录（按目标 stage 收集）
for (const [stage, file] of Object.entries(stageFiles)) {
  const j = read(file);
  const kept = [];
  const seenPoiSid = new Set();  // 同 (stage, school_id) 重复点位去重（实体表同 id 唯一）
  for (const p of (j.schools || j)) {
    if (isNonMiddleCampus(stage, p.name) || isDropCampus(p.name)) continue;  // 纯高中校区/冗余点位删除
    const _st = stageFixOf(stage, p);
    if (_st !== stage) {  // 学段修正：从本表迁出（如 middle→high/primary），目标表追加
      stageMoved[_st] = stageMoved[_st] || [];
      stageMoved[_st].push({ ...p, ...(POI_COORD_FIX[p.school_id] || {}) });
      continue;
    }
    const fix = POI_COORD_FIX[p.school_id];
    if (fix) { p.lng = fix.lng; p.lat = fix.lat; }  // 坐标修正（如花地湾校区→花地大道北320号）
    const sid = poiIdByKey.get(stage + '|' + p.adcode + '|' + p.name) || null;
    p.school_id = sid;
    if (sid) {
      if (seenPoiSid.has(stage + '|' + sid)) continue;  // 同 id 已保留一条，跳过重复点位
      seenPoiSid.add(stage + '|' + sid);
      kept.push(p);
    }
  }
  j.schools = kept;
  write(file, j);
}
for (const [target, recs] of Object.entries(stageMoved)) {
  const j = read(stageFiles[target]);
  const seen = new Set(j.schools.map((x) => target + '|' + (x.school_id || '')));
  for (const p of recs) {
    const sid = poiIdByKey.get(target + '|' + p.adcode + '|' + p.name) || p.school_id || null;
    p.school_id = sid;
    if (sid && !seen.has(target + '|' + sid)) { j.schools.push(p); seen.add(target + '|' + sid); }
  }
  write(stageFiles[target], j);
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
