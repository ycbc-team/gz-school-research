/**
 * 初中升学信号明细（移植自 web RankingView.vue，纯逻辑、无平台依赖）。
 * 输入 loaders：rankingMiddle(已 hydrate 的 schools 数组) / quotaMatrix(已 hydrate) /
 * quotaOutcome / middleEnrollments / middleEnrollmentMechanisms / entities / civilizedCampusSchoolIds。
 * 输出：按行政区归类的分组表格数据，列随「指标」切换（3 列 / 5 列横滑）。
 */
const DISTRICT_NAME = {
  '440103': '荔湾', '440104': '越秀', '440105': '海珠', '440106': '天河',
  '440111': '白云', '440112': '黄埔', '440113': '番禺', '440114': '花都',
  '440117': '从化', '440118': '增城', '440115': '南沙', '440100': '市属',
};
const DISTRICT_ORDER = ['荔湾', '越秀', '海珠', '天河', '白云', '黄埔', '番禺'];
const CIVILIZED_FILTERS = [
  ['national', '全国文明校园'],
  ['provincial', '广东省文明校园'],
  ['municipal', '广州市文明校园'],
  ['advanced', '创建先进学校（储备）'],
  ['other', '其他'],
];
const MECH_FILTER_ORDER = [
  'single_zone', 'zhi_sheng', 'group_paidui', 'single_paidui',
  'single_chouqian', 'min_zi_zhu', 'no_plan',
];

function shortName(name) {
  const n = (name || '').trim();
  if (n.startsWith('广州市')) return n.slice(3);
  if (n.startsWith('广东')) return n.slice(2);
  if (n.startsWith('广州')) {
    const rest = n.slice(2);
    if (rest.length >= 3 && !rest.startsWith('大学')) return rest;
  }
  return n;
}

function fmtRatio(v) { return v == null ? '—' : `${v.toFixed(1)}%`; }
function fmtInt(v) { return v == null ? '—' : String(v); }
function fmtAvg(v) { return v == null ? '—' : v.toFixed(1); }
function fmtWaste(v) { return v == null ? '—' : `${(v * 100).toFixed(1)}%`; }

function districtFull(sid) {
  if (sid) return DISTRICT_NAME[sid.slice(3, 9)] || '其他';
  return null;
}
// 归一化行政区名：quota 等源偶带尾随「区」（如 "海珠区"），统一剥掉，保证 "海珠"/"荔湾"/"市属"/"其他" 一致，
// 否则同一区会被拆成两组（"海珠" 与 "海珠区"）且标题出现 "海珠区区"。
function normDistrict(d) {
  if (!d || d === '其他') return d || '其他';
  return d.replace(/区$/, '');
}

/** 单行指标取值（null=无数据，排序置后；户口生为 0 时比例无意义，返回 null 避免出现 NaN%） */
function metricValue(s, metric) {
  const k = s.kaosheng != null && s.kaosheng > 0 ? s.kaosheng : null;
  switch (metric) {
    case 'default':
    case 'qu_ratio': return k != null && s.qu_quota != null ? (s.qu_quota / k) * 100 : null;
    case 'sheng_ratio': return k != null && s.sheng_quota != null ? (s.sheng_quota / k) * 100 : null;
    case 'tekong': return s.tekong_quota_rate != null ? s.tekong_quota_rate : null;
    case 'sheng_min': return s.sheng_min_score != null ? s.sheng_min_score : null;
    case 'qu_min': return s.qu_min_score != null ? s.qu_min_score : null;
    case 'top14_min': return s.top14_min_score != null ? s.top14_min_score : null;
    default: return null;
  }
}

/** 当前指标对应的数值列表表头（不含「学校」列） */
function columnsFor(metric) {
  if (metric === 'tekong') return ['指标×高中特控率', '考生数'];
  if (metric === 'sheng_min' || metric === 'qu_min') return ['最低分', '近3年平均分', '指标数', '浪费率'];
  if (metric === 'top14_min') return ['TOP14最低分', '近3年平均分', '指标数', '浪费率'];
  const ratioLabel = metric === 'sheng_ratio' ? '省市属指标比例' : '区属指标比例';
  const absLabel = metric === 'sheng_ratio' ? '省市属指标数' : '区属指标数';
  return [ratioLabel, absLabel];
}

