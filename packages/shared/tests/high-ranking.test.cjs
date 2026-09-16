'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { buildHighRankingGroups, buildHighRankingRows } = require('../dist/cjs/index.js');

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

test('高中明细 VM：全量学校的政策标签与简称均不混淆', () => {
  const rows = buildHighRankingRows(loaders);
  for (const row of rows) {
    if (row.category === '省市属示范') assert.ok(['省属', '市属'].includes(row.affiliation), `${row.name} 应标注省属或市属`);
    else if (row.category === '区属示范') assert.match(row.affiliation || '', /^.+区属$/, `${row.name} 应标注对应区属`);
    else assert.equal(row.affiliation, null, `${row.name} 不应展示行政隶属为招生政策标签`);
  }
  const collisions = new Map();
  for (const row of rows) collisions.set(row.displayName, [...(collisions.get(row.displayName) || []), row.name]);
  assert.deepEqual([...collisions].filter(([, names]) => new Set(names).size > 1), [], '任意两所学校的列表简称不得重名');
  const guangdong = rows.find((row) => row.name === '广东实验中学(高中部)');
  const guangzhou = rows.find((row) => row.name === '广州实验中学');
  assert.notEqual(guangdong?.displayName, guangzhou?.displayName);
});

test('高中明细 VM：支持不分组、七区位置筛选与多年份排序', () => {
  const liwanOnly = buildHighRankingGroups(loaders, {
    groupBy: 'none', districtAdcodes: ['440103'], sortBy: 'score2025',
  });
  assert.equal(liwanOnly.length, 1);
  assert.equal(liwanOnly[0].title, '全部高中');
  assert.ok(liwanOnly[0].items.every((row) => row.district === '荔湾区'));
  const scores = liwanOnly[0].items.map((row) => row.sortScore2025).filter((value) => value != null);
  assert.deepEqual(scores, scores.slice().sort((a, b) => b - a));

  const averaged = buildHighRankingGroups(loaders, { groupBy: 'district', sortBy: 'average' });
  for (const group of averaged) {
    const values = group.items.map((row) => row.sortScoreAverage).filter((value) => value != null);
    assert.deepEqual(values, values.slice().sort((a, b) => b - a));
  }
});

test('高中明细 VM：支持按招生学校分类筛选，普通公办高中独立于民办和区属示范', () => {
  const provincialMunicipal = buildHighRankingGroups(loaders, {
    groupBy: 'none', filters: ['province-municipal-demo'],
  });
  assert.ok(provincialMunicipal[0].items.length > 0);
  assert.ok(provincialMunicipal[0].items.every((row) => ['省属', '市属'].includes(row.affiliation)));

  const ordinary = buildHighRankingGroups(loaders, { groupBy: 'none', filters: ['normal-public'] });
  assert.ok(ordinary[0].items.every((row) => row.category === '普通高中' && !row.minban));
  assert.deepEqual(buildHighRankingGroups(loaders, { groupBy: 'none', filters: [] }), []);
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
  assert.equal(rows.find((row) => row.name === '广州市西关培英中学')?.affiliation, null, '普通高中不展示行政区属');
});
