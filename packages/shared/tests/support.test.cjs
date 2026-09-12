/**
 * 名称匹配单元测试（node:test，零依赖）。
 * 运行：cd packages/shared && npm test（= node build.mjs && node --test tests/）
 *
 * 覆盖：
 *  1. 显式场景断言 —— 精确命中 / 别名命中 / 校区全名 / 独立法人不误配 / 品牌归属
 *  2. 全量 POI 快照 —— 475 初中 + 931 小学 的 tier1 命中映射 + 品牌归属映射，
 *     任何名称/别名/品牌表改动导致的匹配漂移都会 fail。
 * 更新快照：UPDATE_SNAPSHOT=1 npm test（仅当改动的确是有意的映射变化时）。
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { normName, buildAliasTable, matchTier1ByPoiName, matchBrandByPoiName } = require('../dist/cjs/support.js');

const ROOT = path.resolve(__dirname, '../../..');
const loadTier1 = (f) => {
  const d = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', f), 'utf8'));
  const out = [];
  for (const v of Object.values(d.districts || {})) out.push(...v.schools);
  return out;
};
const middleTier1 = loadTier1('middle/tier1_schools_all.json');
const primaryTier1 = loadTier1('primary/tier1_schools_all.json');
const middlePois = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/middle/schools-gz.json'), 'utf8')).schools;
const primaryPois = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/primary/schools-gz.json'), 'utf8')).schools;
const highPois = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/high/schools-gz.json'), 'utf8')).schools;
const brandGroups = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/registry/brand_groups.json'), 'utf8')).brands;
const entities = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/registry/entities.json'), 'utf8')).entities;

const mTable = buildAliasTable(middleTier1, entities);
const pTable = buildAliasTable(primaryTier1, entities);

/* ========== 一、normName ========== */
test('normName：去广州市前缀、统一并删除括号、去空白', () => {
  assert.equal(normName('广州市执信中学（执信路校区）'), '执信中学执信路校区');
  assert.equal(normName('广东实验中学越秀学校(天胜校区)'), '广东实验中学越秀学校天胜校区');
  assert.equal(normName('广州 市第 一中学'), '广州市第一中学');
});

/* ========== 二、matchTier1ByPoiName：命中场景 ========== */
test('精确名命中：执信本部、番禺铁英（别名表来自实体注册表）', () => {
  const h1 = matchTier1ByPoiName('广州市执信中学（执信路校区）', middleTier1, mTable);
  assert.ok(h1 && h1.name.includes('执信中学（执信路校区）'));
  const h2 = matchTier1ByPoiName('广州市番禺区广铁一中铁英学校（番禺铁英）', middleTier1, mTable);
  assert.ok(h2 && h2.tier1_eligible === true);
});

test('黄埔铁英口碑记录无实体（POI 未收录）→ 别名表不命中，属正确行为', () => {
  const h = matchTier1ByPoiName('广州市黄埔区铁英学校（黄埔铁英）', middleTier1, mTable);
  assert.equal(h, undefined);
});

test('别名命中：星执（POI 短名 → 星执挂牌记录）', () => {
  const h = matchTier1ByPoiName('广州市星执学校', middleTier1, mTable);
  assert.ok(h && h.name.includes('星执'));
  assert.equal(h.tier1_eligible, false);
});

test('校区全名 alias 命中：番禺铁英东/西校区 → 番禺铁英（口碑）', () => {
  for (const n of ['广州市番禺区广铁一中铁英学校(东校区)', '广州市番禺区广铁一中铁英学校(西校区)']) {
    const h = matchTier1ByPoiName(n, middleTier1, mTable);
    assert.ok(h, `应命中：${n}`);
    assert.ok(h.name.includes('番禺区广铁一中铁英学校'));
    assert.equal(h.tier1_eligible, true);
  }
});

test('修正误配：铁一白云校区 → 白云铁一（而非越秀校区）', () => {
  const h = matchTier1ByPoiName('广州市铁一中学(白云校区)', middleTier1, mTable);
  assert.ok(h && h.name.includes('白云区铁一学校'));
});

/* ========== 三、matchTier1ByPoiName：不误配场景（前缀匹配已废除） ========== */
test('独立法人托管校不误配本部口碑', () => {
  const cases = [
    '广东实验中学越秀学校(天胜校区)', // 不应命中「广东实验中学（初中部）」
    '广东实验中学越秀学校(盘福校区)',
    '广大附中番禺实验学校',           // 不应命中「广州大学附属中学（黄华路校区）」
    '广州市东风实验学校',             // 不应命中执信
    '广州市第十六中学实验学校',       // 不应命中十六中本部
    '广州市第七中学实验学校',         // 不应命中七中本部
    '广州市南武中学附属学校',         // 不应命中南武本部
    '广东实验中学(云城校区)',         // 云城为区属新校，不应命中省实本部
    '广州市第一中学双桥学校',         // 一中集团成员校，不应命中一中口碑
    '广州市天河中学猎德实验学校',     // 猎德实验为独立法人，不应命中天河中学
  ];
  for (const n of cases) {
    const h = matchTier1ByPoiName(n, middleTier1, mTable);
    assert.equal(h, undefined, `不应命中任何口碑/挂牌记录：${n}（实际命中：${h && h.name}）`);
  }
});

test('前缀不再生效（核心回归）：品牌前缀不吸收独立校名', () => {
  // 若前缀匹配复活，「广东实验中学越秀学校」会被「广东实验中学」前缀吸到省实本部
  const h = matchTier1ByPoiName('广东实验中学越秀学校(天胜校区)', middleTier1, mTable);
  assert.equal(h, undefined);
  const h2 = matchTier1ByPoiName('广大附中番禺实验学校', middleTier1, mTable);
  assert.equal(h2, undefined);
});