/** 当前指标下，单行的数值单元格（与 columnsFor 一一对应） */
function cellsFor(s, metric) {
  if (metric === 'tekong') {
    return [fmtRatio(s.tekong_quota_rate), s.kaosheng == null ? '—' : String(s.kaosheng)];
  }
  if (metric === 'sheng_min' || metric === 'qu_min' || metric === 'top14_min') {
    const min3y = metric === 'sheng_min' ? s.sheng_min_3y_avg
      : metric === 'top14_min' ? s.top14_min_3y_avg : s.qu_min_3y_avg;
    const quota = metric === 'sheng_min' ? s.sheng_quota
      : metric === 'top14_min' ? s.top14_quota : s.qu_quota;
    const waste = metric === 'sheng_min' ? s.sheng_waste_rate
      : metric === 'top14_min' ? s.top14_waste_rate : s.qu_waste_rate;
    const minScore = metric === 'top14_min' ? s.top14_min_score
      : metric === 'sheng_min' ? s.sheng_min_score : s.qu_min_score;
    return [fmtInt(minScore), fmtAvg(min3y), fmtInt(quota), fmtWaste(waste)];
  }
  const v = metricValue(s, metric);
  const abs = metric === 'sheng_ratio' ? s.sheng_quota : s.qu_quota;
  return [fmtRatio(v), fmtInt(abs)];
}

