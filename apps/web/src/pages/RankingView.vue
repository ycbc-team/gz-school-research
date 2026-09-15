<script setup lang="ts">
/**
 * 初中升学信号明细
 * - 数据真源：data/linkage/middle_middle.json（scripts/linkage/build_ranking_middle.py 聚合，
 *   含名额分配考生数/省市属·区属指标/2026 自招名单计数/指标到校高中明细+特控率）
 * - 分组：按区（区教育局口径）或按教育集团（@gz/shared groupOfSchool，brand 优先）
 * - 指标（6 选 1）：自招绝对值 / 自招比例 / 区属指标数 / 区属指标比例 / 省市属指标比例 / 指标×高中特控率
 * - 榜单口径：所有比例均以「名额分配符合资格考生数（kaosheng）」为分母，
 *   消除学校规模差异（学生多则名额自然多，须看比例）
 */
import { ref, computed } from 'vue';
import { DISTRICTS } from '@gz/shared';
import { rankingMiddle } from '../data';

interface Row {
  name: string;
  school_id?: string | null;
  district: string;
  group?: { brand: string; source: 'brand' | 'education' } | null;
  reputation?: string | null;
  kaosheng?: number | null;
  sheng_quota?: number | null;
  qu_quota?: number | null;
  autonomy_count: number;
  sz: Array<{ high: string; count: number; tekong?: number | null }>;
  tekong_quota_rate?: number | null;
}

const schools = rankingMiddle.schools as Row[];

const openMenu = ref<'group' | 'metric' | null>(null);
const groupBy = ref<'district' | 'group'>('district');
type MetricKey = 'aut_abs' | 'aut_ratio' | 'qu_abs' | 'qu_ratio' | 'sheng_ratio' | 'tekong';
const metric = ref<MetricKey>('aut_ratio');

const METRIC_GROUPS: Array<{ title: string; items: Array<{ v: MetricKey; l: string }> }> = [
  {
    title: '自主招生（2026 资格名单）',
    items: [
      { v: 'aut_abs', l: '自招人数（绝对值）' },
      { v: 'aut_ratio', l: '自招比例（÷考生数）' },
    ],
  },
  {
    title: '指标到校',
    items: [
      { v: 'qu_abs', l: '区属指标数' },
      { v: 'qu_ratio', l: '区属指标比例（÷考生数）' },
      { v: 'sheng_ratio', l: '省市属指标比例（÷考生数）' },
    ],
  },
  {
    title: '升学出口质量',
    items: [{ v: 'tekong', l: '指标×高中特控率' }],
  },
];

const METRIC_META: Record<MetricKey, { label: string; note: string; unit: string; digits: number }> = {
  aut_abs: { label: '自招人数', note: '2026 年自主招生综合能力考核资格名单中，来源初中的考生人数（绝对值）。', unit: '人', digits: 0 },
  aut_ratio: { label: '自招比例', note: '自招资格人数 ÷ 名额分配符合资格考生数。比例口径消除学校规模差异（学生多则名额自然多）。', unit: '%', digits: 1 },
  qu_abs: { label: '区属指标数', note: '区属示范性高中名额分配指标数（如执信天河校区对天河区的指标）。', unit: '个', digits: 0 },
  qu_ratio: { label: '区属指标比例', note: '区属指标数 ÷ 考生数。反映本区学生获得本区区属指标的机会。', unit: '%', digits: 1 },
  sheng_ratio: { label: '省市属指标比例', note: '省市属高中名额分配指标数 ÷ 考生数。省市属指标按符合资格考生等比例分配，全区一致。', unit: '%', digits: 1 },
  tekong: { label: '指标×特控率', note: 'Σ(区属高中给该校指标名额 × 该高中特控率) ÷ 该校考生数。反映该校考生经区属指标到校路径预计上特控（一本）线的比例；特控率为喜报/网传口径，缺失的高中名额不计。', unit: '%', digits: 1 },
};

const metricLabel = computed(() => METRIC_META[metric.value].label);
const metricNote = computed(() => METRIC_META[metric.value].note);

/** 指标取值（null=无数据，排序置后） */
function metricValue(s: Row): number | null {
  const k = s.kaosheng ?? null;
  switch (metric.value) {
    case 'aut_abs': return s.autonomy_count;
    case 'aut_ratio': return k && s.autonomy_count != null ? (s.autonomy_count / k) * 100 : null;
    case 'qu_abs': return s.qu_quota ?? null;
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

function repLabel(r?: string | null): string {
  return r === '口碑' ? '口碑' : r === '待观察' ? '待观察' : r === '不支撑' ? '不支撑' : '';
}

/** 分组顺序：按区 → DISTRICTS 顺序（未列出的区按出现顺序补尾）；按集团 → 组内口碑校数降序、再按组名 */
const districtOrder = DISTRICTS.map((d) => d.name.replace('区', ''));

const groups = computed(() => {
  const rows = schools.map((s) => ({ s, v: metricValue(s) }));
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
      items: map.get(k)!.slice().sort((a, b) => rankSort(a.v, b.v)),
    }));
  }
  // 按集团
  const map = new Map<string, typeof rows>();
  for (const r of rows) {
    const key = r.s.group?.brand || '未入集团';
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(r);
  }
  const keys = [...map.keys()].sort((a, b) => {
    const ra = map.get(a)!.filter((x) => x.s.reputation === '口碑').length;
    const rb = map.get(b)!.filter((x) => x.s.reputation === '口碑').length;
    if (ra !== rb) return rb - ra;
    return a.localeCompare(b, 'zh');
  });
  return keys.map((k) => ({
    key: `g-${k}`,
    title: k,
    items: map.get(k)!.slice().sort((a, b) => rankSort(a.v, b.v)),
  }));
});

