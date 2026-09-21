/**
 * 详情模型回归：Web 与小程序都必须只渲染 buildDetailModel 的结果。
 * 选取小学/初中/高中各一例，固定跨学部、招生、升学路线和录取线的关键契约。
 */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const { createRepository, buildDetailModel, buildLinkageModel, normName } = require('../dist/cjs/index.js');
const ROOT = path.resolve(__dirname, '../../..');
const load = (file) => JSON.parse(fs.readFileSync(path.join(ROOT, 'data', file), 'utf8'));
const loaders = {
  primarySchools: load('poi/dist/primary_poi.json'),
  primaryTier1: load('primary/tier1_schools_all.json'),
  middleSchools: load('poi/dist/middle_poi.json'),
  middleTier1: load('middle/tier1_schools_all.json'),
  highSchools: load('poi/dist/high_poi.json'),
  highLevels: load('high/level/src/levels.json'),
  enrollments: ['tianhe', 'yuexiu', 'haizhu', 'liwan', 'panyu', 'baiyun', 'huangpu'].map((d) => load(`primary/enrollments/2026-${d}.json`)),
  quotaMatrix: load('linkage/quota_matrix.json'),
  specialMatrix: load('linkage/special_matrix.json'),
  batch2Scores: load('linkage/batch2_scores.json'),
  districtQuota: load('linkage/district_quota.json'),
  highScores2025: load('high/cutoff_score/dist/scores_2025.json'),
  highScores2026: load('high/cutoff_score/dist/scores_2026.json'),
  entities: load('registry/entity/dist/entities.json'),
  xiaoshengchu: load('primary/xiaoshengchu_2026.json'),
  sites: load('registry/entity/dist/sites.json'),
  brandGroups: load('registry/group/src/brand_groups.json'),
  educationGroups: load('registry/group/dist/education_groups.json'),
  schoolGroups: load('registry/group/dist/school_groups.json'),
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

test('第一批高中详情计划数按 school_id 反查（自主/体育/艺术），实体名可命中官方计划', () => {
  const special = loaders.specialMatrix;
  // 1) 自主招生计划：官方原文"（校本部）"与实体"（本部校区）"名称差异已在构建期归一 → 实体名反查命中
  const zg = repo.entities.find((e) => e.name === '广州市真光中学(本部校区)');
  assert.ok(zg, '需要真光本部校区实体');
  const m1 = buildLinkageModel('high', zg.name, repo, zg.school_id);
  assert.equal(m1.autonomyPlan, 70, '真光本部自主招生计划=70');
  assert.equal(m1.sportsPlan, 40, '真光本部体育特长生计划=40');
  assert.equal(m1.artsPlan, 24, '真光本部艺术特长生计划=24');
  // 项目二级细项（官方明细表逐项，合计必须=计划总数）
  assert.equal(m1.sportsProjects.length, 5, '真光本部体育项目=5 项');
  assert.deepEqual(m1.sportsProjects[0], { project: '男子足球', plan: 10, note: '其中体育后备人才不超2人' });
  assert.equal(m1.sportsProjects.reduce((s, p) => s + p.plan, 0), m1.sportsPlan, '体育项目合计=体育计划数');
  assert.equal(m1.artsProjects.length, 2, '真光本部艺术项目=2 项');
  assert.equal(m1.artsProjects.reduce((s, p) => s + p.plan, 0), m1.artsPlan, '艺术项目合计=艺术计划数');
  // 备注类型：真光本部体育含"体育后备人才"上限备注 → 前端条件显示解释
  assert.deepEqual(m1.planNotes, ['reserve'], '真光本部 planNotes 应含 reserve');
  // 2) 特长生计划按 school_id 反查（铁一越秀）
  const ty = repo.entities.find((e) => e.name === '广州市铁一中学(越秀校区)');
  assert.ok(ty);
  const m2 = buildLinkageModel('high', ty.name, repo, ty.school_id);
  assert.equal(m2.autonomyPlan, 33, '铁一越秀自主招生计划=33');
  assert.equal(m2.sportsPlan, 10, '铁一越秀体育特长生计划=10');
  assert.equal(m2.artsPlan, 35, '铁一越秀艺术特长生计划=35');
  // 3) 官方无特长生计划的校区返回 null（不得误显示 0）
  const fs = repo.entities.find((e) => e.name === '广州市真光中学(汾水校区)');
  assert.ok(fs);
  const m3 = buildLinkageModel('high', fs.name, repo, fs.school_id);
  assert.equal(m3.autonomyPlan, 17, '真光汾水自主招生计划=17');
  assert.equal(m3.sportsPlan, null, '真光汾水无特长生计划 → null');
  assert.equal(m3.artsPlan, null);
  assert.equal(m3.sportsProjects, null, '无特长生计划 → 项目明细 null');
  assert.equal(m3.artsProjects, null);
  assert.deepEqual(m3.planNotes, [], '无特长生计划 → 备注类型空');

  // 6) 领军龙足球试点单列：华附石牌 planNotes 含 lingjun → 前端条件显示领军龙解释
  const hf = repo.entities.find((e) => e.name === '华南师范大学附属中学(石牌校区)');
  assert.ok(hf, '需要华附石牌实体');
  const m4 = buildLinkageModel('high', hf.name, repo, hf.school_id);
  assert.ok(m4.planNotes.includes('lingjun'), '华附石牌为领军龙试点 → planNotes 含 lingjun');
  // 4) 特长生计划总量 = 官方口径（体育 1905 不含领军龙 / 艺术 1741 / 领军龙 116）
  assert.equal(special.special_plan_summary.sports, 1905);
  assert.equal(special.special_plan_summary.arts, 1741);
  assert.equal(special.special_plan_summary.football_special, 116);
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
  // 2026-09-16 法人多校区治理后为 58：merge_groups 对 education core_poi 做法人推导补全
  // （matchNorm(coreCampusName) 归并全部校区），华阳小学/真光等校区改由 education 索引命中
  // （education 优先），品牌卡归属更准确（教育集团 core_poi 全校区可见）。
  // 2026-09-17 校区办学联网核实后为 57：41中东/盘福等 9 所校区 stage 修正（middle→high/primary，
  // 见 CAMPUS_STAGE_FIX，campus_middle_webverify_20260917.md），学段变更后不再计入 brand 覆盖
  //（详情页按正确学段渲染品牌卡）。
  // 2026-09-21 后缀式校区统一归并 + 锚点表瘦身（55→4）后为 55：
  //   a) 省实荔湾花地湾 2 校区（花地湾校区 + 小学部）由 brand/广东实验中学教育集团 转入
  //      education/广东实验中学荔湾学校教育集团（法人推导补全 core_poi 后 education 索引优先），
  //      归属更准确，不再计入 brand 覆盖（-2）；
  //   b) 后缀式校区统一规则（school_match.legalCampuses「<法人><校区名>校区」前缀归并）另使
  //      12 个后缀式校区进入 education 覆盖（+12，见 school_groups 增量），brand 覆盖不受影响。
  assert.equal(eligible.length, 55, '品牌实体覆盖范围变更，请审阅当前态回归结果');
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

test('品牌关联：education 多校区成员平铺每校区一行，各自带学段 Badge 与 school_id 跳转（侨乐小学回归）', () => {
  // 侨乐小学：华阳教育集团成员，双校区 campuses（poi_name/school_id 为空）——2026-09-18 修复前
  // 该行 stages=[] 导致「小学」Badge 缺失；修复后平铺为两行、各自独立跳转。
  const cases = [
    { name: '天河区侨乐小学', schoolId: 'gz-440106-3332b6cb' },
    { name: '广州华阳集团侨乐小学(北校区)', schoolId: 'gz-440106-95cb8bc4' },
  ];
  for (const c of cases) {
    const model = buildDetailModel('primary', c.name, repo, c.schoolId);
    assert.ok(model.brandCard, `${c.name}: 必须渲染品牌关联`);
    const rows = model.brandCard.groups.flatMap((g) => g.rows);
    const mine = rows.filter((r) => r.name === c.name);
    assert.equal(mine.length, 1, `${c.name}: 平铺为独立一行`);
    assert.ok(mine[0].stages.includes('小学'), `${c.name}: 应有「小学」学段 Badge（stages=${JSON.stringify(mine[0].stages)}）`);
    assert.ok(mine[0].link && mine[0].link.includes(`id=${c.schoolId}`), `${c.name}: 链接应携带本校区 school_id`);
    assert.equal(mine[0].isCurrent, true, `${c.name}: 当前查看校区行应标记 isCurrent`);
    // 兄弟校区行独立存在且不误标当前
    const sibling = cases.find((x) => x.schoolId !== c.schoolId);
    const other = rows.filter((r) => r.name === sibling.name);
    assert.equal(other.length, 1, `${c.name}: 兄弟校区也应平铺为一行`);
    assert.equal(other[0].isCurrent, false, `${c.name}: 兄弟校区行不应标记 isCurrent`);
  }
});

test('品牌关联：education 成员 school_id 外键补学段 Badge（黄埔铁英初中部回归）', () => {
  // 黄埔铁英 = 广铁一中教育集团托管成员（独立法人），brand 单位含中学+小学两个实体外键
  // （gz-440112-c80ac6ac / gz-440112-adb9c303）。merge_groups 并入 education 源后此前只保留
  // 首 id 且 poi_name 为空 → education 分支 POI 名联查失败 → 初中/小学 Badge 全部消失（2026-09-20）。
  // 修复：merge 保留完整 school_ids，education 分支按实体学段兜底补 Badge。
  const m = buildDetailModel('middle', '广铁一中铁英中学', repo, 'gz-440112-c80ac6ac');
  assert.ok(m.brandCard, '铁英中学详情页必须渲染品牌关联');
  const rows = m.brandCard.groups.flatMap((g) => g.rows);
  const hp = rows.find((r) => r.name === '广州市黄埔区铁英学校（黄埔铁英）');
  assert.ok(hp, '铁英中学详情页品牌卡应含黄埔铁英行');
  assert.ok(hp.stages.includes('初中'), `黄埔铁英行应有「初中」Badge（stages=${JSON.stringify(hp.stages)}）`);
  assert.ok(hp.stages.includes('小学'), `黄埔铁英为九年一贯，还应有「小学」Badge（stages=${JSON.stringify(hp.stages)}）`);
  assert.equal(hp.isCurrent, true, '铁英中学详情页当前行应标记 isCurrent');
  assert.ok(hp.link && hp.link.includes('id=gz-440112-c80ac6ac'), '黄埔铁英行链接应携带初中 school_id');
});

test('品牌关联：7 区外远郊成员不可点击跳转（南沙铁英回归）', () => {
  // 南沙铁英在 7 区范围外（无实体无 POI，merge 标注「远郊不在POI范围」）。
  // 修复前 education 分支对任意非空成员名生成链接 → 点击落入空详情页（availableStages=[]）；
  // 修复：无外键且名不可解析的成员只作信息行（link=null）。
  const m = buildDetailModel('middle', '广铁一中铁英中学', repo, 'gz-440112-c80ac6ac');
  const rows = m.brandCard.groups.flatMap((g) => g.rows);
  const ns = rows.find((r) => r.name === '广州市南沙区铁英学校');
  assert.ok(ns, '品牌卡应保留南沙铁英信息行（铁一官网「1+3」托管口径）');
  assert.equal(ns.link, null, '南沙铁英无实体无 POI，不得生成可点击跳转');
});

test('法人多校区：官方升学文件一个名称对应多个 school_id，聚合展示分别跳转', () => {
  // 一一三中法人行：2 个 middle 校区（乐学/东方）；金融城/元岗为纯高中（NON_MIDDLE，
  // 2026-09-17 联网核实 campus_middle_webverify_20260917.md）
  const row = loaders.quotaMatrix.schools.find((s) => s.school === '广州市第一一三中学');
  assert.ok(row, 'quota 应有广州市第一一三中学法人行');
  assert.equal(row.school_ids.length, 2, '法人行应挂 2 个 middle 校区 school_id');
  const model = buildLinkageModel('middle', '广州市第一一三中学', repo, row.school_id);
  assert.equal(model.quota?.sheng_quota != null, true, '法人级配额应可展示');
  assert.equal(model.campuses.length, 2, '升学信息应聚合 2 个校区');
  for (const c of model.campuses) {
    assert.ok(c.poiName, '每个校区都应能跳转各自详情页');
    const e = repo.entities.find((x) => x.school_id === c.schoolId);
    assert.ok(e, '校区 school_id 必须存在实体');
    assert.equal(c.campus, e.name, '校区跳转目标 = 实体 POI 名（1 id ↔ 1 详情页 ↔ 1 POI）');
  }
});

test('法人多校区：从任一校区 POI 进入都能命中法人升学数据', () => {
  const campusEntity = repo.entities.find((e) => e.school_id === 'gz-440106-b049d65a'); // 东方校区（初中部）
  assert.ok(campusEntity, '应存在一一三中东方校区实体');
  const model = buildLinkageModel('middle', campusEntity.name, repo, campusEntity.school_id);
  assert.ok(model.quota, '校区 POI 应归并到法人行展示升学数据');
  assert.equal(model.campuses.length, 2, '聚合展示法人全部 middle 校区');
  // 无 school_id 纯名进入（搜索/反查场景）也应命中
  const byName = buildLinkageModel('middle', '广州市第一一三中学(东方校区)', repo, null);
  assert.ok(byName.quota, '纯名进入也应命中法人行');
});

test('法人多校区：高中覆盖反查行聚合法人全部校区', () => {
  const model = buildLinkageModel('high', '华南师范大学附属中学（石牌校区）', repo, null);
  const row = model.highCoverage.find((r) => r.school === '广州市第一一三中学');
  assert.ok(row, '省市属高中覆盖反查应含一一三中法人行');
  assert.equal(row.campuses.length, 2, '覆盖行应聚合法人 2 个 middle 校区');
  assert.ok(row.campuses.every((c) => c.poiName), '覆盖行各校区均可跳转');
});

test('品牌关联全量回归：法人组成员校区详情页品牌卡不得消失（快照显式更新）', () => {
  // 判定「应有品牌卡」：实体法人 core（去括号校区+区名归一）∈ 任一组 core/成员名/brand units 名
  // （与 scripts/merge_groups.py legal_campuses 同语义）。任何改动导致品牌模块从详情页
  // 消失/未渲染（null 或 useful=false），本测试立即失败——快照 digest 强制显式更新。
  const edu = load('registry/group/dist/education_groups.json').groups;
  const brand = (load('registry/group/src/brand_groups.json').groups || []);
  const coreOf = (n) => (n || '').replace(/[（(][^）)]*[）)]/g, '').trim();
  const nrm = (s) => s.replace(/[（(]/g, '').replace(/[）)]/g, '').replace(/广州市/g, '').replace(/\s/g, '');
  const grpKeys = new Set();
  for (const g of edu) {
    for (const c of g.core || []) grpKeys.add(nrm(coreOf(c)));
    for (const m of g.members || []) grpKeys.add(nrm(coreOf(m.name)));
  }
  for (const g of brand) {
    for (const u of g.units || []) grpKeys.add(nrm(coreOf(u.name)));
  }
  const miss = [];
  const shown = [];
  for (const e of repo.entities) {
    if (!grpKeys.has(nrm(coreOf(e.name)))) continue;
    const m = buildDetailModel(e.stage, e.name, repo, e.school_id);
    shown.push(`${e.school_id}|${m.brandCard ? m.brandCard.brand : ''}|${m.brandCardUseful}`);
    if (!m.brandCard) { miss.push(`${e.name} 品牌卡为 null`); continue; }
    // 组内有非当前成员行（真增量信息）时必须渲染（useful）
    if (!m.brandCardUseful && m.brandCard.groups.some((g) => g.rows.some((r) => !r.isCurrent))) {
      miss.push(`${e.name} 有非当前成员行但 useful=false`);
    }
    // 行级不变量：可点击行必须有学段 Badge（有外键实体或有 POI 命中）；
    // 无外键且名不可解析的 7 区外/建设中成员必须不可点击（防空跳详情页，南沙铁英回归）
    for (const g of m.brandCard.groups) {
      for (const r of g.rows) {
        if (r.link && r.stages.length === 0) miss.push(`${e.name} 品牌卡行「${r.name}」有链接但无学段 Badge`);
      }
    }
  }
  assert.deepEqual(miss, [], `品牌卡消失/未渲染: ${miss.join('; ')}`);
  // 快照：渲染中的品牌卡名单 digest（brandCardUseful=true 实体）
  const digest = crypto
    .createHash('sha256')
    .update(shown.filter((s) => s.endsWith('|true')).sort().join('\n'))
    .digest('hex')
    .slice(0, 16);
  // 2026-09-17 同址冗余合并（build_entities DROP_CAMPUS：省实荔湾初中部一期、十三中初中部、
  // 柯子岭43号A座）后更新：品牌卡渲染名单随实体合并变化（无品牌卡消失，miss 为空）
  // 2026-09-18 奥林匹克修复+高中学段判定重构：智谷 high 实体消失、8 所已核实高中校区 stage 修正
  // 随实体表/POI 表联动（无品牌卡消失，miss 为空）——有意变更
    // 2026-09-18 南武教育集团入册（海珠区教育局2023-12-27调整通知）：新增12条品牌卡渲染（南武中学三校区/江南外国语南北/南二实南北/南武实验/文润/附属/南武小学北/南武实验小学），REMOVED=0，无品牌卡消失——有意变更
    // 2026-09-18 番禺仲元附属加入仲元集团（官方2024-12仍属成员校）：附属学校品牌卡主归属仲元集团（多集团展示逻辑不变），ADDED=0 REMOVED=0——有意变更
  assert.equal(digest, 'd99c4422556d3656', '品牌关联全量快照漂移：有实体的品牌卡渲染状态变化，需显式确认后更新');
});

test('品牌关联：逐集团学校名单快照（education 86 + brand 8，集团变化精确定位）', () => {
  // 每个集团独立快照（school_id 名单）于 snapshots/group_roster.json：core_poi + members
  // 及成员 campuses（brand 为 units[].school_ids）。任一集团名单增删 → 该集团断言失败并打印
  // 增/删明细，可精确定位到集团。2026-09-21 后缀式校区统一归并（school_match.legalCampuses）
  // 后初建：东风东+2（天伦/锦城花园）、沙面+2（岭南/悦江）、六十五中+1（桃园）、宝玉直+1（宝贤）、
  // 西关外国语+1（文昌南）等 12 个后缀式校区进入 education 名单，均由本快照感知。
  // 更新快照：重跑「node -e 生成逻辑」（与 collectEdu/collectBrand 一致，见 git 历史）。
  const snap = JSON.parse(fs.readFileSync(path.join(__dirname, 'snapshots/group_roster.json'), 'utf8'));
  const edu = load('registry/group/dist/education_groups.json').groups;
  const brand = (load('registry/group/src/brand_groups.json').brands || []);
  const collectEdu = (g) => {
    const ids = new Set();
    for (const p of g.core_poi || []) if (p.school_id) ids.add(p.school_id);
    for (const m of g.members || []) {
      if (m.school_id) ids.add(m.school_id);
      for (const c of m.campuses || []) if (c.school_id) ids.add(c.school_id);
    }
    return [...ids].sort();
  };
  const collectBrand = (b) => {
    const ids = new Set();
    for (const u of b.units || []) for (const sid of u.school_ids || []) if (sid) ids.add(sid);
    return [...ids].sort();
  };
  const cur = new Map();
  for (const g of edu) cur.set(`edu|${g.brand}`, collectEdu(g));
  for (const b of brand) cur.set(`brand|${b.brand}`, collectBrand(b));
  const diffs = [];
  for (const [key, ids] of cur) {
    const nm = key.slice(key.indexOf('|') + 1);
    const prev = key.startsWith('edu|') ? snap.education[nm] : snap.brand[nm];
    if (!prev) { diffs.push(`${key}: 快照无此集团（新增集团）`); continue; }
    const added = ids.filter((x) => !prev.includes(x));
    const removed = prev.filter((x) => !ids.includes(x));
    if (added.length || removed.length) diffs.push(`${key}: 新增[${added.join(',')}] 移除[${removed.join(',')}]`);
  }
  for (const [sec, map] of [['edu', snap.education], ['brand', snap.brand]]) {
    for (const nm of Object.keys(map)) {
      if (!cur.has(`${sec}|${nm}`)) diffs.push(`${sec}|${nm}: 集团已消失`);
    }
  }
  assert.deepEqual(diffs, [], `集团名单快照漂移（${diffs.length} 处）：\n${diffs.join('\n')}`);

  // 名单闭环：名单内 school_id 实体存在、schoolGroups 映射无孤儿。一个实体可属多个集团
  //（如东山培正小学=东山培正集团核心+培正集团成员、黄石学校=白云中学集团+培英集团成员、
  // 仲元附属学校=仲元附属集团核心+仲元中学集团成员），schoolGroups 仅存一条映射，
  // 故 edu 映射允许为该实体所属的任一集团；brand 单归属实体必须映射回品牌（edu 收录时 education 优先）。
  const sg = load('registry/group/dist/school_groups.json').schoolGroups;
  const entById = new Map(repo.entities.map((e) => [e.school_id, e]));
  const belongsTo = new Map(); // sid -> Set(所属集团名，含 edu + brand)
  for (const [key, ids] of cur) {
    const nm = key.slice(key.indexOf('|') + 1);
    for (const sid of ids) {
      if (!belongsTo.has(sid)) belongsTo.set(sid, new Set());
      belongsTo.get(sid).add(nm);
    }
  }
  const problems = [];
  for (const [key, ids] of cur) {
    const nm = key.slice(key.indexOf('|') + 1);
    const isEdu = key.startsWith('edu|');
    for (const sid of ids) {
      const e = entById.get(sid);
      if (!e) { problems.push(`${key}: ${sid} 无实体`); continue; }
      const g = sg[sid];
      if (!g) { problems.push(`${key}: ${e.name}(${sid}) 不在 schoolGroups 映射`); continue; }
      const owned = belongsTo.get(sid) || new Set();
      if (isEdu && !owned.has(g.brand)) problems.push(`${key}: ${e.name}(${sid}) 映射到 ${g.brand}（不属于 ${[...owned].join('/')}）`);
      if (!isEdu && !owned.has(g.brand)) problems.push(`${key}: ${e.name}(${sid}) 映射到 ${g.brand}（不属于 ${[...owned].join('/')}）`);
      const m = buildDetailModel(e.stage, e.name, repo, sid);
      if (!m.brandCard) problems.push(`${key}: ${e.name}(${sid}) 品牌卡未渲染`);
    }
  }
  assert.deepEqual(problems, [], `集团名单闭环问题（${problems.length} 处）：\n${problems.join('\n')}`);
});

test('品牌关联：校区+学部复合名实体归属教育集团（奥体小学部品牌卡）', () => {
  // 回归：merge_groups legal_campuses 剥学部后缀后，「广州奥林匹克中学（智谷校区）小学部」
  // 归入奥林匹克教育集团 core_poi → 小学部详情页显示品牌卡（核心校多校区平铺）
  const ent = repo.entities.find((e) => e.school_id === 'gz-440106-a7cac9ec');
  assert.ok(ent, '小学部实体应存在');
  const m = buildDetailModel('primary', ent.name, repo, ent.school_id);
  assert.equal(m.brandCard?.brand, '奥林匹克教育集团', '小学部应命中教育集团');
  assert.equal(m.brandCardUseful, true, '核心校有非当前成员行时应渲染');
  const coreRows = m.brandCard.groups.find((g) => g.key === 'core').rows;
  const names = coreRows.map((r) => r.name);
  for (const expect of ['广州奥林匹克中学（智谷校区）小学部', '广州市奥林匹克中学(黄村西路校区)', '广州奥林匹克中学(智谷校区)', '广州奥林匹克中学(高中部)']) {
    assert.ok(names.includes(expect), `核心校应含 ${expect}（实际: ${names.join(' / ')}）`);
  }
  const cur = coreRows.find((r) => r.isCurrent);
  assert.ok(cur && cur.stages.includes('小学'), '当前行应为小学部且学段含小学');
});

test('高中徽章/信息行：省市属·区属官方口径 + 区属不带区名', () => {
  // 回归：徽章对应指标到校批次（省市属面向全市/区属面向本区），不再误标「省示范/市示范」；
  // 信息行隶属区属统一「区属」（不带区名），省市属保留细粒度省属/市属
  const target = repo.entities.find((e) => e.name.includes('天河中学') && e.stage === 'high');
  assert.ok(target, '天河中学高中实体应存在');
  const m = buildDetailModel('high', target.name, repo, target.school_id);
  const texts = m.badges.map((b) => b.text);
  assert.ok(texts.includes('区属'), `天河中学区属徽章应含「区属」（实际: ${texts.join('·')}）`);
  assert.ok(!texts.some((t) => t.includes('市示范')), '不应再出现「市示范」徽章');
  assert.ok(!texts.some((t) => t.includes('省示范')), '不应再出现「省示范」徽章');
  assert.ok(m.headText.includes('国家级示范性'), '信息行应保留示范等级（国家级示范性）');
  assert.ok(m.headText.includes('区属') && !m.headText.includes('天河区属') && !m.headText.includes('天河区区属'), '信息行隶属应归一为「区属」不带区名');
  // 省市属学校（华附）徽章为「省市属」
  const hf = repo.entities.find((e) => e.name.includes('华南师范大学附属中学') && e.stage === 'high');
  const m2 = buildDetailModel('high', hf.name, repo, hf.school_id);
  const t2 = m2.badges.map((b) => b.text);
  assert.ok(t2.includes('省市属'), `省市属学校徽章应含「省市属」（实际: ${t2.join('·')}）`);
  assert.ok(m2.headText.includes('省属'), '省市属信息行应保留细粒度「省属」');
});

test('品牌关联：多校区成员通名打开不再全行选中（陶育实验学校）', () => {
  // 回归：education 分支 isCurrent 第三条用成员通名 m.name 匹配，多校区成员（campuses 非空）
  // 所有行共享通名 → 通名打开详情页（如搜索「广州市第一一三中学陶育实验学校」进初中 tab）
  // 小学部与暨南校区两行都被选中。修复：仅单校区成员允许通名兜底选中。
  const rowsOf = (stage, name, id) => {
    const m = buildDetailModel(stage, name, repo, id);
    return (m.brandCard?.groups || []).flatMap((g) => g.rows).filter((r) => r.name.includes('陶育'));
  };
  // 1. 通名打开：任何一行都不应选中（通名是聚合入口，不代表具体校区）
  const agg = rowsOf('middle', '广州市第一一三中学陶育实验学校');
  assert.equal(agg.length, 2, '陶育成员应平铺两校区');
  assert.ok(agg.every((r) => !r.isCurrent), '通名打开不应选中任何校区行');
  // 2. 小学部详情页只选小学部
  const px = rowsOf('primary', '广州市第一一三中学陶育实验学校小学部', 'gz-440106-35cad4e6');
  assert.equal(px.find((r) => r.name.includes('小学部'))?.isCurrent, true, '小学部详情页应选中小学部行');
  assert.equal(px.find((r) => r.name.includes('暨南校区'))?.isCurrent, false, '小学部详情页不应选中初中部行');
  // 3. 初中部（暨南校区）详情页只选初中部
  const jn = rowsOf('middle', '广州市第一一三中学陶育实验学校(暨南校区)', 'gz-440106-7c81ab92');
  assert.equal(jn.find((r) => r.name.includes('暨南校区'))?.isCurrent, true, '初中部详情页应选中暨南校区行');
  assert.equal(jn.find((r) => r.name.includes('小学部'))?.isCurrent, false, '初中部详情页不应选中小学部行');
});
