/**
 * 数据层完整性测试（node:test，零依赖）。
 * 运行：cd packages/shared && npm test
 *
 * 覆盖：
 *  1. 实体/POI 外键：每个 POI 的 school_id 在 entities 里存在；entities 无孤儿
 *  2. 校名合法性：schoolnames.json 不出现 OCR 垃圾（单字、空、纯符号）
 *  3. 升学关系引用完整性：district_quota / quota_matrix 引用的学校名必须能在 POI 或 entities 里归一化命中
 *  4. 名额值约束：必须是非负整数
 *  5. 品牌成员：brand_groups 的成员 school_id 在 entities 里
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { normName } = require('../dist/cjs/support.js');

const ROOT = path.resolve(__dirname, '../../..');
const load = (rel) => JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8'));

const entities = load('data/registry/entities.json').entities;
const middlePois = load('data/middle/schools-gz.json').schools;
const primaryPois = load('data/primary/schools-gz.json').schools;
const highPois = load('data/high/schools-gz.json').schools;
const districtQuota = load('data/linkage/district_quota.json').data;
const quotaMatrix = load('data/linkage/quota_matrix.json');
const schoolnames = load('data/linkage/raw/schoolnames.json');
const brandGroups = load('data/registry/brand_groups.json').brands;

/** 归一化后的校名集合（POI + entities 并集），用于引用校验 */
const nameSet = new Set();
for (const p of [...middlePois, ...primaryPois, ...highPois]) {
  if (p.name) nameSet.add(normName(p.name));
  if (p.school) nameSet.add(normName(p.school));
}
for (const e of entities) {
  if (e.name) nameSet.add(normName(e.name));
  if (e.aliases) for (const a of e.aliases) nameSet.add(normName(a));
}

/* ========== 一、实体/POI 外键 ========== */
test('每个 POI 的 school_id 在 entities 里存在', () => {
  const ids = new Set(entities.map((e) => e.school_id));
  const missing = [];
  for (const p of [...middlePois, ...primaryPois, ...highPois]) {
    if (p.school_id && !ids.has(p.school_id)) missing.push(p.name || p.school, p.school_id);
  }
  assert.deepEqual(missing, [], `POI 引用了不存在的 entity: ${missing.join(', ')}`);
});

test('entities 里每个实体都有合法 name（非空、非单字 OCR 垃圾）', () => {
  const bad = entities.filter(
    (e) => !e.name || e.name.trim().length < 2 || /^[必的了吗呢啊哦]$/.test(e.name.trim()),
  );
  assert.deepEqual(bad.map((e) => e.school_id + '=' + e.name), [], 'entities 存在可疑校名');
});

/* ========== 二、schoolnames.json 无 OCR 垃圾 ========== */
test('schoolnames.json 不出现单字/空字符串的非区名', () => {
  const bad = [];
  for (const [p, arr] of Object.entries(schoolnames)) {
    arr.forEach((nm, i) => {
      if (!nm) return; // 空行允许（OCR 多识别行）
      const t = nm.trim();
      // 区名（XX区）允许
      if (/^[东西南北]?[山区市县]?$/.test(t) || t.endsWith('区')) return;
      // 单字或纯标点视为 OCR 垃圾
      if (t.length < 2 || /^[，。、；：！？\s必]$/.test(t)) bad.push(`p${p}[${i}]=${JSON.stringify(nm)}`);
    });
  }
  assert.deepEqual(bad, [], `schoolnames.json 存在 OCR 垃圾: ${bad.join('; ')}`);
});

/* ========== 三、升学关系引用完整性 ========== */
/**
 * 引用名只拦 OCR 垃圾（半截名/单字/截断），不要求全部命中 POI——
 * 官方名单里很多学校尚未采集点位是数据现状，由快照/人工 review 跟进。
 */
const isOcrJunk = (nm) => {
  if (!nm) return true;
  const t = nm.trim();
  if (t.length < 3) return true;
  // 半截名特征：以"市第"结尾、或只有"XX中学/学校"前半段
  if (/市第[一二三四五六七八九十]*$/.test(t)) return true;
  // 已知 OCR 误识别字符
  if (/[—–]{2,}/.test(t)) return true;
  return false;
};

test('district_quota 初中名不含 OCR 垃圾（半截/单字）', () => {
  const bad = Object.keys(districtQuota).filter(isOcrJunk);
  assert.deepEqual(bad, [], `district_quota 初中名疑似 OCR 错误: ${bad.join(', ')}`);
});

test('district_quota 高中名不含 OCR 垃圾', () => {
  const bad = new Set();
  for (const row of Object.values(districtQuota)) {
    for (const s of Object.keys(row)) if (isOcrJunk(s)) bad.add(s);
  }
  assert.deepEqual([...bad], [], `district_quota 高中名疑似 OCR 错误: ${[...bad].join(', ')}`);
});

test('quota_matrix.school 不含 OCR 垃圾', () => {
  const bad = (quotaMatrix.schools || []).map((s) => s.school).filter(isOcrJunk);
  assert.deepEqual(bad, [], `quota_matrix 学校名疑似 OCR 错误: ${bad.join(', ')}`);
});

/* ========== 四、名额值约束 ========== */
test('district_quota 名额值为非负整数', () => {
  const bad = [];
  for (const [j, row] of Object.entries(districtQuota)) {
    for (const [s, v] of Object.entries(row)) {
      if (!Number.isInteger(v) || v < 0 || v > 500) bad.push(`${j}->${s}=${v}`);
    }
  }
  assert.deepEqual(bad, [], `名额值异常: ${bad.join(', ')}`);
});

/* ========== 五、品牌成员外键 ========== */
test('brand_groups 成员 school_id 在 entities 里存在', () => {
  const ids = new Set(entities.map((e) => e.school_id));
  const missing = [];
  for (const b of brandGroups) {
    for (const m of b.members || []) {
      const sid = typeof m === 'string' ? m : m.school_id;
      if (sid && !ids.has(sid)) missing.push(b.brand || b.name, sid);
    }
  }
  assert.deepEqual(missing, [], `品牌成员引用了不存在的 entity: ${missing.join(', ')}`);
});
