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
