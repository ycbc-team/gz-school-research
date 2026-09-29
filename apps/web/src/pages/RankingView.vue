<script setup lang="ts">
/**
 * 初中升学信号明细
 * - 数据真源：data/linkage/dist（运行时只消费 id 粒度）——行数据在页面按 canonical 同口径
 *   联表还原：ranking_middle(自招数/特控率) + quota_matrix.name_index/ids(名/区/考生数/省市属·
 *   区属指标) + entities(民办) + groupOfSchool(集团)；无 school_id 原文行按 dist 自带 name
 *   联 quota_matrix.schools 补数值。全量审计见 canonical/ranking_middle.json
 * - 分组：不分组 / 按区（区教育局口径）或按教育集团（@gz/shared groupOfSchool，brand 优先）；可叠加行政区位置筛选
 * - 指标（4 选 1）：默认（机构综合口径，school_id 名单见 data/middle/org_sort/dist/compiled.json，真源 data/middle/org_sort/src/*.json）/ 区属指标比例 / 省市属指标比例 / 指标×高中特控率
 * - 榜单口径：所有比例均以「符合名额分配报考资格考生数（kaosheng）」为分母，
 *   消除学校规模差异（学生多则名额自然多，须看比例）
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { DISTRICTS } from '@gz/shared';
import { rankingMiddle, quotaMatrix, entities, middleOrgSort, civilizedCampusSchoolIds, groupOfSchool, quotaOutcome } from '../data';
import DetailFilterBar from '../components/DetailFilterBar.vue';
import DetailPageHeader from '../components/DetailPageHeader.vue';
import DetailRankingList from '../components/DetailRankingList.vue';

interface Row {
  name: string;
  school_id?: string | null;
  school_ids?: string[] | null;
  district: string;
  minban?: boolean;
  group?: { brand: string; source: 'brand' | 'education' } | null;
  kaosheng?: number | null;
  sheng_quota?: number | null;
  qu_quota?: number | null;
  /** 第二批次指标结果（dist/quota_outcome，id 粒度；py 层聚合，运行时零推断） */
  sheng_min_score?: number | null;
  qu_min_score?: number | null;
  sheng_min_3y_avg?: number | null;
  qu_min_3y_avg?: number | null;
  sheng_waste_rate?: number | null;
  qu_waste_rate?: number | null;
  autonomy_count: number;
  tekong_quota_rate?: number | null;
}

const router = useRouter();

/** dist 行运行时联表还原（口径与 canonical/ranking_middle.json 一致）：
 * - ranking_middle：school_id/school_ids/autonomy_count/tekong_quota_rate
 * - quota_matrix.name_index（官方名→id，构建行序）：反查展示名；同名同 id 多行按出现序配对
 *   （如荔湾东沙博雅/博雅实验学校同实体两行，行序与 canonical 一致）
 * - quota_matrix.ids（同序游标）：district/kaosheng/qu_quota/sheng_quota
 * - quota_matrix.schools：无 school_id 的原文行（dist 自带 name）按名补数值
 * - entities.nature='民办'：minban；groupOfSchool：集团（brand 优先 + education 兜底） */
const NAME_BY_ID = new Map<string, string[]>();
for (const [name, id] of Object.entries(quotaMatrix.name_index)) {
  if (!NAME_BY_ID.has(id)) NAME_BY_ID.set(id, []);
  NAME_BY_ID.get(id)!.push(name);
}
const QUOTA_BY_ID = new Map<string, typeof quotaMatrix.ids>();
for (const q of quotaMatrix.ids) {
  if (!QUOTA_BY_ID.has(q.school_id)) QUOTA_BY_ID.set(q.school_id, []);
  QUOTA_BY_ID.get(q.school_id)!.push(q);
}
const namePos = new Map<string, number>();
const quotaPos = new Map<string, number>();
const MINBAN_IDS = new Set(
  (entities as { entities: Array<{ school_id: string; nature?: string }> }).entities
    .filter((e) => e.nature === '民办')
    .map((e) => e.school_id),
);
const QUOTA_BY_NAME = new Map(quotaMatrix.schools.map((q) => [q.school, q]));
/** 指标结果索引：id 粒度优先（dist 只消费 id），无实体原文兜底（前端仅展示不可点） */
const OUTCOME_BY_ID = new Map<string, (typeof quotaOutcome.ids)[string]>();
for (const [id, v] of Object.entries(quotaOutcome.ids)) OUTCOME_BY_ID.set(id, v);
const OUTCOME_BY_NAME = new Map(Object.entries(quotaOutcome.schools));

