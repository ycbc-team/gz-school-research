/**
 * 详情模型回归：Web 与小程序都必须只渲染 buildDetailModel 的结果。
 * 选取小学/初中/高中各一例，固定跨学部、招生、升学路线和录取线的关键契约。
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { createRepository, buildDetailModel, buildLinkageModel, normName } = require('../dist/cjs/index.js');
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

test('第一批高中详情只按 school_id 反查，所有已映射招生单位均有覆盖数据', () => {
  const special = loaders.specialMatrix;
  const seen = new Set();
  const missing = [];
  for (const [rawName, schoolId] of Object.entries(special.high_school_ids || {})) {
    if (!schoolId || seen.has(schoolId)) continue;
    seen.add(schoolId);
    const entity = repo.entities.find((e) => e.school_id === schoolId);
    if (!entity) {
      missing.push(`${rawName}: 实体不存在(${schoolId})`);
      continue;
    }
    const model = buildLinkageModel('high', entity.name, repo, schoolId);
    if (!model.highSpecialCoverage.length) missing.push(`${rawName}: ${schoolId} 无第一批覆盖`);
  }
  assert.deepEqual(missing, [], `第一批招生 ID 反查回归: ${missing.join('; ')}`);
});

test('品牌关联：广大附黄华路校区以 school_id 标记当前项并生成 ID 跳转', () => {
  const schoolId = 'gz-440104-b22c4eca';
  const entity = repo.entities.find((e) => e.school_id === schoolId);
  assert.ok(entity, '黄华路校区实体必须存在');
  const model = buildDetailModel('middle', entity.name, repo, schoolId);
  const rows = model.brandCard.groups.flatMap((g) => g.rows);
  const current = rows.filter((r) => r.isCurrent);
  assert.deepEqual(current.map((r) => r.name), ['广州大学附属中学（黄华路校区）']);
  assert.match(current[0].link, /id=gz-440104-b22c4eca/);
});

test('品牌关联：全量品牌实体对比修复前后，品牌分支新增当前态必须由显式身份来源支撑', () => {
  const eligible = repo.entities.filter((entity) =>
    ['primary', 'middle', 'high'].includes(entity.stage) &&
    repo.groupOfSchool(entity.name, entity.school_id)?.source === 'brand',
  );
  // 覆盖范围快照：新品牌实体加入时必须显式审阅这条 ID 当前态规则。
  // 口径 = groupOfSchool 解析为 brand 来源的全部实体（按名 + school_id 外键），school_id 外键新增实体同样受回归保护。
  // 注：重跑生产脚本后为 65 —— 铁英小学/铁英中学/省实荔湾初中部/广雅荔湾/西关广雅南岸路 5 个实体
  // 同时命中 education 索引（education 优先），回归 education 分支，不再计入 brand 覆盖。
  // 2026-09-16 品牌关联治理后为 66：锚点表瘦身 + entities 脚本构建（school_id 外键 35 个 + 按名匹配 31 个），
  // 品牌详情页覆盖范围经全量回归审阅（每个实体均能解析到集团且当前态非空）。
  assert.equal(eligible.length, 66, '品牌实体覆盖范围变更，请审阅当前态回归结果');
  const failures = [];
  for (const entity of eligible) {
    const group = repo.groupOfSchool(entity.name, entity.school_id);
    assert.ok(group, `${entity.name}: 必须能解析到集团`);
    const model = buildDetailModel(entity.stage, entity.name, repo, entity.school_id);
    const after = model.brandCard.groups.flatMap((g) => g.rows)
      .filter((r) => r.isCurrent)
      .map((r) => r.name)
      .sort();
    if (!after.length) failures.push(`${entity.name}: 修复后没有当前项`);

    if (group.source === 'education') {
      // 本次修复只改品牌分支；教育集团分支的当前态必须逐项保持不变。
      const before = group.members
        .filter((m) => (m.school_id && m.school_id === entity.school_id) || normName(m.name) === normName(entity.name) || (m.poi_name && normName(m.poi_name) === normName(entity.name)))
        .map((m) => m.name)
        .sort();
      if (JSON.stringify(after) !== JSON.stringify(before)) {
        failures.push(`${entity.name}: 教育集团当前项发生变化（修复前 ${before.join('、')}；修复后 ${after.join('、')}）`);
      }
      continue;
    }

    // 修复前品牌规则会剥离括号内容再比名（校区实体因此普遍失去当前态）；修复后：
    // - 保留原命中（非校区别名兼容，仅无校区括号的单位）；
    // - 新增命中必须来自显式身份来源之一：school_id 外键 / 全名全等（校区括号是身份的一部分）/ poi_names 显式点位覆盖。
    const before = group.members
      .filter((m) => normName(m.name.replace(/[（(][^）)]*[）)]/g, '')) === normName(entity.name))
      .map((m) => m.name);
    const legitNew = group.members
      .filter((m) =>
        (m.school_ids || []).includes(entity.school_id) ||
        normName(m.name) === normName(entity.name) ||
        (m.poi_names || []).some((p) => normName(p) === normName(entity.name)),
      )
      .map((m) => m.name);
    for (const name of before) {
      if (!after.includes(name)) failures.push(`${entity.name}: 原当前项丢失 ${name}`);
    }
    for (const name of after) {
      if (!before.includes(name) && !legitNew.includes(name)) failures.push(`${entity.name}: 出现无显式身份来源支撑的新当前项 ${name}`);
    }
  }
  assert.deepEqual(failures, [], `品牌当前态全量回归: ${failures.join('; ')}`);
});