test('同法人校区变体通过显式 alias 命中（不再是前缀兜底）', () => {
  const cases = [
    ['广州市真光中学(岭南校区)', '广州市真光中学（校本部）'],
    ['广州市第四中学(津园校区)', '广州市第四中学'],
    ['广州市第一中学(初中部)', '广州市第一中学'],
    ['广州市执信中学(水荫路校区)', '广州市执信中学（执信路校区）'],
    ['广东实验中学荔湾学校(初中部)', '广东实验中学荔湾学校（省实荔湾）'],
    ['广州市铁一中学白云校区(初中部)', '广州市白云区铁一学校（白云铁一）'],
    ['广州云雅实验学校初中部', '广州市白云区云雅实验学校'],
    ['广州市黄埔区苏元学校(西校区)', '广州市黄埔区苏元学校（二中苏元）'],
  ];
  for (const [poi, expectFrag] of cases) {
    const h = matchTier1ByPoiName(poi, middleTier1, mTable);
    assert.ok(h, `${poi} 应命中含「${expectFrag}」的记录（实际：${h && h.name}）`);
    const nH = normName(h.name);
    const nE = normName(expectFrag);
    assert.ok(nH === nE || nH.includes(nE) || nE.includes(nH), `${poi} 应命中含「${expectFrag}」的记录（实际：${h.name}）`);
  }
});

test('新开办学校不进口碑（数据层 note 由调用层短路；匹配层本身不产生命中即可）', () => {
  // 这些带「新开办」note 的 POI 不在 tier1 名单（无别名），匹配层必须返回 undefined
  const newPois = middlePois.filter((p) => p.note && p.note.includes('新开办'));
  assert.ok(newPois.length >= 8, `应至少有 8 所带新开办 note 的初中 POI（实际 ${newPois.length}）`);
  for (const p of newPois) {
    const h = matchTier1ByPoiName(p.name, middleTier1, mTable);
    assert.equal(h, undefined, `新开办 POI 不应命中口碑/挂牌记录：${p.name}`);
  }
});

/* ========== 四、matchBrandByPoiName ========== */
test('品牌归属全等匹配', () => {
  const cases = [
    ['广东实验中学越秀学校(天胜校区)', '广东实验中学教育集团'],
    ['广东实验中学天河学校', '广东实验中学教育集团'],
    ['广州市番禺区广铁一中铁英学校(东校区)', '广铁一中教育集团'],
    ['广州市铁一中学(番禺校区)', '广铁一中教育集团'],
    ['广州市星执学校', '广州市执信中学教育集团'],
    ['广州市番禺区番雅实验学校', '广东广雅中学教育集团'],
    ['广州市黄埔区苏元学校', '广州市第二中学教育集团'],
  ];
  for (const [poi, expectBrand] of cases) {
    assert.equal(matchBrandByPoiName(poi, brandGroups), expectBrand, `${poi} 应归属 ${expectBrand}`);
  }
});

test('品牌不误配：非品牌成员不靠前缀进组', () => {
  for (const n of ['广州市第一中学双桥学校', '广州市天河中学猎德实验学校', '广州市第七中学实验学校']) {
    assert.equal(matchBrandByPoiName(n, brandGroups), undefined, `${n} 不应靠前缀进任何品牌组`);
  }
});

/* ========== 五、全量快照（防名称/别名/品牌表改动漂移） ========== */
const SNAP = path.join(__dirname, 'snapshots', 'match_snapshot.json');

function buildSnapshot() {
  const tier = {};
  for (const p of middlePois) {
    const h = matchTier1ByPoiName(p.name, middleTier1, mTable);
    if (h) tier['初中|' + p.name] = h.name;
  }
  for (const p of primaryPois) {
    const h = matchTier1ByPoiName(p.name, primaryTier1, pTable);
    if (h) tier['小学|' + p.name] = h.name;
  }
  const brand = {};
  for (const p of [...middlePois.map((s) => ({ ...s, _s: '初中' })), ...primaryPois.map((s) => ({ ...s, _s: '小学' })), ...highPois.map((s) => ({ ...s, _s: '高中' }))]) {
    const b = matchBrandByPoiName(p.name, brandGroups);
    if (b) brand[p._s + '|' + p.name] = b;
  }
  return { tier, brand };
}

test('全量快照：名称/别名/品牌表改动导致匹配漂移必须显式更新', () => {
  const snap = buildSnapshot();
  if (process.env.UPDATE_SNAPSHOT === '1') {
    fs.mkdirSync(path.dirname(SNAP), { recursive: true });
    fs.writeFileSync(SNAP, JSON.stringify(snap, null, 2) + '\n');
    console.log(`[snapshot] 已更新 ${SNAP}（tier ${Object.keys(snap.tier).length} 条 / brand ${Object.keys(snap.brand).length} 条）`);
    return;
  }
  assert.ok(fs.existsSync(SNAP), `快照不存在：${SNAP}。首次运行请执行 UPDATE_SNAPSHOT=1 npm test 生成基线。`);
  const base = JSON.parse(fs.readFileSync(SNAP, 'utf8'));
  assert.deepEqual(snap.tier, base.tier, `tier1 匹配快照漂移！改动名称/别名后请先确认意图，再 UPDATE_SNAPSHOT=1 更新。`);
  assert.deepEqual(snap.brand, base.brand, `品牌归属快照漂移！改动品牌表后请先确认意图，再 UPDATE_SNAPSHOT=1 更新。`);
});