function buildRows(loaders) {
  const { rankingMiddle, quotaMatrix, quotaOutcome, entities, civilizedCampusSchoolIds } = loaders;
  const NAME_BY_ID = new Map();
  for (const [name, id] of Object.entries(quotaMatrix.name_index || {})) {
    if (!NAME_BY_ID.has(id)) NAME_BY_ID.set(id, []);
    NAME_BY_ID.get(id).push(name);
  }
  const QUOTA_BY_ID = new Map();
  for (const q of (quotaMatrix.ids || [])) {
    if (!QUOTA_BY_ID.has(q.school_id)) QUOTA_BY_ID.set(q.school_id, []);
    QUOTA_BY_ID.get(q.school_id).push(q);
  }
  const QUOTA_BY_NAME = new Map((quotaMatrix.schools || []).map((q) => [q.school, q]));
  const OUTCOME_BY_ID = new Map(Object.entries(quotaOutcome.ids || {}));
  const OUTCOME_BY_NAME = new Map(Object.entries(quotaOutcome.schools || {}));
  const MINBAN_IDS = new Set(
    (entities.entities || []).filter((e) => e.nature === '民办').map((e) => e.school_id),
  );
  const QUOTA_POS = new Map();
  const NAME_POS = new Map();
  const rows = (rankingMiddle.schools || []).map((r) => {
    const id = r.school_id || '';
    const qpos = QUOTA_POS.get(id) || 0;
    const q = id ? (QUOTA_BY_ID.get(id) || [])[qpos] : undefined;
    if (id) QUOTA_POS.set(id, qpos + 1);
    const npos = NAME_POS.get(id) || 0;
    const name = id ? (NAME_BY_ID.get(id) || [])[npos] || r.name || '' : r.name || '';
    if (id) NAME_POS.set(id, npos + 1);
    const nameRow = id ? undefined : QUOTA_BY_NAME.get(name);
    const oc = id ? OUTCOME_BY_ID.get(id) : OUTCOME_BY_NAME.get(name);
    const sid = id && id.length >= 9 ? id : null;
    return {
      name,
      school_id: id,
      school_ids: r.school_ids ? r.school_ids.filter((x) => !!x) : null,
      district: normDistrict(districtFull(sid) || q?.district || nameRow?.district || '其他'),
      minban: !!id && MINBAN_IDS.has(id),
      kaosheng: q?.kaosheng != null ? q.kaosheng : (nameRow?.kaosheng != null ? nameRow.kaosheng : null),
      sheng_quota: q?.sheng_quota != null ? q.sheng_quota : (nameRow?.sheng_quota != null ? nameRow.sheng_quota : null),
      qu_quota: q?.qu_quota != null ? q.qu_quota : (nameRow?.qu_quota != null ? nameRow.qu_quota : null),
      sheng_min_score: oc?.sheng_min_score != null ? oc.sheng_min_score : null,
      qu_min_score: oc?.qu_min_score != null ? oc.qu_min_score : null,
      top14_min_score: oc?.top14_min_score != null ? oc.top14_min_score : null,
      top14_min_3y_avg: oc?.top14_min_3y_avg != null ? oc.top14_min_3y_avg : null,
      top14_quota: oc?.top14_quota != null ? oc.top14_quota : null,
      top14_waste_rate: oc?.top14_waste_rate != null ? oc.top14_waste_rate : null,
      sheng_min_3y_avg: oc?.sheng_min_3y_avg != null ? oc.sheng_min_3y_avg : null,
      qu_min_3y_avg: oc?.qu_min_3y_avg != null ? oc.qu_min_3y_avg : null,
      sheng_waste_rate: oc?.sheng_waste_rate != null ? oc.sheng_waste_rate : null,
      qu_waste_rate: oc?.qu_waste_rate != null ? oc.qu_waste_rate : null,
      autonomy_count: r.autonomy_count || 0,
      tekong_quota_rate: r.tekong_quota_rate != null ? r.tekong_quota_rate : null,
    };
  });

  // 默认态必须展示「全部学校」：rankingMiddle 只覆盖有 2026 中考数据/已并校的学校，
  // 新校区、当年无毕业生的学校会整体缺席（七区内约 40 所）。这里用实体表补齐，
  // 指标列全部为 null（渲染成 '—'，排序自然置后），保证列表不漏学校。
  const SEVEN_ADCODES = new Set(
    Object.keys(DISTRICT_NAME).filter((code) => DISTRICT_ORDER.indexOf(DISTRICT_NAME[code]) >= 0),
  );
  const coveredIds = new Set();
  for (const r of rows) {
    if (r.school_id) coveredIds.add(r.school_id);
    for (const id of (r.school_ids || [])) if (id) coveredIds.add(id);
  }
  const seenNames = new Set(rows.map((r) => shortName(r.name)));
  for (const e of (entities.entities || [])) {
    if (e.stage !== 'middle' || !e.school_id) continue;
    const adcode = e.school_id.slice(3, 9);
    if (!SEVEN_ADCODES.has(adcode)) continue;
    if (coveredIds.has(e.school_id)) continue;
    const sn = shortName(e.name);
    if (seenNames.has(sn)) continue;   // 同名校区别名不重复加行
    seenNames.add(sn);
    rows.push({
      name: e.name,
      school_id: e.school_id,
      school_ids: null,
      district: normDistrict(districtFull(e.school_id) || '其他'),
      minban: e.nature === '民办',
      kaosheng: null,
      sheng_quota: null,
      qu_quota: null,
      sheng_min_score: null,
      qu_min_score: null,
      top14_min_score: null,
      top14_min_3y_avg: null,
      top14_quota: null,
      top14_waste_rate: null,
      sheng_min_3y_avg: null,
      qu_min_3y_avg: null,
      sheng_waste_rate: null,
      qu_waste_rate: null,
      autonomy_count: 0,
      tekong_quota_rate: null,
    });
  }

  // 校园荣誉：school_id 命中即记录对应荣誉档
  const civBySchool = new Map();
  for (const [key, ids] of Object.entries(civilizedCampusSchoolIds || {})) {
    for (const id of ids) {
      if (!civBySchool.has(id)) civBySchool.set(id, []);
      civBySchool.get(id).push(key);
    }
  }
  for (const row of rows) {
    const ids = [row.school_id, ...(row.school_ids || [])].filter(Boolean);
    const hits = ids.map((id) => civBySchool.get(id) || []).reduce((a, b) => a.concat(b), []);
    row.civilized = [...new Set(hits)];
  }
  return rows;
}

