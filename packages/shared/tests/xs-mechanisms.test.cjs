/**
 * 小学升学机制徽章：数据驱动契约（与初中机制枚举完全对齐）。
 * 机制在数据层固化（parsed 转录解析 + from_middle 初中直写；dist 五区以初中反推为准），
 * 运行时零文本匹配——buildDetailModel.feedJuniors.mechanisms 直接读 dist groups.mechanism。
 * 校验：真实数据 case 归类、label 与初中一致、全量合法性与顺序。
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

const { createRepository, buildDetailModel, XS_MECH_LABELS, splitEnrollments } = require('../dist/cjs/index.js');
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
// 初中机制枚举 label 真源（对齐断言用）
const MIDDLE_MECH_LABELS = { zhi_sheng: '对口直升', single_zone: '单校划片', group_paidui: '多校电脑派位', single_paidui: '电脑派位', min_zi_zhu: '自主招生' };
const MECH_ORDER = ['zhi_sheng', 'single_zone', 'group_paidui', 'single_paidui', 'min_zi_zhu'];

function primaryBy(adcode, groupRe) {
  const hit = loaders.primarySchools.schools.find((p) => p.adcode === adcode && p.school_id && groupRe.test(repo.xiaoshengchuOf(p.school_id)?.group || ''));
  assert.ok(hit, `需要 ${adcode} 命中 ${groupRe} 的小学作为基线`);
  return hit;
}
function mechsOf(poi) {
  return buildDetailModel('primary', poi.name, repo, poi.school_id).feedJuniors?.mechanisms || [];
}
/** 找 group 命中且机制恰为 expected 的小学（机制以数据为准——dist 记录级初中反推/官方解析） */
function primaryBy(adcode, groupRe, expected) {
  const hit = loaders.primarySchools.schools.find(
    (p) => p.adcode === adcode && p.school_id && groupRe.test(repo.xiaoshengchuOf(p.school_id)?.group || '')
      && JSON.stringify(mechsOf(p)) === JSON.stringify(expected),
  );
  assert.ok(hit, `需要 ${adcode} 命中 ${groupRe} 且机制为 ${expected} 的小学作为基线`);
  return hit;
}

test('真实数据：机制归类与初中枚举对齐（数据驱动）', () => {
  // 白云单校划片 → single_zone
  assert.deepEqual(mechsOf(primaryBy('440111', /白云区小升初对口（单校划片）/, ['single_zone'])), ['single_zone']);
  // 越秀派位组 → group_paidui（初中同区口径）
  assert.deepEqual(mechsOf(primaryBy('440104', /越秀区小升初第.+组（多校划片·电脑派位）/, ['group_paidui'])), ['group_paidui']);
  // 越秀直升+派位并存（九年制小学，初中反推精确）→ zhi_sheng 先行
  assert.deepEqual(mechsOf(primaryBy('440104', /越秀区小升初第.+组（多校划片·电脑派位）/, ['zhi_sheng', 'group_paidui'])), ['zhi_sheng', 'group_paidui']);
  // 海珠派位组 → group_paidui
  assert.deepEqual(mechsOf(primaryBy('440105', /海珠区公办初中第.+组电脑派位/, ['group_paidui'])), ['group_paidui']);
  // 天河对口划片 → single_zone（天河初中 zhi_sheng=0，对口划片标 single_zone）
  assert.deepEqual(mechsOf(primaryBy('440106', /天河区公办初中对口直升（广州中学划片）/, ['single_zone'])), ['single_zone']);
  // 天河九年制内部直升 + 附件10 → zhi_sheng + min_zi_zhu（直升先行）
  assert.deepEqual(mechsOf(primaryBy('440106', /天河区九年制学校内部直升/, ['zhi_sheng', 'min_zi_zhu'])), ['zhi_sheng', 'min_zi_zhu']);
  // 番禺电脑抽签 → single_paidui（初中番禺同口径）
  assert.deepEqual(mechsOf(primaryBy('440113', /番禺区小升初对口（电脑抽签）/, ['single_paidui'])), ['single_paidui']);
  // 番禺市桥城区 → group_paidui
  assert.deepEqual(mechsOf(primaryBy('440113', /番禺区小升初对口（市桥城区电脑派位（多校））/, ['group_paidui'])), ['group_paidui']);
  // 缺口组无徽章
  assert.deepEqual(mechsOf(primaryBy('440111', /不参与公办派位/, [])), []);
});

test('label 与初中机制文案一致', () => {
  for (const k of Object.keys(MIDDLE_MECH_LABELS)) {
    assert.equal(XS_MECH_LABELS[k], MIDDLE_MECH_LABELS[k], `${k} label 应与初中一致`);
  }
});

test('全量：所有小学 mechanisms 合法、有序、有 label；dist group 机制完整', () => {
  const legal = new Set(Object.keys(MIDDLE_MECH_LABELS));
  let checked = 0;
  for (const p of loaders.primarySchools.schools) {
    if (!p.school_id) continue;
    const m = buildDetailModel('primary', p.name, repo, p.school_id);
    if (!m.feedJuniors) continue;
    checked += 1;
    const mechs = m.feedJuniors.mechanisms || [];
    for (const k of mechs) {
      assert.ok(legal.has(k), `非法机制枚举 ${k}（${p.name}）`);
      assert.ok(XS_MECH_LABELS[k], `缺少 label ${k}（${p.name}）`);
    }
    // 顺序对齐初中 MECH_ORDER
    const sorted = MECH_ORDER.filter((m) => mechs.includes(m));
    assert.deepEqual(mechs, sorted, `机制顺序应对齐初中 MECH_ORDER（${p.name}: ${mechs}）`);
  }
  assert.ok(checked > 100, `应覆盖大量小学，实际 ${checked}`);
  // dist 层：groups 均携带合法 mechanism（数据层固化的入口）
  const dist = loaders.xiaoshengchu;
  for (const g of dist.groups) {
    for (const k of g.mechanism || []) {
      assert.ok(legal.has(k), `dist group 非法机制 ${k}（${g.name}）`);
    }
  }
  // 初中反推覆盖抽查：from_middle 五区记录级机制与 dist 记录级 mechanism 完全一致（dist 以初中反推为准）
  for (const d of ['baiyun', 'haizhu', 'huangpu', 'liwan', 'yuexiu']) {
    const fm = load(`primary/transition/parsed/xiaoshengchu_from_middle_${d}_2026.json`);
    for (const r of fm.records) {
      if (!(r.mechanisms || []).length) continue;
      const rec = dist.records.find((x) => x.school_id === r.school_id);
      assert.ok(rec, `from_middle 小学应在 dist 有记录（${r.name}）`);
      assert.deepEqual(
        MECH_ORDER.filter((m) => (rec.mechanism || []).includes(m)),
        MECH_ORDER.filter((m) => r.mechanisms.includes(m)),
        `dist 记录级机制应与初中反推一致（${r.name}）`,
      );
    }
  }
});
