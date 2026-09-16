/**
 * 详情模型回归：Web 与小程序都必须只渲染 buildDetailModel 的结果。
 * 选取小学/初中/高中各一例，固定跨学部、招生、升学路线和录取线的关键契约。
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { createRepository, buildDetailModel } = require('../dist/cjs/index.js');
const ROOT = path.resolve(__dirname, '../../..');
const load = (file) => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', file), 'utf8'));
const loaders = {
  primarySchools: load('primary/schools-gz.json'),
  primaryTier1: load('primary/tier1_schools_all.json'),
  middleSchools: load('middle/schools-gz.json'),
  middleTier1: load('middle/tier1_schools_all.json'),
  highSchools: load('high/schools-gz.json'),
  highLevels: load('high/levels.json'),
  enrollments: ['tianhe', 'yuexiu', 'haizhu', 'liwan', 'panyu', 'baiyun', 'huangpu'].map((d) => load(`primary/enrollments/2026-${d}.json`)),
  quotaMatrix: load('linkage/quota_matrix.json'),
  specialMatrix: load('linkage/special_matrix.json'),
  batch2Scores: load('linkage/batch2_scores.json'),
  districtQuota: load('linkage/district_quota.json'),
  highScores2025: load('high/scores_2025.json'),
  highScores2026: load('high/scores_2026.json'),
  entities: load('registry/entities.json'),
  xiaoshengchu: load('primary/xiaoshengchu_2026.json'),
  sites: load('registry/sites.json'),
  brandGroups: load('registry/brand_groups.json'),
  educationGroups: load('registry/education_groups.json'),
  rankingMiddle: load('linkage/ranking_middle.json'),
};
const repo = createRepository(loaders);

test('详情模型：小学保留招生与升学路线', () => {
  const poi = loaders.primarySchools.schools.find((p) => p.school_id && repo.matchEnrollment(p.school_id) && repo.xiaoshengchuOf(p.school_id));
  assert.ok(poi, '需要一所同时有招生和升学路线数据的小学作为基线');
  const model = buildDetailModel('primary', poi.name, repo, poi.school_id);
  assert.equal(model.stage, 'primary');
  assert.ok(model.availableStages.includes('primary'));
  assert.ok(model.enrollment);
  assert.ok(model.feedJuniors || model.feedGap);
});

test('详情模型：初中保留名额通道与生源反查', () => {
  const row = loaders.quotaMatrix.schools.find((s) => s.school_id);
  assert.ok(row, '名额矩阵应至少有一所已关联实体的初中');
  const name = repo.entities.find((e) => e.school_id === row.school_id).name;
  const model = buildDetailModel('middle', name, repo, row.school_id);
  assert.equal(model.stage, 'middle');
  assert.ok(model.availableStages.includes('middle'));
});

test('详情模型：高中保留官方录取线', () => {
  const [schoolId] = Object.keys(loaders.highScores2026.by_school_id);
  const entity = repo.entities.find((e) => e.school_id === schoolId);
  assert.ok(entity, '录取线 school_id 必须关联实体');
  const model = buildDetailModel('high', entity.name, repo, schoolId);
  assert.equal(model.stage, 'high');
  assert.ok(model.admissionRows.length > 0);
});

test('详情模型：高中校区详情不聚合同校其它校区的录取线', () => {
  const poi = loaders.highSchools.schools.find((p) => p.name === '广州市真光中学(广钢校区)');
  assert.ok(poi?.school_id, '需要真光广钢校区实体');
  const model = buildDetailModel('high', poi.name, repo, poi.school_id);
  assert.equal(model.admissionRows.length, 2);
  assert.ok(model.admissionRows.every((row) => row.value.includes('广钢')));
});
