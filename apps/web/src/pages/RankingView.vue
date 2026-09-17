<script setup lang="ts">
/**
 * 初中升学信号明细
 * - 数据真源：data/linkage/middle_middle.json（scripts/linkage/build_ranking_middle.py 聚合，
 *   含名额分配符合资格考生数/省市属·区属指标/2026 自招名单计数/指标到校高中明细+特控率）
 * - 分组：按区（区教育局口径）或按教育集团（@gz/shared groupOfSchool，brand 优先）
 * - 指标（6 选 1）：自招绝对值 / 自招比例 / 区属指标数 / 区属指标比例 / 省市属指标比例 / 指标×高中特控率
 * - 榜单口径：所有比例均以「符合名额分配报考资格考生数（kaosheng）」为分母，
 *   消除学校规模差异（学生多则名额自然多，须看比例）
 */
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { DISTRICTS } from '@gz/shared';
import { rankingMiddle, entities } from '../data';

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
  autonomy_count: number;
  sz: Array<{ high: string; count: number; tekong?: number | null }>;
  tekong_quota_rate?: number | null;
}

const router = useRouter();
const schools = rankingMiddle.schools as Row[];

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

const openMenu = ref<'group' | 'metric' | null>(null);
const groupBy = ref<'district' | 'group'>('district');
type MetricKey = 'aut_abs' | 'aut_ratio' | 'qu_ratio' | 'sheng_ratio' | 'tekong';
const metric = ref<MetricKey>('aut_ratio');

const METRIC_GROUPS: Array<{ title: string; items: Array<{ v: MetricKey; l: string }> }> = [
  {
    title: '自主招生（2026 资格名单）',
    items: [
      { v: 'aut_abs', l: '自招人数（绝对值）' },
      { v: 'aut_ratio', l: '自招比例（÷名额分配符合资格考生数）' },
    ],
  },
  {
    title: '指标到校',
    items: [
      { v: 'qu_ratio', l: '区属指标比例（÷名额分配符合资格考生数）' },
      { v: 'sheng_ratio', l: '省市属指标比例（÷名额分配符合资格考生数）' },
    ],
  },
  {
    title: '升学出口质量',
    items: [{ v: 'tekong', l: '指标×高中特控率' }],
  },
];

const METRIC_META: Record<MetricKey, { label: string; note: string; unit: string; digits: number }> = {
  aut_abs: { label: '自招人数', note: '2026 年自主招生综合能力考核资格名单中，来源初中的考生人数（绝对值）。', unit: '人', digits: 0 },
  aut_ratio: { label: '自招比例', note: '自招资格人数 ÷ 符合名额分配报考资格考生数。比例口径消除学校规模差异（学生多则名额自然多）。', unit: '%', digits: 1 },
  qu_ratio: { label: '区属指标比例', note: '区属指标数 ÷ 符合名额分配报考资格考生数。反映本区学生获得本区区属指标的机会。', unit: '%', digits: 1 },
  sheng_ratio: { label: '省市属指标比例', note: '省市属高中名额分配指标数 ÷ 符合名额分配报考资格考生数。省市属指标按符合资格考生等比例分配，全区一致。', unit: '%', digits: 1 },
  tekong: { label: '指标×特控率', note: 'Σ(区属高中给该校指标名额 × 该高中特控率) ÷ 符合名额分配报考资格考生数。反映该校符合资格考生经区属指标到校路径预计上特控（一本）线的比例；特控率为喜报/网传口径，缺失的高中名额不计。', unit: '%', digits: 1 },
};

/** 区属/省市属比例指标额外展示一列指标数绝对值 */
const showAbs = computed(() => metric.value === 'qu_ratio' || metric.value === 'sheng_ratio');
const absLabel = computed(() => (metric.value === 'qu_ratio' ? '区属指标数' : '省市属指标数'));
function absValue(s: Row): number | null {
  return metric.value === 'qu_ratio' ? (s.qu_quota ?? null) : (s.sheng_quota ?? null);
}
function fmtAbs(v: number | null): string {
  return v == null ? '—' : String(v);
}

/** 指标口径 / 名额分配符合资格考生数口径问号 popup（PC hover / 触屏点击）。
 *  Teleport 到 body + fixed 定位，避免被 .rank-group overflow 裁剪；
 *  切换指标、页面滚动、窗口缩放时自动收起。 */