const schools: Row[] = rankingMiddle.schools.map((r) => {
  const id = r.school_id || '';
  const pos = quotaPos.get(id) ?? 0;
  const q = id ? (QUOTA_BY_ID.get(id) ?? [])[pos] : undefined;
  if (id) quotaPos.set(id, pos + 1);
  const npos = namePos.get(id) ?? 0;
  const name = id ? (NAME_BY_ID.get(id) ?? [])[npos] ?? r.name ?? '' : r.name ?? '';
  if (id) namePos.set(id, npos + 1);
  const nameRow = id ? undefined : QUOTA_BY_NAME.get(name);
  const oc = id ? OUTCOME_BY_ID.get(id) : OUTCOME_BY_NAME.get(name);
  const grp = groupOfSchool(name, r.school_id);
  return {
    name,
    school_id: r.school_id,
    school_ids: r.school_ids ? r.school_ids.filter((x): x is string => !!x) : null,
    district: q?.district ?? nameRow?.district ?? '',
    minban: !!id && MINBAN_IDS.has(id),
    group: grp ? { brand: grp.brand, source: grp.source } : null,
    kaosheng: q?.kaosheng ?? nameRow?.kaosheng ?? null,
    sheng_quota: q?.sheng_quota ?? nameRow?.sheng_quota ?? null,
    qu_quota: q?.qu_quota ?? nameRow?.qu_quota ?? null,
    sheng_min_score: oc?.sheng_min_score ?? null,
    qu_min_score: oc?.qu_min_score ?? null,
    sheng_min_3y_avg: oc?.sheng_min_3y_avg ?? null,
    qu_min_3y_avg: oc?.qu_min_3y_avg ?? null,
    sheng_waste_rate: oc?.sheng_waste_rate ?? null,
    qu_waste_rate: oc?.qu_waste_rate ?? null,
    autonomy_count: r.autonomy_count,
    tekong_quota_rate: r.tekong_quota_rate ?? null,
  };
});

/** school_id → 实体（校区名/区），多校区法人行弹窗选校区用 */
const ENT_BY_ID = new Map(
  (entities as { entities: Array<{ school_id: string; name: string }> }).entities.map((e) => [e.school_id, e]),
);
const ADCODE_DIST: Record<string, string> = {
  '440103': '荔湾', '440104': '越秀', '440105': '海珠', '440106': '天河',
  '440111': '白云', '440112': '黄埔', '440113': '番禺', '440114': '花都',
  '440117': '从化', '440118': '增城', '440115': '南沙', '440100': '市属',
};
const districtOf = (sid: string): string => ADCODE_DIST[sid.slice(3, 9)] || '';

/** 多校区法人行弹窗：一个名字 → 点击弹出 school_ids 校区列表 → 选跳哪个校区 */
const campusPicker = ref<{ top: number; left: number; items: Array<{ id: string; name: string; district: string }> } | null>(null);
function openCampusPicker(s: Row, e: MouseEvent) {
  const ids = (s.school_ids || []).filter((i) => ENT_BY_ID.has(i));
  if (ids.length < 2) {
    // 弹窗数据不足（school_ids 缺失/无法解析）→ 回退直接跳主 id
    goSchool(s.name, s.school_id || undefined);
    return;
  }
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const w = 300;
  let left = r.left;
  if (left + w > window.innerWidth - 8) left = Math.max(8, window.innerWidth - w - 8);
  campusPicker.value = {
    top: r.bottom + 6,
    left,
    items: ids.map((id) => ({ id, name: ENT_BY_ID.get(id)!.name, district: districtOf(id) })),
  };
}
function closeCampusPicker() { campusPicker.value = null; }
function goCampus(item: { id: string; name: string }) {
  closeCampusPicker();
  goSchool(item.name, item.id);
}
function goSchool(name: string, id?: string) {
  router.push({ path: `/school/${encodeURIComponent(name)}`, query: { stage: 'middle', ...(id ? { id } : {}) } });
}

const openMenu = ref<'group' | 'filter' | 'metric' | null>(null);
const groupBy = ref<'none' | 'district' | 'group'>('none');
type MetricKey = 'default' | 'qu_ratio' | 'sheng_ratio' | 'tekong' | 'sheng_min' | 'qu_min';
const metric = ref<MetricKey>('default');

const METRIC_GROUPS: Array<{ title: string; items: Array<{ v: MetricKey; l: string }> }> = [
  {
    title: '综合排序',
    items: [{ v: 'default', l: '默认' }],
  },
  {
    title: '指标到校',
    items: [
      { v: 'qu_ratio', l: '区属指标比例（÷名额分配符合资格考生数）' },
      { v: 'sheng_ratio', l: '省市属指标比例（÷名额分配符合资格考生数）' },
      { v: 'sheng_min', l: '省市属指标最低分' },
      { v: 'qu_min', l: '区属指标最低分' },
    ],
  },
  {
    title: '升学出口质量',
    items: [{ v: 'tekong', l: '指标×高中特控率' }],
  },
];