function buildMechBySchool(middleEnrollments) {
  const MECH = new Map();
  for (const snap of (middleEnrollments || [])) {
    for (const rec of (snap.records || [])) {
      const ids = [rec.school_id, ...(rec.school_ids || [])].filter(Boolean);
      for (const id of ids) {
        if (!MECH.has(id)) MECH.set(id, new Set());
        MECH.get(id).add(rec.mechanism);
      }
    }
  }
  return MECH;
}

/** 招生机制命中任一选中机制即显示 */
function mechVisible(row, selectedMechs, mechBySchool) {
  if (!selectedMechs || selectedMechs === 'all' || (Array.isArray(selectedMechs) && selectedMechs.length === 0)) return true;   // 空选（全不选）→ 展示全部
  const ids = [row.school_id, ...(row.school_ids || [])].filter(Boolean);
  for (const id of ids) {
    const set = mechBySchool.get(id);
    if (!set) continue;
    for (const m of set) if (selectedMechs.indexOf(m) >= 0) return true;
  }
  return false;
}

/** 校园荣誉可见：全选(null)→全部；否则选中档命中即显；'other'＝未命中其余任何档 */
function civilizedVisible(row, selectedCivilized) {
  if (!selectedCivilized || selectedCivilized === 'all' || (Array.isArray(selectedCivilized) && selectedCivilized.length === 0)) return true;   // 空选（全不选）→ 展示全部
  if (selectedCivilized.indexOf('other') >= 0 && (!row.civilized || row.civilized.length === 0)) return true;
  return (row.civilized || []).some((k) => selectedCivilized.indexOf(k) >= 0);
}

function districtVisible(row, selectedDistricts) {
  if (!selectedDistricts || selectedDistricts.length === 0) return true;
  const adcode = row.school_id ? row.school_id.slice(3, 9) : null;
  return selectedDistricts.indexOf(adcode) >= 0;
}

/**
 * 构建初中分组表格。
 * opts: { metric, selectedDistricts:[adcode...]|[], selectedCivilized:[keys]|'all'|null, selectedMechs:[...]|'all'|null, locatedDistrict }
 */
function buildMiddleGroups(loaders, opts) {
  const metric = opts.metric || 'default';
  const rows = buildRows(loaders);
  const mechBySchool = buildMechBySchool(loaders.middleEnrollments);
  const filtered = rows.filter((s) =>
    districtVisible(s, opts.selectedDistricts) &&
    civilizedVisible(s, opts.selectedCivilized) &&
    mechVisible(s, opts.selectedMechs, mechBySchool));

  const asc = metric === 'sheng_min' || metric === 'qu_min' || metric === 'top14_min';
  const sortFn = (a, b) => {
    if (!!a.minban !== !!b.minban) return a.minban ? 1 : -1;
    const av = a.v; const bv = b.v;
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return asc ? av - bv : bv - av;
  };

  const map = new Map();
  for (const s of filtered) {
    const key = s.district;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(s);
  }

  // 区排序：未筛选区域且已定位 → 定位区置顶；其余按固定区序；其余区（花都等）补尾
  const located = opts.locatedDistrict;
  const orderIndex = (d) => {
    const i = DISTRICT_ORDER.indexOf(d);
    if (located && d === located) return -1;
    return i < 0 ? 99 : i;
  };
  const keys = [...map.keys()].sort((a, b) => orderIndex(a) - orderIndex(b));

  const columns = columnsFor(metric);
  const groups = keys.map((k) => {
    const items = map.get(k).slice().sort((a, b) => sortFn(
      { minban: a.minban, v: metricValue(a, metric) },
      { minban: b.minban, v: metricValue(b, metric) },
    )).map((s) => ({
      school: shortName(s.name),
      minban: !!s.minban,
      schoolId: s.school_id,
      schoolIds: s.school_ids,
      cells: cellsFor(s, metric),
    }));
    const title = !k ? '其他' : (k === '市属' || k === '其他' ? k : k + '区');
    return { district: k, title, items };
  });
  return { columns, groups };
}

module.exports = {
  buildMiddleGroups,
  columnsFor,
  cellsFor,
  metricValue,
  CIVILIZED_FILTERS,
  MECH_FILTER_ORDER,
  DISTRICT_ORDER,
};
