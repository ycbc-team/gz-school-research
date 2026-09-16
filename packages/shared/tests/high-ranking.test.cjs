'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { buildHighRankingGroups } = require('../dist/cjs/index.js');

const ROOT = path.resolve(__dirname, '../../..');
const load = (file) => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', file), 'utf8'));
const loaders = {
  highSchools: load('high/schools-gz.json'),
  highLevels: load('high/levels.json'),
  highScores2025: load('high/scores_2025.json'),
  highScores2026: load('high/scores_2026.json'),
  entities: load('registry/entities.json'),
};

test('高中明细 VM：仅七区、保留两年录取线，并按 2026 分数降序', () => {
  const groups = buildHighRankingGroups(loaders, 'district');
  const rows = groups.flatMap((group) => group.items);
  assert.equal(rows.some((row) => row.district === '南沙区'), false);
  assert.ok(rows.some((row) => row.score2025.length && row.score2026.length), '应至少有一所学校具备两年官方录取线');
  for (const group of groups) {
    const values = group.items.map((row) => row.sortScore2026).filter((value) => value != null);
    assert.deepEqual(values, values.slice().sort((a, b) => b - a));
  }
});

test('高中明细 VM：只展示第三批户籍生，且绝不聚合同校其它校区', () => {
  const rows = buildHighRankingGroups(loaders, 'category').flatMap((group) => group.items);
  const universityTown = rows.find((row) => row.name === '广州大学附属中学(大学城校区)');
  assert.equal(universityTown?.score2026[0]?.text, '738');
  assert.equal(universityTown?.score2025[0]?.text, '732');
  assert.equal(rows.some((row) => row.name === '广州市真光中学(芳花校区)'), false);
  assert.ok(rows.some((row) => row.name === '广州市西关培英中学' && row.score2026.length === 0), '仅第四批的学校应展示为空');
  assert.ok(rows.some((row) => row.category === '普通高中'), '普通高中应单独分组，不并入省市属示范');
});

test('高中明细 VM：民办徽标读取实体注册表办学性质', () => {
  const rows = buildHighRankingGroups(loaders, 'category').flatMap((group) => group.items);
  assert.equal(rows.find((row) => row.name === '耀华中学')?.minban, true);
  assert.equal(rows.find((row) => row.name === '广东实验中学(高中部)')?.minban, false);
});

test('高中明细 VM：未标注点位并入普通高中模块', () => {
  const unclassified = {
    ...loaders,
    highSchools: {
      ...loaders.highSchools,
      schools: [...loaders.highSchools.schools, {
        name: '未标注高中', school: '未标注高中', school_id: 'test-unclassified-high',
        adcode: '440103', lng: 113.2, lat: 23.1,
      }],
    },
    entities: {
      ...loaders.entities,
      entities: [...loaders.entities.entities, {
        school_id: 'test-unclassified-high', name: '未标注高中', stage: 'high', aliases: [],
      }],
    },
  };
  const groups = buildHighRankingGroups(unclassified, 'category');
  assert.equal(groups.some((group) => group.title === '未标注'), false);
  const normal = groups.find((group) => group.title === '普通高中');
  assert.ok(normal?.items.some((row) => row.category === '未标注'));
});

test('高中明细 VM：校区保留隶属信息，未匹配时为空', () => {
  const noAffiliation = {
    ...loaders,
    highSchools: {
      ...loaders.highSchools,
      schools: [...loaders.highSchools.schools, {
        name: '无隶属高中', school: '无隶属高中', school_id: 'test-no-affiliation-high',
        adcode: '440103', lng: 113.2, lat: 23.1,
      }],
    },
    entities: {
      ...loaders.entities,
      entities: [...loaders.entities.entities, {
        school_id: 'test-no-affiliation-high', name: '无隶属高中', stage: 'high', aliases: [],
      }],
    },
  };
  const rows = buildHighRankingGroups(noAffiliation, 'category').flatMap((group) => group.items);
  assert.equal(rows.find((row) => row.name === '广东实验中学(高中部)')?.affiliation, '省属');
  assert.equal(rows.find((row) => row.name === '无隶属高中')?.affiliation, null);
});