function rankSort(a: number | null, b: number | null): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  return b - a;
}
</script>

<template>
  <div class="page">
    <header class="top">
      <RouterLink to="/" class="back">‹ 首页</RouterLink>
      <h1 class="page-title">初中升学信号明细</h1>
      <p class="page-sub">55 所初中升学信号 · 自招 / 指标到校 / 特控率 · 比例口径消除规模差异</p>
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

    <p class="metric-note">当前指标：<b>{{ metricLabel }}</b> — {{ metricNote }}</p>

    <main class="rank-body">
      <section v-for="g in groups" :key="g.key" class="rank-group">
        <h3 class="rg-title">{{ g.title }}<em class="rg-count">{{ g.items.length }} 所</em></h3>
        <table class="rank-table">
          <thead>
            <tr>
              <th class="c-rank">#</th>
              <th class="c-name">学校</th>
              <th class="c-val">{{ metricLabel }}</th>
              <th class="c-sub">考生数</th>
              <th class="c-sub">口碑</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in g.items" :key="row.s.name" :class="{ rep: row.s.reputation === '口碑' }">
              <td class="c-rank">{{ i + 1 }}</td>
              <td class="c-name">{{ row.s.name }}</td>
              <td class="c-val">{{ fmt(row.v) }}</td>
              <td class="c-sub">{{ row.s.kaosheng ?? '—' }}</td>
              <td class="c-sub">
                <span v-if="row.s.reputation" class="rep-badge" :class="row.s.reputation">{{ repLabel(row.s.reputation) }}</span>
                <span v-else class="rep-none">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>

    <footer class="foot-note">
      数据来源：广州市招考办 2026 名额分配计划汇总表（考生数/指标数）· 2026 自主招生资格名单（13866 条）· 高中特控率喜报/网传口径（data/high/levels.json）。比例均为「÷ 名额分配符合资格考生数」。
    </footer>
  </div>
</template>

<style scoped>
.page { max-width: 980px; margin: 0 auto; padding: 16px; }
.top { display: flex; flex-direction: column; gap: 6px; }
.back { font-size: 13px; color: #1a6bd6; text-decoration: none; }
.back:hover { text-decoration: underline; }
.page-title { font-size: 20px; font-weight: 700; margin: 0; }
.page-sub { font-size: 12.5px; color: #6b7280; margin: 0; }

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

.metric-note { font-size: 12.5px; color: #4b5563; background: #f7f8fa; border-radius: 10px; padding: 10px 12px; margin: 12px 0; line-height: 1.6; }
.metric-note b { color: #1a6bd6; }

/* ---- 排行主体 ---- */
.rank-body { display: flex; flex-direction: column; gap: 16px; }
.rank-group { background: #fff; border: 1px solid #e4e3dd; border-radius: 14px; overflow: hidden; }
.rg-title {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 15px; font-weight: 700; margin: 0; padding: 12px 14px 8px;
}
.rg-count { font-style: normal; font-size: 11.5px; color: #8a93a3; font-weight: 500; }
.rank-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.rank-table th {
  text-align: left; font-size: 11.5px; color: #8a93a3; font-weight: 600;
  padding: 6px 10px; border-bottom: 1px solid #ecebe6;
}
.rank-table td { padding: 7px 10px; border-bottom: 1px solid #f2f1ec; vertical-align: middle; }
.rank-table tbody tr:last-child td { border-bottom: none; }
.rank-table tbody tr.rep { background: #f4f8ff; }
.rank-table tbody tr:hover { background: #fafbfc; }
.c-rank { width: 34px; color: #8a93a3; font-size: 12px; }
.c-val { font-variant-numeric: tabular-nums; font-weight: 600; color: #1a6bd6; }
.c-sub { color: #6b7280; font-size: 12px; font-variant-numeric: tabular-nums; }
.c-name { max-width: 220px; }
.rep-badge {
  display: inline-block; font-size: 10.5px; border-radius: 999px; padding: 1px 8px;
}
.rep-badge.口碑 { color: #b42318; background: #fef0ee; }
.rep-badge.待观察 { color: #8a6d1c; background: #fbf4dd; }
.rep-badge.不支撑 { color: #6b7280; background: #f0f0ee; }
.rep-none { color: #c3c7cd; }
.foot-note { font-size: 11.5px; color: #8a93a3; margin: 18px 2px 30px; line-height: 1.7; }
</style>
