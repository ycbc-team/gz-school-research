/**
 * 名称匹配单元测试（node:test，零依赖）。
 * 运行：cd packages/shared && npm test（= node build.mjs && node --test tests/）
 *
 * 覆盖：
 *  1. 显式场景断言 —— normName 归一 / 品牌归属全等匹配
 *  2. 全量 POI 快照 —— 475 初中 + 931 小学 + 126 高中 的品牌归属映射，
 *     任何名称/别名/品牌表改动导致的匹配漂移都会 fail。
 * 更新快照：UPDATE_SNAPSHOT=1 npm test（仅当改动的确是有意的映射变化时）。
 * 注：tier1（口碑）匹配已于 2026-09-30 废弃归档，相关测试随业务一并移除。
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { normName, matchBrandByPoiName } = require('../dist/cjs/support.js');
const { diffSnapshots, formatDiff } = require('./helpers/snapshot-diff.cjs');

const ROOT = path.resolve(__dirname, '../../..');
const middlePois = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/poi/dist/middle_poi.json'), 'utf8')).schools;
const primaryPois = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/poi/dist/primary_poi.json'), 'utf8')).schools;
const highPois = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/poi/dist/high_poi.json'), 'utf8')).schools;
const brandGroups = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/registry/group/src/brand_groups.json'), 'utf8')).brands;

/* ========== 一、normName ========== */
test('normName：去广州市前缀、统一并删除括号、去空白', () => {
  assert.equal(normName('广州市执信中学（执信路校区）'), '执信中学执信路校区');
  assert.equal(normName('广东实验中学越秀学校(天胜校区)'), '广东实验中学越秀学校天胜校区');
  assert.equal(normName('广州 市第 一中学'), '广州市第一中学');
});

/* ========== 二、matchBrandByPoiName ========== */
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

/* ========== 三、全量快照（防名称/别名/品牌表改动漂移） ========== */
const SNAP = path.join(__dirname, 'snapshots', 'match_snapshot.json');

function buildSnapshot() {
  const brand = {};
  for (const p of [...middlePois.map((s) => ({ ...s, _s: '初中' })), ...primaryPois.map((s) => ({ ...s, _s: '小学' })), ...highPois.map((s) => ({ ...s, _s: '高中' }))]) {
    const b = matchBrandByPoiName(p.name, brandGroups);
    if (b) brand[p._s + '|' + p.name] = b;
  }
  return { brand };
}

test('全量快照：名称/别名/品牌表改动导致匹配漂移必须显式更新', () => {
  const snap = buildSnapshot();
  if (process.env.UPDATE_SNAPSHOT === '1') {
    fs.mkdirSync(path.dirname(SNAP), { recursive: true });
    fs.writeFileSync(SNAP, JSON.stringify(snap, null, 2) + '\n');
    console.log(`[snapshot] 已更新 ${SNAP}（brand ${Object.keys(snap.brand).length} 条）`);
    return;
  }
  assert.ok(fs.existsSync(SNAP), `快照不存在：${SNAP}。首次运行请执行 UPDATE_SNAPSHOT=1 npm test 生成基线。`);
  const base = JSON.parse(fs.readFileSync(SNAP, 'utf8'));
  const bd = diffSnapshots(base.brand, snap.brand);
  assert.deepEqual(bd.lines, [], `品牌归属快照漂移（${formatDiff(bd)}）：\n${bd.lines.join('\n')}`);
});