const METRIC_META: Record<MetricKey, { label: string; note: string; unit: string; digits: number }> = {
  default: { label: '默认', note: '默认排序采用机构综合口径，数值列为区属指标比例（口径同“区属指标比例”）。', unit: '%', digits: 1 },
  qu_ratio: { label: '区属指标比例', note: '区属指标数 ÷ 符合名额分配报考资格考生数。反映本区学生获得本区区属指标的机会。', unit: '%', digits: 1 },
  sheng_ratio: { label: '省市属指标比例', note: '省市属高中名额分配指标数 ÷ 符合名额分配报考资格考生数。省市属指标按符合资格考生等比例分配，全区一致。', unit: '%', digits: 1 },
  tekong: { label: '指标×特控率', note: 'Σ(区属高中给该校指标名额 × 该高中特控率) ÷ 符合名额分配报考资格考生数。反映该校符合资格考生经区属指标到校路径预计上特控（一本）线的比例；特控率为喜报/网传口径，缺失的高中名额不计。', unit: '%', digits: 1 },
  sheng_min: { label: '省市属指标最低分', note: '该校学生通过第二批次（名额分配/指标到校）被省市属高中（11 所 20 校区 + 广州外国语学校）录取的最低分（录取序列最后一名，升学分数门槛）。第三批次分数不在此列。近3年平均分 = 2024/2025/2026 各年该最低分的时间维算术平均（某年无录取记录不参与）。', unit: '', digits: 0 },
  qu_min: { label: '区属指标最低分', note: '该校学生通过第二批次（名额分配/指标到校）被本区区属示范高中录取的最低分（录取序列最后一名，升学分数门槛）。第三批次分数不在此列。近3年平均分 = 2024/2025/2026 各年该最低分的时间维算术平均（某年无录取记录不参与）。', unit: '', digits: 0 },
};

/** 区属/省市属比例指标额外展示一列指标数绝对值 */
const showAbs = computed(() => metric.value === 'default' || metric.value === 'qu_ratio' || metric.value === 'sheng_ratio');
const absLabel = computed(() => (metric.value === 'sheng_ratio' ? '省市属指标数' : '区属指标数'));
function absValue(s: Row): number | null {
  return metric.value === 'sheng_ratio' ? (s.sheng_quota ?? null) : (s.qu_quota ?? null);
}
function fmtAbs(v: number | null): string {
  return v == null ? '—' : String(v);
}