const showHint = ref<'metric' | 'kaosheng' | null>(null);
const hintPos = ref({ top: 0, left: 0 });
let hintTimer: number | undefined;
function openHint(kind: 'metric' | 'kaosheng', e: MouseEvent) {
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
function toggleHint(kind: 'metric' | 'kaosheng', e: MouseEvent) {
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

const metricLabel = computed(() => METRIC_META[metric.value].label);
const metricNote = computed(() => METRIC_META[metric.value].note);

/** 指标取值（null=无数据，排序置后） */
function metricValue(s: Row): number | null {
  const k = s.kaosheng ?? null;
  switch (metric.value) {
    case 'aut_abs': return s.autonomy_count;
    case 'aut_ratio': return k && s.autonomy_count != null ? (s.autonomy_count / k) * 100 : null;
    case 'qu_ratio': return k && s.qu_quota != null ? (s.qu_quota / k) * 100 : null;
    case 'sheng_ratio': return k && s.sheng_quota != null ? (s.sheng_quota / k) * 100 : null;
    case 'tekong': return s.tekong_quota_rate ?? null;
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

/** 组内排序：公办（false）在前、民办（true）在后；同类内按指标倒序（null 置后） */
function rankSort(a: { v: number | null; minban?: boolean }, b: { v: number | null; minban?: boolean }): number {
  if (!!a.minban !== !!b.minban) return a.minban ? 1 : -1;
  if (a.v == null && b.v == null) return 0;
  if (a.v == null) return 1;
  if (b.v == null) return -1;
  return b.v - a.v;
}

/** 分组顺序：按区 → DISTRICTS 顺序（未列出的区按出现顺序补尾）；按集团 → 组名拼音序 */
const districtOrder = DISTRICTS.map((d) => d.name.replace('区', ''));

const groups = computed(() => {
  const rows = schools.map((s) => ({ s, v: metricValue(s), minban: !!s.minban }));
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
      items: map.get(k)!.slice().sort((a, b) => rankSort(a, b)),
    }));
  }
  // 按集团
  const map = new Map<string, typeof rows>();
  for (const r of rows) {
    const key = r.s.group?.brand || '未入集团';
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(r);
  }
  const keys = [...map.keys()].sort((a, b) => a.localeCompare(b, 'zh'));
  return keys.map((k) => ({
    key: `g-${k}`,
    title: k,
    items: map.get(k)!.slice().sort((a, b) => rankSort(a, b)),
  }));
});
</script>

