/**
 * 小学升学机制标签：parseXsMechanisms 归类（直升/派位/抽签）与
 * buildDetailModel.feedJuniors.mechanisms 输出契约。
 * 数据层未结构化机制枚举，group 文本（官方分组说明）是权威输入。
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

const { createRepository, buildDetailModel, parseXsMechanisms, splitEnrollments } = require('../dist/cjs/index.js');
const ROOT = path.resolve(__dirname, '../../..');
const load = (file) => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', file), 'utf8'));
const loaders = {
  primarySchools: load('poi/dist/primary_poi.json'),
  middleSchools: load('poi/dist/middle_poi.json'),
  highSchools: load('poi/dist/high_poi.json'),
  highLevels: load('high/level/src/levels.json'),
  enrollments: splitEnrollments(load('primary/enrollment/dist/2026-all.json')),
  quotaMatrix: load('linkage/dist/quota_matrix.json'),
  specialMatrix: load('linkage/dist/special_matrix.json'),
  batch2Scores: load('linkage/dist/batch2_scores.json'),
  districtQuota: load('linkage/dist/district_quota.json'),
  highScores2025: load('high/cutoff_score/dist/scores_2025.json'),
  highScores2026: load('high/cutoff_score/dist/scores_2026.json'),
  entities: load('registry/entity/dist/entities.json'),
  xiaoshengchu: load('primary/transition/dist/xiaoshengchu_2026.json'),
};
const repo = createRepository(loaders);

test('parseXsMechanisms：直升 / 派位 / 抽签归类', () => {
  // 单机制
  assert.deepEqual(parseXsMechanisms('白云区小升初对口（单校划片）'), ['直升']);
  assert.deepEqual(parseXsMechanisms('越秀区小升初第一组（多校划片·电脑派位）'), ['派位']);
  assert.deepEqual(parseXsMechanisms('海珠区公办初中第1组电脑派位'), ['派位']);
  assert.deepEqual(parseXsMechanisms('天河区公办初中对口直升（广州中学划片）'), ['直升']);
  assert.deepEqual(parseXsMechanisms('番禺区小升初对口（电脑抽签）'), ['抽签']);
  assert.deepEqual(parseXsMechanisms('番禺区小升初对口（单校（九年制））'), ['直升']);
  assert.deepEqual(parseXsMechanisms('番禺区小升初对口（多校（50%/50%））'), ['派位']);
  assert.deepEqual(parseXsMechanisms('黄埔区公办初中电脑派位第1组（多校划片）'), ['派位']);
  // 多机制混合：顺序固定 直升 → 派位 → 抽签
  assert.deepEqual(parseXsMechanisms('白云区小升初对口（单校划片；多校（部分地段/统筹））'), ['直升', '派位']);
  assert.deepEqual(parseXsMechanisms('天河区九年制学校内部直升（官方未单列小学部直升，按区属九年制直升惯例）+ 附件10全区电脑派位'), ['直升', '派位']);
  assert.deepEqual(parseXsMechanisms('天河区九年制/企事业办学校小学部内部直升'), ['直升']);
});

test('parseXsMechanisms：否定语境与缺口不计标签', () => {
  // 「不参加/不参与…派位」否定语境 → 只计直升、不计派位
  assert.deepEqual(parseXsMechanisms('对口直升（不参加电脑派位）'), ['直升']);
  assert.deepEqual(parseXsMechanisms('协和学校（市属十二年制，小学部直升本校初中部，不参加荔湾区公办初中派位）'), ['直升']);
  // 缺口组无机制标签
  assert.deepEqual(parseXsMechanisms('不参与公办派位/待核'), []);
  assert.deepEqual(parseXsMechanisms('不参与公办电脑派位'), []);
  assert.deepEqual(parseXsMechanisms('官方未单列（待核）'), []);
  assert.deepEqual(parseXsMechanisms(null), []);
  assert.deepEqual(parseXsMechanisms(''), []);
});

test('详情模型：feedJuniors.mechanisms 输出机制标签（真实数据）', () => {
  // 白云单校划片小学 → 直升
  const baiyun = loaders.primarySchools.schools.find(
    (p) => p.adcode === '440111' && p.school_id && /单校划片/.test(repo.xiaoshengchuOf(p.school_id)?.group || ''),
  );
  assert.ok(baiyun, '需要一所白云单校划片小学作为基线');
  let model = buildDetailModel('primary', baiyun.name, repo, baiyun.school_id);
  assert.ok(model.feedJuniors?.mechanisms?.includes('直升'), `白云单校划片应标直升: ${model.feedJuniors?.mechanisms}`);
  // 越秀电脑派位小学 → 派位
  const yuexiu = loaders.primarySchools.schools.find(
    (p) => p.adcode === '440104' && p.school_id && /电脑派位/.test(repo.xiaoshengchuOf(p.school_id)?.group || ''),
  );
  assert.ok(yuexiu, '需要一所越秀电脑派位小学作为基线');
  model = buildDetailModel('primary', yuexiu.name, repo, yuexiu.school_id);
  assert.ok(model.feedJuniors?.mechanisms?.includes('派位'), `越秀电脑派位应标派位: ${model.feedJuniors?.mechanisms}`);
  // 全量：所有有升学路线的小学 mechanisms 均为合法标签集合（直升/派位/抽签 子集）
  const legal = new Set(['直升', '派位', '抽签']);
  let checked = 0;
  for (const p of loaders.primarySchools.schools) {
    if (!p.school_id) continue;
    const m = buildDetailModel('primary', p.name, repo, p.school_id);
    if (!m.feedJuniors) continue;
    checked += 1;
    for (const t of m.feedJuniors.mechanisms || []) {
      assert.ok(legal.has(t), `非法机制标签 ${t}（${p.name}）`);
    }
  }
  assert.ok(checked > 100, `应覆盖大量小学，实际 ${checked}`);
});