/** 最低分指标模式：表格显示 最低分 / 近3年平均分 / 指标数 / 浪费率 四列（考生数列让位，指标数/浪费率随所选类型） */
const showOutcome = computed(() => metric.value === 'sheng_min' || metric.value === 'qu_min');
const outcomeQuotaLabel = computed(() => '指标数');
/** 近3年平均分（2024/2025/2026 各年最低分时间维均值，某年无录取不参与） */
function outcomeMin3y(s: Row): number | null {
  return metric.value === 'sheng_min' ? (s.sheng_min_3y_avg ?? null) : (s.qu_min_3y_avg ?? null);
}
function outcomeQuota(s: Row): number | null {
  return metric.value === 'sheng_min' ? (s.sheng_quota ?? null) : (s.qu_quota ?? null);
}
function outcomeWaste(s: Row): number | null {
  return metric.value === 'sheng_min' ? (s.sheng_waste_rate ?? null) : (s.qu_waste_rate ?? null);
}
function fmtWaste(v: number | null): string {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`;
}
function fmtAvg(v: number | null): string {
  return v == null ? '—' : v.toFixed(1);
}

/** 指标口径 / 名额分配符合资格考生数口径问号 popup（PC hover / 触屏点击）。
 *  Teleport 到 body + fixed 定位，避免被 .rank-group overflow 裁剪；
 *  切换指标、页面滚动、窗口缩放时自动收起。 */
const showHint = ref<'metric' | 'kaosheng' | 'waste' | 'avg' | null>(null);
const hintPos = ref({ top: 0, left: 0 });
let hintTimer: number | undefined;
function openHint(kind: 'metric' | 'kaosheng' | 'waste' | 'avg', e: MouseEvent) {
  clearTimeout(hintTimer);
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const w = 330;
  let left = r.left;
  if (left + w > window.innerWidth - 8) left = Math.max(8, window.innerWidth - w - 8);
  hintPos.value = { top: r.bottom + 6, left };
  showHint.value = kind;
}
function scheduleClose() {
  clearTimeout(hintTimer);
  hintTimer = window.setTimeout(() => { showHint.value = null; }, 160);
}
function keepHint() { clearTimeout(hintTimer); }
function toggleHint(kind: 'metric' | 'kaosheng' | 'waste' | 'avg', e: MouseEvent) {
  if (showHint.value === kind) showHint.value = null;
  else openHint(kind, e);
}
function closeHint() { clearTimeout(hintTimer); showHint.value = null; }
watch(metric, () => { closeHint(); closeCampusPicker(); });
onMounted(() => {
  window.addEventListener('scroll', () => { closeHint(); closeCampusPicker(); }, true);
  window.addEventListener('resize', () => { closeHint(); closeCampusPicker(); });
});
onBeforeUnmount(() => {
  window.removeEventListener('scroll', () => { closeHint(); closeCampusPicker(); }, true);
  window.removeEventListener('resize', () => { closeHint(); closeCampusPicker(); });
});

/** 符合名额分配报考资格考生数：广州市招考办政策口径（官方原文整理） */
const KAOSHENG_NOTE = '本列统计的是“符合名额分配报考资格的考生数”，不是学校全部应考人数。按广州市招生政策，须同时满足：初中应届毕业、具有广州市户籍（含政策性照顾学生，户籍或资格申报截止当年4月30日），并满足学籍条件——在广州同一初中有三年完整学籍且就读至毕业，或从市外转入广州后在转入学校就读至毕业。未满足上述条件但仍报名参加中考的考生，不计入本列，因此学校实际应考人数通常会更多。';

/** 指标浪费率口径（对数口径，与 canonical quota_outcome note 一致） */
const WASTE_NOTE = '指标浪费率 = 未完成录取的对数 ÷ 有指标的对数（对数口径）。官方录取分数表按「初中 × 高中」列出全部有指标的对，未填录取分数的对 = 有名额但未完成录取（未达控制线/无人报考/流标）。示例：某初中 10 个省市属录取对中有 2 个无录取分数，浪费率 20%。省市属与区属统一采用对数口径以保证两列可比；该口径以“官方表列出录取对”为分母，与指标总名额（quota）数值略有差异。';

/** 近3年平均分口径（时间维均值，非在校生混合均） */
const AVG_NOTE = '近3年平均分 = 2024 / 2025 / 2026 三年“最低分”（该校学生通过第二批次名额分配被省市属（或区属）高中录取的最后一名分数）的算术平均。各年均为同场中考的绝对值分数，可直接平均；某年该校无录取记录（当年未参加该批次 / 无数据）则不参与平均，平均分基于实际有录取记录的年份。与“最低分”列（最新 2026 年）并列展示。';

const metricLabel = computed(() => METRIC_META[metric.value].label);
const metricNote = computed(() => METRIC_META[metric.value].note);
/** 表格数值列列名：默认排序时仍显示区属指标比例；最低分模式缩写为「最低分」 */
const columnLabel = computed(() => {
  if (metric.value === 'sheng_min' || metric.value === 'qu_min') return '最低分';
  return metric.value === 'default' ? METRIC_META.qu_ratio.label : METRIC_META[metric.value].label;
});

/** 指标取值（null=无数据，排序置后） */
function metricValue(s: Row): number | null {
  const k = s.kaosheng ?? null;
  switch (metric.value) {
    case 'default':
    case 'qu_ratio': return k && s.qu_quota != null ? (s.qu_quota / k) * 100 : null;
    case 'sheng_ratio': return k && s.sheng_quota != null ? (s.sheng_quota / k) * 100 : null;
    case 'tekong': return s.tekong_quota_rate ?? null;
    case 'sheng_min': return s.sheng_min_score ?? null;
    case 'qu_min': return s.qu_min_score ?? null;
    default: return null;
  }
}

function fmt(v: number | null): string {
  if (v == null) return '—';
  const m = METRIC_META[metric.value]!;
  return `${v.toFixed(m.digits)}${m.unit}`;
}

/** 校名去行政区划前缀：广州市/广东/广州。去后 <3 字或以「大学」开头保留原名
 *  （避免「广州中学」→「中学」、「广州大学附属中学」→「大学附属中学」）。 */
function shortName(name: string): string {
  const n = name.trim();
  if (n.startsWith('广州市')) return n.slice(3);
  if (n.startsWith('广东')) return n.slice(2);
  if (n.startsWith('广州')) {
    const rest = n.slice(2);
    if (rest.length >= 3 && !rest.startsWith('大学')) return rest;
  }
  return n;
}

/** 组内排序：公办（false）在前、民办（true）在后；同类内按指标排序。
 *  最低分指标升序（asc=true，门槛越低越靠前），其余指标降序；null 置后。 */
function rankSort(a: { v: number | null; minban?: boolean }, b: { v: number | null; minban?: boolean }, asc = false): number {
  if (!!a.minban !== !!b.minban) return a.minban ? 1 : -1;
  if (a.v == null && b.v == null) return 0;
  if (a.v == null) return 1;
  if (b.v == null) return -1;
  return asc ? a.v - b.v : b.v - a.v;
}

/** 内部默认排序：机构手工整理档位（data/middle/org_sort/dist/compiled.json，school_id 由
 * data/middle/org_sort/scripts/build_org_sort.py 经 SchoolMatcher 匹配；对外不展示档位信息） */
const LEVEL_OF = new Map<string, number>();
// 同 school_id 可能出现在多档（如六中珠江鹭江 L3 / 六中逸景 L4 同记录 cb432890），取最小档（高优先级）
for (const item of middleOrgSort) {
  const cur = LEVEL_OF.get(item.school_id);
  if (cur === undefined || item.level < cur) LEVEL_OF.set(item.school_id, item.level);
}
function levelSort(a: { s: Row; v: number | null; minban?: boolean }, b: { s: Row; v: number | null; minban?: boolean }): number {
  const la = LEVEL_OF.get(a.s.school_id ?? '') ?? 99;
  const lb = LEVEL_OF.get(b.s.school_id ?? '') ?? 99;
  if (la !== lb) return la - lb;
  return rankSort(a, b);
}

/** 行政区位置筛选：默认全选，参考高中明细（未列入七区的行仅在全选时保留）。 */
const selectedDistricts = ref(new Set(DISTRICTS.map((d) => d.adcode)));
const districtAllOn = computed(() => selectedDistricts.value.size === DISTRICTS.length);
function toggleDistrict(adcode: string) {
  const next = new Set(selectedDistricts.value);
  next.has(adcode) ? next.delete(adcode) : next.add(adcode);
  selectedDistricts.value = next;
}
function flipDistricts() {
  selectedDistricts.value = districtAllOn.value ? new Set() : new Set(DISTRICTS.map((d) => d.adcode));
}
const DISTRICT_TO_ADCODE = new Map(DISTRICTS.map((d) => [d.name, d.adcode]));
function districtVisible(s: Row): boolean {
  if (districtAllOn.value) return true;
  const ad = DISTRICT_TO_ADCODE.get(s.district || '');
  return ad ? selectedDistricts.value.has(ad) : false;
}
const CIVILIZED_FILTERS = [['national', '全国文明校园'], ['provincial', '广东省文明校园'], ['municipal', '广州市文明校园'], ['advanced', '创建先进学校（储备）'], ['other', '其他']] as const;
type CivilizedKey = typeof CIVILIZED_FILTERS[number][0];
const selectedCivilized = ref<Set<CivilizedKey> | null>(null);
const civilizedAllOn = computed(() => selectedCivilized.value === null);
function civilizedOn(key: CivilizedKey) { return civilizedAllOn.value || selectedCivilized.value!.has(key); }
function toggleCivilized(key: CivilizedKey) { const next = new Set(selectedCivilized.value || CIVILIZED_FILTERS.map(([v]) => v)); next.has(key) ? next.delete(key) : next.add(key); selectedCivilized.value = next; }
function isCivilized(s: Row) { return [s.school_id, ...(s.school_ids || [])].some((id) => !!id && Object.values(civilizedCampusSchoolIds).some((ids) => ids.includes(id))); }
function civilizedVisible(s: Row) { return civilizedAllOn.value || [...selectedCivilized.value!].some((key) => key === 'other' ? !isCivilized(s) : [s.school_id, ...(s.school_ids || [])].some((id) => !!id && (civilizedCampusSchoolIds[key] || []).includes(id))); }
const filterCount = computed(() => (districtAllOn.value ? 0 : selectedDistricts.value.size) + (civilizedAllOn.value ? 0 : selectedCivilized.value!.size));
function resetFilters() { selectedDistricts.value = new Set(DISTRICTS.map((d) => d.adcode)); selectedCivilized.value = null; }
function toggleAllDistricts() { selectedDistricts.value = districtAllOn.value ? new Set() : new Set(DISTRICTS.map((d) => d.adcode)); }
function toggleAllCivilized() { selectedCivilized.value = civilizedAllOn.value ? new Set() : null; }

const groupLabel = computed(() => ({ none: '不分组', district: '按区', group: '按集团' })[groupBy.value]);

/** 分组顺序：按区 → DISTRICTS 顺序（未列出的区按出现顺序补尾）；按集团 → 组名拼音序 */
const districtOrder = DISTRICTS.map((d) => d.name.replace('区', ''));

const groups = computed(() => {
  const rows = schools.filter(districtVisible).filter(civilizedVisible).map((s) => ({ s, v: metricValue(s), minban: !!s.minban }));
  const asc = metric.value === 'sheng_min' || metric.value === 'qu_min';
  const sortFn = metric.value === 'default' ? levelSort : (a: { v: number | null; minban?: boolean }, b: { v: number | null; minban?: boolean }) => rankSort(a, b, asc);
  if (groupBy.value === 'none') {
    return [{ key: 'all', title: '', items: rows.slice().sort(sortFn) }];
  }
  if (groupBy.value === 'district') {
    const map = new Map<string, typeof rows>();
    for (const r of rows) {
      const key = r.s.district || '其他';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(r);
    }
    const keys = [...map.keys()].sort((a, b) => {
      const ia = districtOrder.indexOf(a); const ib = districtOrder.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });
    return keys.map((k) => ({
      key: `d-${k}`,
      title: k,
      items: map.get(k)!.slice().sort(sortFn),
    }));
  }
  // 按集团
  const map = new Map<string, typeof rows>();
  for (const r of rows) {
    const key = r.s.group?.brand || '未入集团';
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(r);
  }
  // 未入集团固定排最后（不参与拼音序）；其余组按组名拼音序
  const keys = [...map.keys()].sort((a, b) => {
    if (a === '未入集团') return 1;
    if (b === '未入集团') return -1;
    return a.localeCompare(b, 'zh');
  });
  return keys.map((k) => ({
    key: `g-${k}`,
    title: k,
    items: map.get(k)!.slice().sort(sortFn),
  }));
});
</script>

<template>
  <div class="page">
    <DetailPageHeader title="广州七区初中明细" subtitle="按升学指标与学校点位整理；排名不分先后。" />

    <!-- 顶部过滤器（对齐地图页 filter-bar 交互） -->
    <DetailFilterBar :open="!!openMenu" @close="openMenu = null">
      <template #buttons>
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'group' }" @click="openMenu = openMenu === 'group' ? null : 'group'">
          分组<em class="fb-badge">{{ groupLabel }}</em><span class="arr">▾</span>
        </button>
      </div>
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'filter' }" @click="openMenu = openMenu === 'filter' ? null : 'filter'">
          筛选<em v-if="filterCount" class="fb-badge">{{ filterCount }}</em><span class="arr">▾</span>
        </button>
      </div>
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'metric' }" @click="openMenu = openMenu === 'metric' ? null : 'metric'">
          指标：{{ metricLabel }}<span class="arr">▾</span>
        </button>
      </div>

      </template>
      <div v-if="openMenu === 'group'">
        <div class="pop-chips">
          <button class="pop-chip" :class="{ on: groupBy === 'none' }" @click="groupBy = 'none'">不分组</button>
          <button class="pop-chip" :class="{ on: groupBy === 'district' }" @click="groupBy = 'district'">按区</button>
          <button class="pop-chip" :class="{ on: groupBy === 'group' }" @click="groupBy = 'group'">按教育集团</button>
        </div>
        <div class="pop-foot">
          <button class="pop-link" @click="openMenu = null">完成</button>
        </div>
      </div>

      <div v-if="openMenu === 'filter'">
        <div class="pop-group-title">位置</div>
        <div class="pop-chips">
          <button v-for="d in DISTRICTS" :key="d.adcode" class="pop-chip" :class="{ on: selectedDistricts.has(d.adcode) }" @click="toggleDistrict(d.adcode)">{{ d.name }}</button>
        </div>
        <div class="pop-foot"><button class="pop-link" @click="toggleAllDistricts">{{ districtAllOn ? '全不选' : '全选' }}</button></div>
        <div class="pop-group-title">校园荣誉</div><div class="pop-chips"><button v-for="option in CIVILIZED_FILTERS" :key="option[0]" class="pop-chip" :class="{ on: civilizedOn(option[0]) }" @click="toggleCivilized(option[0])">{{ option[1] }}</button></div><div class="pop-foot"><button class="pop-link" @click="toggleAllCivilized">{{ civilizedAllOn ? '全不选' : '全选' }}</button></div>
        <div class="pop-foot">
          <button class="pop-link" @click="resetFilters">重置</button>
          <button class="pop-link" @click="openMenu = null">完成</button>
        </div>
      </div>

      <div v-if="openMenu === 'metric'">
        <div v-for="g in METRIC_GROUPS" :key="g.title" class="pop-group">
          <div class="pop-group-title">{{ g.title }}</div>
          <div class="pop-chips">
            <button v-for="m in g.items" :key="m.v" class="pop-chip" :class="{ on: metric === m.v }" @click="metric = m.v">{{ m.l }}</button>
          </div>
        </div>
        <div class="pop-foot">
          <button class="pop-link" @click="openMenu = null">完成</button>
        </div>
      </div>
    </DetailFilterBar>

    <DetailRankingList :groups="groups" :group-key="(g) => g.key">
      <template #heading="{ group: g }"><h3 v-if="groupBy !== 'none'" class="rg-title">{{ g.title }}<em class="rg-count">{{ g.items.length }} 所 · 排名不分先后</em></h3></template>
      <template #default="{ group: g }">
        <table class="rank-table">
          <colgroup>
            <col class="col-name">
            <col class="col-val">
            <col v-if="showOutcome" class="col-sub-avg">
            <col v-if="showOutcome" class="col-sub">
            <col v-if="showOutcome" class="col-sub">
            <col v-else-if="showAbs" class="col-sub">
            <col v-else class="col-sub">
          </colgroup>
          <thead>
            <tr>
              <th class="c-name">学校</th>
              <th class="c-val">
                {{ columnLabel }}
                <span
                  class="q-mark"
                  aria-label="指标口径说明"
                  @mouseenter="openHint('metric', $event)"
                  @mouseleave="scheduleClose"
                  @click.stop="toggleHint('metric', $event)"
                >?</span>
              </th>
              <th v-if="showOutcome" class="c-sub">
                近3年平均分
                <span
                  class="q-mark"
                  aria-label="近3年最低分平均分口径说明"
                  @mouseenter="openHint('avg', $event)"
                  @mouseleave="scheduleClose"
                  @click.stop="toggleHint('avg', $event)"
                >?</span>
              </th>
              <th v-if="showOutcome" class="c-sub">{{ outcomeQuotaLabel }}</th>
              <th v-if="showOutcome" class="c-sub">
                浪费率
                <span
                  class="q-mark"
                  aria-label="指标浪费率口径说明"
                  @mouseenter="openHint('waste', $event)"
                  @mouseleave="scheduleClose"
                  @click.stop="toggleHint('waste', $event)"
                >?</span>
              </th>
              <th v-else-if="showAbs" class="c-sub">{{ absLabel }}</th>
              <th v-else class="c-sub">
                考生数
                <span
                  class="q-mark"
                  aria-label="名额分配符合资格考生数口径说明"
                  @mouseenter="openHint('kaosheng', $event)"
                  @mouseleave="scheduleClose"
                  @click.stop="toggleHint('kaosheng', $event)"
                >?</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in g.items" :key="row.s.name">
              <td class="c-name">
                <button
                  v-if="(row.s.school_ids?.length ?? 0) > 1"
                  class="school-link campus-open"
                  @click="openCampusPicker(row.s, $event)"
                >{{ shortName(row.s.name) }}</button>
                <RouterLink
                  v-else
                  class="school-link"
                  :to="{ path: '/school/' + encodeURIComponent(row.s.name), query: { stage: 'middle', ...(row.s.school_id ? { id: row.s.school_id } : {}) } }"
                >{{ shortName(row.s.name) }}</RouterLink>
                <em v-if="row.s.minban" class="mb-tag">民办</em>
              </td>
              <td class="c-val">{{ fmt(row.v) }}</td>
              <td v-if="showOutcome" class="c-sub">{{ fmtAvg(outcomeMin3y(row.s)) }}</td>
              <td v-if="showOutcome" class="c-sub">{{ fmtAbs(outcomeQuota(row.s)) }}</td>
              <td v-if="showOutcome" class="c-sub">{{ fmtWaste(outcomeWaste(row.s)) }}</td>
              <td v-else-if="showAbs" class="c-sub">{{ fmtAbs(absValue(row.s)) }}</td>
              <td v-else class="c-sub">{{ row.s.kaosheng ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </DetailRankingList>

    <footer class="foot-note">
      数据来源：广州市招考办 2026 名额分配计划汇总表（符合名额分配报考资格考生数/指标数）· 高中特控率喜报/网传口径（data/high/level/src/levels.json）。比例均为「÷ 符合名额分配报考资格考生数」，不代表学校全部应考人数。
    </footer>

    <Teleport to="body">
      <div
        v-if="showHint"
        class="hint-pop"
        :style="{ top: hintPos.top + 'px', left: hintPos.left + 'px' }"
        @mouseenter="keepHint"
        @mouseleave="scheduleClose"
      >
        <template v-if="showHint === 'metric'">
          <div class="hp-title">{{ metricLabel }}</div>
          <div class="hp-line">{{ metricNote }}</div>
        </template>
        <template v-else-if="showHint === 'waste'">
          <div class="hp-title">指标浪费率口径</div>
          <div class="hp-line">{{ WASTE_NOTE }}</div>
        </template>
        <template v-else-if="showHint === 'avg'">
          <div class="hp-title">近3年最低分均值口径</div>
          <div class="hp-line">{{ AVG_NOTE }}</div>
        </template>
        <template v-else>
          <div class="hp-title">名额分配符合资格考生数口径</div>
          <div class="hp-line">{{ KAOSHENG_NOTE }}</div>
        </template>
      </div>
      <!-- 多校区法人行：一个名字 + 弹窗选校区（用户口径：不直接锚定单校区） -->
      <div v-if="campusPicker" class="campus-mask" @click="closeCampusPicker"></div>
      <div
        v-if="campusPicker"
        class="campus-pop"
        :style="{ top: campusPicker.top + 'px', left: campusPicker.left + 'px' }"
      >
        <div class="campus-pop-title">选择校区</div>
        <button v-for="c in campusPicker.items" :key="c.id" class="campus-opt" @click="goCampus(c)">
          <span class="campus-name">{{ shortName(c.name) }}</span>
          <span class="campus-dist">{{ c.district }}</span>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page { max-width: 1180px; margin: 0 auto; }

/* ---- 排行主体 ---- */
.rg-title {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 15px; font-weight: 700; margin: 0; padding: 12px 18px 8px;
}
.rg-count { font-style: normal; font-size: 11.5px; color: #8a93a3; font-weight: 500; }
.rank-table { width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 12.5px; }
/* 列宽统一（colgroup），保证各分组表格列对齐；col-sub 不设宽，均分剩余空间。
 * 最低分模式 5 列：学校 38% / 最低分 17% / 近3年平均分 16% / 指标数、浪费率均分剩余 29%。 */
.col-name { width: 38%; }
.col-val { width: 17%; }
.col-sub-avg { width: 16%; }
.rank-table th {
  text-align: left; font-size: 11.5px; color: #8a93a3; font-weight: 600;
  padding: 7px 10px; border-bottom: 1px solid #ecebe6;
  position: relative;
}
.rank-table td { padding: 9px 10px; border-bottom: 1px solid #f2f1ec; vertical-align: middle; line-height: 1.5; }
.rank-table tbody tr:last-child td { border-bottom: none; }
.rank-table tbody tr:hover { background: #fafbfc; }
.c-val { font-variant-numeric: tabular-nums; font-weight: 600; color: #1a1b1c; white-space: nowrap; }
.c-sub { color: #6b7280; font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.c-name { overflow-wrap: anywhere; }

/* 指标口径/名额分配符合资格考生数口径问号 + popup（Teleport 到 body，fixed 定位不受表格 overflow 裁剪） */
.q-mark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; margin-left: 4px; border-radius: 50%;
  border: 1px solid #c3c9d4; color: #6b7280; font-size: 10.5px; line-height: 1;
  cursor: help; vertical-align: 1px; user-select: none;
}
.q-mark:hover { border-color: #1a6bd6; color: #1a6bd6; }
.hint-pop {
  position: fixed; z-index: 1300;
  width: 330px; max-width: 86vw; background: #fff;
  border: 1px solid #e4e3dd; border-radius: 12px;
  box-shadow: 0 10px 30px rgba(20, 30, 50, 0.16); padding: 10px 12px;
  font-size: 12px; color: #4b5563; line-height: 1.65; font-weight: 400; white-space: normal;
}
.hp-title { font-size: 12.5px; font-weight: 700; color: #1a1b1c; margin-bottom: 4px; }
.hp-line { margin-bottom: 4px; }
.hp-line:last-child { margin-bottom: 0; }

.campus-open { font: inherit; background: none; border: 0; padding: 0; cursor: pointer; text-align: left; }
.campus-open:hover { color: #0e4fb0; }
.campus-mask { position: fixed; inset: 0; z-index: 1350; background: rgba(0, 0, 0, 0.03); }
.campus-pop {
  position: fixed; z-index: 1400; width: 300px; max-width: 86vw;
  background: #fff; border: 1px solid #e4e3dd; border-radius: 12px;
  box-shadow: 0 10px 30px rgba(20, 30, 50, 0.16); padding: 8px;
}
.campus-pop-title { font-size: 12.5px; font-weight: 700; color: #1a1b1c; padding: 4px 6px 8px; }
.campus-opt {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  width: 100%; border: 0; background: transparent; border-radius: 8px;
  padding: 7px 8px; font-size: 12.5px; color: #1a6bd6; cursor: pointer; text-align: left;
}
.campus-opt:hover { background: #f2f7ff; }
.campus-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.campus-dist { flex: none; font-size: 11px; color: #8a93a3; }
.mb-tag {
  margin-left: 6px; font-style: normal; font-size: 10.5px; color: #b45309;
  background: #fef3c7; border: 1px solid #fde68a; border-radius: 8px; padding: 0 5px; line-height: 15px;
}
.foot-note { font-size: 11.5px; color: #8a93a3; margin: 18px 2px 30px; line-height: 1.7; }
</style>