<template>
  <div class="page">
    <header class="top">
      <RouterLink to="/" class="back">‹ 首页</RouterLink>
      <h1 class="page-title">广州七区初中明细</h1>
    </header>

    <!-- 顶部过滤器（对齐地图页 filter-bar 交互） -->
    <div class="filter-bar">
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'group' }" @click="openMenu = openMenu === 'group' ? null : 'group'">
          分组<em class="fb-badge">{{ groupBy === 'district' ? '按区' : '按集团' }}</em><span class="arr">▾</span>
        </button>
      </div>
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'metric' }" @click="openMenu = openMenu === 'metric' ? null : 'metric'">
          指标：{{ metricLabel }}<span class="arr">▾</span>
        </button>
      </div>

      <div v-if="openMenu === 'group'" class="fb-pop">
        <div class="pop-chips">
          <button class="pop-chip" :class="{ on: groupBy === 'district' }" @click="groupBy = 'district'">按区</button>
          <button class="pop-chip" :class="{ on: groupBy === 'group' }" @click="groupBy = 'group'">按教育集团</button>
        </div>
        <div class="pop-foot">
          <button class="pop-link" @click="openMenu = null">完成</button>
        </div>
      </div>

      <div v-if="openMenu === 'metric'" class="fb-pop">
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
    </div>
    <div v-if="openMenu" class="pop-mask" @click="openMenu = null"></div>

    <main class="rank-body">
      <section v-for="g in groups" :key="g.key" class="rank-group">
        <h3 class="rg-title">{{ g.title }}<em class="rg-count">{{ g.items.length }} 所 · 排名不分先后</em></h3>
        <table class="rank-table">
          <thead>
            <tr>
              <th class="c-name">学校</th>
              <th class="c-val">
                {{ metricLabel }}
                <span
                  class="q-mark"
                  aria-label="指标口径说明"
                  @mouseenter="openHint('metric', $event)"
                  @mouseleave="scheduleClose"
                  @click.stop="toggleHint('metric', $event)"
                >?</span>
              </th>
              <th v-if="showAbs" class="c-sub">{{ absLabel }}</th>
              <th class="c-sub">
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
              <td v-if="showAbs" class="c-sub">{{ fmtAbs(absValue(row.s)) }}</td>
              <td class="c-sub">{{ row.s.kaosheng ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>

    <footer class="foot-note">
      数据来源：广州市招考办 2026 名额分配计划汇总表（符合名额分配报考资格考生数/指标数）· 2026 自主招生资格名单（13866 条）· 高中特控率喜报/网传口径（data/high/levels.json）。比例均为「÷ 符合名额分配报考资格考生数」，不代表学校全部应考人数。
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
.page { max-width: 980px; margin: 0 auto; padding: 16px; }
.top { display: flex; flex-direction: column; gap: 6px; }
.back { font-size: 13px; color: #1a6bd6; text-decoration: none; }
.back:hover { text-decoration: underline; }
.page-title { font-size: 20px; font-weight: 700; margin: 0; }

/* ---- 顶部过滤器（对齐地图页） ---- */
.filter-bar {
  position: sticky; top: 0; z-index: 1200;
  display: flex; gap: 8px; background: #fff;
  border: 1px solid #e4e3dd; border-radius: 14px; padding: 8px; margin-top: 14px;
}
.fb-col { flex: 1 1 0; min-width: 0; }
.fb-btn {
  width: 100%; border: none; background: transparent; cursor: pointer;
  font-size: 13px; color: #1a1b1c; padding: 8px 6px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center; gap: 4px; white-space: nowrap;
}
.fb-btn:hover { background: #f2f7ff; }
.fb-btn.on { background: #eaf1fe; color: #1a6bd6; font-weight: 600; }
.fb-btn .arr { font-size: 10px; color: #8a93a3; }
.fb-badge {
  background: #1a6bd6; color: #fff; font-style: normal; font-size: 10.5px;
  border-radius: 9px; padding: 0 6px; line-height: 15px;
}
.fb-pop {
  position: absolute; top: calc(100% + 6px); left: 8px; right: 8px; z-index: 1300;
  background: #fff; border: 1px solid #e4e3dd; border-radius: 12px;
  box-shadow: 0 8px 28px rgba(20, 30, 50, 0.16); padding: 12px;
}
.pop-group { margin-bottom: 10px; }
.pop-group:last-of-type { margin-bottom: 0; }
.pop-group-title { font-size: 11.5px; color: #6b7280; font-weight: 600; margin-bottom: 6px; }
.pop-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.pop-chip {
  border: 1px solid #d6d4cc; background: #fff; border-radius: 16px;
  padding: 5px 14px; font-size: 12.5px; cursor: pointer; color: #1a1b1c;
}
.pop-chip.on { background: #1a6bd6; border-color: #1a6bd6; color: #fff; }
.pop-foot { display: flex; justify-content: flex-end; margin-top: 10px; }
.pop-link { border: none; background: none; color: #1a6bd6; font-size: 13px; cursor: pointer; padding: 4px 8px; }
.pop-mask { position: fixed; inset: 0; z-index: 1100; }

/* ---- 排行主体 ---- */
.rank-body { display: flex; flex-direction: column; gap: 16px; }
.rank-group { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; overflow: hidden; }
.rg-title {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 15px; font-weight: 700; margin: 0; padding: 12px 10px 8px;
}
.rg-count { font-style: normal; font-size: 11.5px; color: #8a93a3; font-weight: 500; }
.rank-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.rank-table th {
  text-align: left; font-size: 11.5px; color: #8a93a3; font-weight: 600;
  padding: 6px 10px; border-bottom: 1px solid #ecebe6;
  position: relative;
}
.rank-table td { padding: 7px 10px; border-bottom: 1px solid #f2f1ec; vertical-align: middle; }
.rank-table tbody tr:last-child td { border-bottom: none; }
.rank-table tbody tr:hover { background: #fafbfc; }
.c-val { font-variant-numeric: tabular-nums; font-weight: 600; color: #1a1b1c; white-space: nowrap; }
.c-sub { color: #6b7280; font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.c-name { max-width: 240px; }

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

.school-link { color: #1a6bd6; text-decoration: underline; text-underline-offset: 2px; }
.school-link:hover { text-decoration-thickness: 2px; }
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
