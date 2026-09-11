<script setup lang="ts">
/**
 * 七区中小学·高中分布地图（Vue3 + Leaflet，功能对齐旧版 map/index.html）：
 * - 七类点位配色：小学普通/口碑、初中普通/口碑、高中普通/区属示范/省市属示范
 * - 有支撑加粗+晕光、部分支撑加粗、独立法人挂牌校虚线点
 * - 7 类筛选 + 全选/全不选；各区小学/初中/高中三栏统计（全量，不随勾选变化）
 * - 点击点位信息卡：高中（分类/指标/口径）、小学初中（梯队信号/判定依据）、普通（学段/区）
 * - 高德瓦片 GCJ-02 同坐标系；区边界 + 核心四区初始视野 + 半径随缩放
 */
import { computed, onActivated, onBeforeUnmount, onMounted, reactive, ref, watch, type Ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

/** 组件名：App.vue 的 KeepAlive 按此名只缓存本页 */
defineOptions({ name: 'MapView' });
import {
  buildAliasTable,
  matchTier1ByPoiName,
  normName,
  formatPrimarySignals,
  formatMiddleSignals,
  formatXiaoshengchuBrief,
  type SchoolStage,
  type Tier1School,
  type HighLevelSchool,
} from '@gz/shared';
import {
  primarySchools,
  middleSchools,
  highSchools,
  primaryTier1,
  middleTier1,
  highLevels,
  tier1Schools,
  middleTier1Schools,
  matchEnrollment,
  xiaoshengchuOf,
  schoolBadges,
} from '../data';

/* ========== 配置（与旧版 map/index.html 一致） ========== */
const DISTRICTS = [
  { name: '荔湾区', adcode: '440103', color: '#C0392B' },
  { name: '越秀区', adcode: '440104', color: '#B7950B' },
  { name: '海珠区', adcode: '440105', color: '#27AE60' },
  { name: '天河区', adcode: '440106', color: '#16A085' },
  { name: '白云区', adcode: '440111', color: '#2980B9' },
  { name: '黄埔区', adcode: '440112', color: '#6C3483' },
  { name: '番禺区', adcode: '440113', color: '#C2185B' },
];
const districtByAdcode = Object.fromEntries(DISTRICTS.map((d) => [d.adcode, d.name]));
const adcodeByDistrict = Object.fromEntries(DISTRICTS.map((d) => [d.name, d.adcode]));

const CLASS_CFG = {
  pN: { stage: 'primary', color: '#94A3B8', label: '小学·普通' },
  pT: { stage: 'primary', color: '#2563EB', label: '小学·口碑' },
  mN: { stage: 'middle', color: '#A8A29E', label: '初中·普通' },
  mT: { stage: 'middle', color: '#DC2626', label: '初中·口碑' },
  hN: { stage: 'high', color: '#64748B', label: '高中·普通' },
  hD: { stage: 'high', color: '#10B981', label: '高中·区属示范' },
  hM: { stage: 'high', color: '#F59E0B', label: '高中·省市属示范' },
} as const;
type ClsKey = keyof typeof CLASS_CFG;
const GLOW_COLOR: Record<string, string> = {
  primary: 'rgba(37,99,235,0.35)',
  middle: 'rgba(220,38,38,0.35)',
};

/* ========== 梯队/高中匹配表（构建一次，性能复用） ========== */
const tierTables = {
  primary: buildAliasTable(tier1Schools),
  middle: buildAliasTable(middleTier1Schools),
};
function tierOf(stage: 'primary' | 'middle', name: string, note?: string): Tier1School | undefined {
  // 新开办学校无成绩：不参与口碑/挂牌判定（数据层 note 标记「新开办（年份）·待首届成绩」，
  // 避免「广东实验中学天河学校」等独立法人新校因前缀匹配被误判为本部口碑校）
  if (note && note.includes('新开办')) return undefined;
  return matchTier1ByPoiName(name, stage === 'primary' ? tier1Schools : middleTier1Schools, tierTables[stage]);
}
/** 独立法人挂牌校（tier1_eligible=false，成绩未达标/无证据）不计入口碑学校 */
function isTierRecord(t?: Tier1School): boolean {
  return !!t && t.tier1_eligible !== false && (t.conclusion === '有支撑' || t.conclusion === '部分支撑');
}

const highTable = new Map<string, HighLevelSchool>();
for (const sc of highLevels.schools) {
  for (const k of [sc.name, ...(sc.aliases || []), ...(sc.campuses || [])]) {
    const nk = normName(k);
    if (nk && !highTable.has(nk)) highTable.set(nk, sc);
  }
}
function highRecord(pt: { school?: string; name: string }): HighLevelSchool | undefined {
  const key = normName(pt.school || pt.name);
  const rec = highTable.get(key);
  if (rec) return rec;
  // 兜底：点位名精确匹配
  const n = normName(pt.name);
  if (!n) return undefined;
  return highTable.get(n);
}
function highCls(rec?: HighLevelSchool): ClsKey {
  if (!rec) return 'hN';
  if (rec.category === '省市属示范') return 'hM';
  if (rec.category === '区属示范') return 'hD';
  return 'hN';
}

/* ========== 点位聚合 ========== */
interface Pt {
  name: string;
  lat: number;
  lng: number;
  adcode: string;
  stage: SchoolStage;
  cls: ClsKey;
  tier?: Tier1School | null; // 小学/初中梯队记录
  rec?: HighLevelSchool | null; // 高中分类记录
}

const allPoints: Pt[] = [];
const tierByName: Record<string, true> = {};
function buildPoints() {
  for (const s of primarySchools.schools) {
    if (!districtByAdcode[s.adcode]) continue;
    const t = tierOf('primary', s.name, s.note);
    allPoints.push({
      name: s.name, lat: s.lat, lng: s.lng, adcode: s.adcode,
      stage: 'primary', cls: isTierRecord(t) ? 'pT' : 'pN', tier: t ?? null,
    });
    if (t) tierByName[t.name] = true;
  }
  for (const s of middleSchools.schools) {
    if (!districtByAdcode[s.adcode]) continue;
    const t = tierOf('middle', s.name, s.note);
    allPoints.push({
      name: s.name, lat: s.lat, lng: s.lng, adcode: s.adcode,
      stage: 'middle', cls: isTierRecord(t) ? 'mT' : 'mN', tier: t ?? null,
    });
    if (t) tierByName[t.name] = true;
  }
  for (const s of highSchools.schools) {
    if (!districtByAdcode[s.adcode]) continue;
    const rec = highRecord(s);
    allPoints.push({
      name: s.name, lat: s.lat, lng: s.lng, adcode: s.adcode,
      stage: 'high', cls: highCls(rec), rec: rec ?? null,
    });
  }
  // 补点：tier1 内手工坐标（小学 3 所 + 初中 14 所），按名去重
  const addExtra = (snapshot: { districts: Record<string, { schools: Tier1School[] }> }, stage: 'primary' | 'middle') => {
    for (const sc of Object.values(snapshot.districts).flatMap((d) => d.schools)) {
      if (!sc.coords || tierByName[sc.name]) continue;
      allPoints.push({
        name: sc.name,
        lat: sc.coords.lat,
        lng: sc.coords.lng,
        adcode: adcodeByDistrict[sc.district ?? ''] || '',
        stage,
        cls: isTierRecord(sc) ? (stage === 'primary' ? 'pT' : 'mT') : (stage === 'primary' ? 'pN' : 'mN'),
        tier: sc,
      });
      tierByName[sc.name] = true;
    }
  };
  addExtra(primaryTier1, 'primary');
  addExtra(middleTier1, 'middle');
}

/* ========== 筛选状态（贝壳式浮层：区域/学段/分级 均多选） ========== */
const selectedDistricts = ref<Set<string>>(new Set(DISTRICTS.map((d) => d.adcode)));
const selectedStages = ref<Set<SchoolStage>>(new Set<SchoolStage>(['primary', 'middle', 'high']));
const selectedGrades = ref<Set<ClsKey>>(new Set(Object.keys(CLASS_CFG) as ClsKey[]));
const openMenu = ref<null | 'district' | 'stage' | 'grade'>(null);

const STAGE_LABEL: Record<SchoolStage, string> = { primary: '小学', middle: '初中', high: '高中' };
const STAGE_TABS: Array<{ v: SchoolStage; l: string }> = [
  { v: 'primary', l: '小学' },
  { v: 'middle', l: '初中' },
  { v: 'high', l: '高中' },
];
const GRADE_GROUPS: Array<{ title: string; items: Array<{ v: ClsKey; l: string }> }> = [
  { title: '小学', items: [{ v: 'pT', l: '口碑学校' }, { v: 'pN', l: '普通学校' }] },
  { title: '初中', items: [{ v: 'mT', l: '口碑学校' }, { v: 'mN', l: '普通学校' }] },
  { title: '高中', items: [
    { v: 'hM', l: '市重点（省市属示范）' },
    { v: 'hD', l: '区重点（区属示范）' },
    { v: 'hN', l: '普通高中' },
  ]},
];
const ALL_DISTRICT_ADCODES = DISTRICTS.map((d) => d.adcode);
const ALL_STAGES: SchoolStage[] = ['primary', 'middle', 'high'];
const ALL_GRADES = Object.keys(CLASS_CFG) as ClsKey[];

function toggleIn<T>(setRef: { value: Set<T> }, v: T) {
  const s = new Set(setRef.value);
  if (s.has(v)) s.delete(v); else s.add(v);
  setRef.value = s;
}
function flipSet<T>(setRef: { value: Set<T> }, all: T[]) {
  setRef.value = setRef.value.size === all.length ? new Set<T>() : new Set(all);
}
const districtAll = computed(() => selectedDistricts.value.size === ALL_DISTRICT_ADCODES.length);
const stageAll = computed(() => selectedStages.value.size === ALL_STAGES.length);
const gradeAll = computed(() => selectedGrades.value.size === ALL_GRADES.length);
const flipDistrictLabel = computed(() => (districtAll.value ? '全不选' : '全选'));
const flipStageLabel = computed(() => (stageAll.value ? '全不选' : '全选'));
const flipGradeLabel = computed(() => (gradeAll.value ? '全不选' : '全选'));

function toggleDistrictAd(ad: string) { toggleIn(selectedDistricts, ad); }
function toggleStageTab(v: SchoolStage) { toggleIn(selectedStages, v); }
function toggleGradeCls(v: ClsKey) { toggleIn(selectedGrades, v); }
function flipDistricts() { flipSet(selectedDistricts, ALL_DISTRICT_ADCODES); }
function flipStages() { flipSet(selectedStages, ALL_STAGES); }
function flipGrades() { flipSet(selectedGrades, ALL_GRADES); }

function isVisible(pt: Pt): boolean {
  if (!selectedDistricts.value.has(pt.adcode)) return false;
  if (!selectedStages.value.has(pt.stage)) return false;
  if (!selectedGrades.value.has(pt.cls)) return false;
  return true;
}
const builtAt = ref(0);
const visibleCount = computed(() => { void builtAt.value; return allPoints.filter(isVisible).length; });

/* ========== 学校搜索 ========== */
const kw = ref('');
const searchOpen = ref(false);
const searchResults = computed(() => {
  const k = kw.value.trim();
  if (!k) return [];
  return allPoints.filter((p) => p.name.includes(k)).slice(0, 12);
});
function badgesOf(pt: Pt) {
  return schoolBadges(pt.stage, { district: districtByAdcode[pt.adcode] || '', tier: pt.tier, rec: pt.rec, name: pt.name });
}
function pickResult(pt: Pt) {
  if (!map) return;
  map.flyTo([pt.lat, pt.lng], 15, { duration: 0.8 });
  showInfo(pt);
  kw.value = '';
  searchOpen.value = false;
}

/* ========== 地图 ========== */
const mapEl = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;
/** 渲染条目：点位 marker + 可选晕光，按筛选显隐 */
interface RenderedItem { pt: Pt; marker: L.CircleMarker; glow?: L.CircleMarker }
const rendered: RenderedItem[] = [];
const markers: L.CircleMarker[] = [];
let unionSW: { lat: number; lng: number } | null = null;
let unionNE: { lat: number; lng: number } | null = null;

function radiusForZoom(z: number): number {
  z = Math.round(z);
  if (z >= 15) return 10;
  if (z >= 14) return 9;
  if (z >= 13) return 8;
  if (z >= 12) return 7;
  if (z >= 11) return 6;
  return 5;
}
function markerStyle(cls: ClsKey, tier?: Tier1School | null) {
  const cfg = CLASS_CFG[cls];
  const s: L.CircleMarkerOptions = {
    radius: radiusForZoom(map?.getZoom() ?? 13),
    color: 'rgba(255,255,255,0.85)',
    weight: 1.2,
    fillColor: cfg.color,
    fillOpacity: 1,
    bubblingMouseEvents: false,
  };
  if (!cfg.stage || (cls !== 'pT' && cls !== 'mT' && cls !== 'hD' && cls !== 'hM')) {
    s.fillOpacity = 0.7;
  } else if (tier) {
    s.weight = tier.conclusion === '有支撑' ? 2.8 : 2.2;
  }
  if (tier && tier.tier1_eligible === false) {
    s.dashArray = '4 3';
    s.fillOpacity = 0.85;
  }
  return s;
}
function isTierCls(cls: ClsKey): boolean {
  return cls === 'pT' || cls === 'mT' || cls === 'hD' || cls === 'hM';
}
function renderPoints() {
  for (const pt of allPoints) {
    const m = L.circleMarker([pt.lat, pt.lng], markerStyle(pt.cls, pt.tier));
    const item: RenderedItem = { pt, marker: m };
    const tier = pt.tier;
    if (tier && tier.conclusion === '有支撑' && tier.tier1_eligible !== false) {
      item.glow = L.circleMarker([pt.lat, pt.lng], {
        radius: radiusForZoom(map?.getZoom() ?? 13) + 4,
        color: GLOW_COLOR[pt.stage],
        weight: 2,
        fill: false,
        interactive: false,
      });
    }
    m.bindTooltip(
      `${pt.name}${tier && tier.tier1_eligible === false ? ' · 挂牌校' : ''}`,
      { direction: 'top', offset: L.point(0, -8), opacity: 0.95, className: 'poi-tip' },
    );
    m.on('click', (e) => {
      if (e.originalEvent && 'stopPropagation' in e.originalEvent) e.originalEvent.stopPropagation();
      showInfo(pt);
    });
    rendered.push(item);
    markers.push(m);
  }
}
function applyFilters() {
  if (!map) return;
  for (const it of rendered) {
    const vis = isVisible(it.pt);
    const inMap = map.hasLayer(it.marker);
    if (vis && !inMap) {
      it.marker.addTo(map);
      if (it.glow) it.glow.addTo(map);
    } else if (!vis && inMap) {
      map.removeLayer(it.marker);
      if (it.glow && map.hasLayer(it.glow)) map.removeLayer(it.glow);
    }
  }
}
watch([selectedDistricts, selectedStages, selectedGrades], applyFilters);
function renderBoundaries() {
  for (const dd of primarySchools.districts || []) {
    const d = DISTRICTS.find((x) => x.adcode === dd.adcode);
    if (!d) continue;
    for (const path of dd.boundary || []) {
      const latlngs: Array<[number, number]> = [];
      for (const raw of path) {
        const [lng, lat] = raw as [number, number];
        latlngs.push([lat, lng]);
        if (!unionSW) { unionSW = { lat, lng }; unionNE = { lat, lng }; }
        else if (unionSW && unionNE) {
          unionSW.lat = Math.min(unionSW.lat, lat);
          unionSW.lng = Math.min(unionSW.lng, lng);
          unionNE.lat = Math.max(unionNE.lat, lat);
          unionNE.lng = Math.max(unionNE.lng, lng);
        }
      }
      L.polygon(latlngs, {
        color: d.color, weight: 1.2, opacity: 0.75,
        fillColor: d.color, fillOpacity: 0.05, interactive: false,
      }).addTo(map!);
    }
  }
}
const CORE_ADCODES: Record<string, boolean> = { '440103': true, '440104': true, '440105': true, '440106': true };
function coreCenter(): [number, number] | null {
  let sw: { lat: number; lng: number } | null = null;
  let ne: { lat: number; lng: number } | null = null;
  for (const dd of primarySchools.districts || []) {
    if (!CORE_ADCODES[dd.adcode]) continue;
    for (const path of dd.boundary || []) {
      for (const raw of path) {
        const [lng, lat] = raw as [number, number];
        if (!sw) { sw = { lat, lng }; ne = { lat, lng }; }
        else if (sw && ne) {
          sw.lat = Math.min(sw.lat, lat); sw.lng = Math.min(sw.lng, lng);
          ne.lat = Math.max(ne.lat, lat); ne.lng = Math.max(ne.lng, lng);
        }
      }
    }
  }
  return sw ? [(sw.lat + ne!.lat) / 2, (sw.lng + ne!.lng) / 2] : null;
}

onMounted(() => {
  if (!mapEl.value) return;
  buildPoints();
  const cc = coreCenter();
  map = L.map(mapEl.value, {
    center: cc ?? [23.16, 113.35],
    zoom: cc ? 13 : 10,
    minZoom: 9,
    maxZoom: 18,
    zoomSnap: 0.5,
    zoomControl: false,
    preferCanvas: true,
  });
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    subdomains: ['1', '2', '3', '4'],
    maxZoom: 18,
    attribution: '&copy; 高德地图',
  }).addTo(map);
  renderBoundaries();
  renderPoints();
  builtAt.value++;
  if (unionSW && unionNE) {
    map.setMaxBounds(L.latLngBounds([unionSW.lat, unionSW.lng], [unionNE.lat, unionNE.lng]).pad(0.5));
  }
  applyFilters();
  const focus = route.query.focus;
  if (typeof focus === 'string' && focus) focusSchool(focus);
  map.on('zoomend', () => {
    const r = radiusForZoom(map!.getZoom());
    for (const m of markers) m.setRadius(r);
  });
  map.on('click', () => closeInfo());
});

onBeforeUnmount(() => {
  map?.remove();
  map = null;
});

// keep-alive 缓存下从详情页返回时重新显示：容器尺寸恢复后重算地图，避免瓦片/点位错位
onActivated(() => {
  if (map) map.invalidateSize();
});

/* ========== 信息卡 ========== */
const active = ref<Pt | null>(null);
const route = useRoute();
const router = useRouter();
function showInfo(pt: Pt) { active.value = pt; }
function closeInfo() { active.value = null; }

/** 详情页"在地图中查看"：按校名定位并弹出信息卡 */
function focusSchool(name: string) {
  const pt = allPoints.find((p) => p.name === name) || allPoints.find((p) => p.name.includes(name));
  if (!pt || !map) return;
  map.flyTo([pt.lat, pt.lng], 15, { duration: 0.8 });
  showInfo(pt);
  // 定位后清掉 focus 参数：用户再点其他学校→详情→返回时，回到当前地图视图而非重新 flyTo 旧 focus
  router.replace({ query: {} });
}
watch(() => route.query.focus, (v) => { if (typeof v === 'string' && v) focusSchool(v); });
/** 小学招生条件行（2026 招生计划：班数 + 对口地段） */
function primaryEnrollRows(name: string): InfoRow[] {
  const en = matchEnrollment(name);
  if (!en) return [];
  const rows: InfoRow[] = [];
  if (en.plan_classes != null) rows.push({ label: '2026班数', value: `${en.plan_classes} 个班`, strong: true });
  if (en.zone) rows.push({ label: '招生地段', value: en.zone });
  return rows;
}

/** 小学升学路线行（全量 xiaoshengchu 真源，校名全等匹配，跨区同名按 adcode 消歧） */
function primaryLinkageRows(name: string, adcode?: string): InfoRow[] {
  const xs = xiaoshengchuOf(name, adcode);
  if (!xs || (!xs.direct_feed && !(xs.feed_junior_highs || []).length)) return [];
  return [{ label: '升学路线', value: formatXiaoshengchuBrief(xs) }];
}

interface InfoRow { label: string; value: string; strong?: boolean }
interface InfoModel {
  name: string;
  badges: { text: string; cls: string }[];
  head: string | null;
  rows: InfoRow[];
  note: string | null;
  link: { text: string; to: string } | null;
}

const infoModel = computed<InfoModel | null>(() => {
  const pt = active.value;
  if (!pt) return null;
  const districtName = districtByAdcode[pt.adcode] || '';
  const name = pt.name;
  const detailLink = { text: '查看学校详情 →', to: `/school/${pt.stage}/${encodeURIComponent(name)}` };
  if (pt.stage === 'high') {
    const rec = pt.rec;
    if (!rec) {
      return {
        name,
        badges: schoolBadges('high', { district: districtName, name }),
        head: null,
        rows: [
          { label: '学段', value: '高中' },
          { label: '所在区', value: districtName || '—' },
        ],
        note: '该点位暂未匹配到高中分类（可能为未收录学校）。',
        link: detailLink,
      };
    }
    const ind = rec.indicators || {};
    const rows: Array<{ label: string; value: string; strong?: boolean }> = [];
    const put = (k: string, label: string, strong = false) => {
      const v = ind[k];
      if (v !== undefined && v !== null && v !== '') rows.push({ label, value: String(v), strong });
    };
    // 侧边只展示概要，完整指标见学校详情页
    put('score_2025', '2025 中考录取线（户籍生）', true);
    put('tekong_2026', '特控线上线率 2026');
    put('gaofen_2026', '高分段 2026');
    return {
      name,
      badges: schoolBadges('high', { district: districtName, rec, name }),
      head: null,
      rows,
      note: '口径：录取线为官方发布；特控率/高分段为喜报或网传数据。完整出口数据见详情页。',
      link: detailLink,
    };
  }
  const tier = pt.tier;
  if (tier) {
    // 小学缩略面板优先展示招生条件（班数 + 对口地段）
    const enrollRows = pt.stage === 'primary' ? primaryEnrollRows(name) : [];
    // 小学升学路线取全量 xiaoshengchu（全等匹配）；口碑信号另缩略一条
    const linkageRows = pt.stage === 'primary' ? primaryLinkageRows(name, pt.adcode) : [];
    if (tier.tier1_eligible === false) {
      return {
        name,
        badges: schoolBadges(pt.stage, { district: districtName, tier, name }),
        head: '网传"口碑学校" · 独立法人，未计入口碑学校',
        rows: [
          ...enrollRows,
          ...linkageRows,
          ...(tier.exclude_reason ? [{ label: '未计入原因', value: tier.exclude_reason }] : []),
        ],
        note: null,
        link: detailLink,
      };
    }
    const head =
      '网传"口碑学校" · 民间口径非官方' +
      (tier.entity_relation === '同法人校区' ? ' · 与本部同一法人' : '');
    // 小学：升学路线（全量）+ 一条口碑信号（教育集团等）；初中：中考信号缩略一条
    const signalRows = pt.stage === 'primary'
      ? [...linkageRows, ...formatPrimarySignals(tier).slice(0, 1)]
      : formatMiddleSignals(tier).slice(0, 1);
    return {
      name,
      badges: schoolBadges(pt.stage, { district: districtName, tier, name }),
      head,
      rows: [...enrollRows, ...signalRows],
      note: '完整口碑信号与升学通道见详情页。',
      link: detailLink,
    };
  }
  return {
    name,
    badges: schoolBadges(pt.stage, { district: districtName, name }),
    head: null,
    rows: [
      { label: '学段', value: pt.stage === 'primary' ? '小学' : pt.stage === 'middle' ? '初中' : '高中' },
      { label: '所在区', value: districtName || '—' },
      ...(pt.stage === 'primary' ? primaryEnrollRows(name) : []),
      ...(pt.stage === 'primary' ? primaryLinkageRows(name, pt.adcode) : []),
    ],
    note: null,
    link: detailLink,
  };
});
</script>

<template>
  <section>
  <!-- 浮层：搜索 + 筛选（压在地图上方） -->
  <div class="float-panel">
    <div class="search-bar">
      <input v-model="kw" class="search-input" placeholder="搜索学校名，如：华南师范大学附属中学" @focus="searchOpen = true" />
      <ul v-if="searchOpen && kw.trim()" class="search-drop">
        <li v-for="r in searchResults" :key="r.name + r.adcode" @mousedown.prevent="pickResult(r)">
          <b>{{ r.name }}</b>
          <span class="s-badges"><span v-for="b in badgesOf(r)" :key="b.cls + b.text" class="badge sm" :class="b.cls">{{ b.text }}</span></span>
        </li>
        <li v-if="!searchResults.length" class="search-empty">无匹配学校</li>
      </ul>
    </div>

    <div class="filter-bar">
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'district' }" @click="openMenu = openMenu === 'district' ? null : 'district'">
          区域<em v-if="!districtAll" class="fb-badge">{{ selectedDistricts.size }}</em><span class="arr">▾</span>
        </button>
      </div>
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'stage' }" @click="openMenu = openMenu === 'stage' ? null : 'stage'">
          学段<em v-if="!stageAll" class="fb-badge">{{ selectedStages.size }}</em><span class="arr">▾</span>
        </button>
      </div>
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'grade' }" @click="openMenu = openMenu === 'grade' ? null : 'grade'">
          分级<em v-if="!gradeAll" class="fb-badge">{{ selectedGrades.size }}</em><span class="arr">▾</span>
        </button>
      </div>

      <!-- 区域多选 -->
      <div v-if="openMenu === 'district'" class="fb-pop">
        <div class="pop-chips">
          <button v-for="d in DISTRICTS" :key="d.adcode" class="pop-chip" :class="{ on: selectedDistricts.has(d.adcode) }" @click="toggleDistrictAd(d.adcode)">{{ d.name.replace('区', '') }}</button>
        </div>
        <div class="pop-foot">
          <button class="pop-link" @click="flipDistricts()">{{ flipDistrictLabel }}</button>
          <button class="pop-link" @click="openMenu = null">完成</button>
        </div>
      </div>
      <!-- 学段多选 -->
      <div v-if="openMenu === 'stage'" class="fb-pop">
        <div class="pop-chips">
          <button v-for="o in STAGE_TABS" :key="o.v" class="pop-chip" :class="{ on: selectedStages.has(o.v) }" @click="toggleStageTab(o.v)">{{ o.l }}</button>
        </div>
        <div class="pop-foot">
          <button class="pop-link" @click="flipStages()">{{ flipStageLabel }}</button>
          <button class="pop-link" @click="openMenu = null">完成</button>
        </div>
      </div>
      <!-- 分级多选（分组列表） -->
      <div v-if="openMenu === 'grade'" class="fb-pop">
        <div v-for="g in GRADE_GROUPS" :key="g.title" class="pop-group">
          <div class="pop-group-title">{{ g.title }}</div>
          <div class="pop-chips">
            <button v-for="o in g.items" :key="o.v" class="pop-chip" :class="{ on: selectedGrades.has(o.v) }" @click="toggleGradeCls(o.v)">{{ o.l }}</button>
          </div>
        </div>
        <div class="pop-foot">
          <button class="pop-link" @click="flipGrades()">{{ flipGradeLabel }}</button>
          <button class="pop-link" @click="openMenu = null">完成</button>
        </div>
      </div>
    </div>
  </div>

  <div v-if="openMenu || searchOpen" class="pop-mask" @click="openMenu = null; searchOpen = false;"></div>
  <div ref="mapEl" class="map"></div>
  <div class="map-count">当前显示 {{ visibleCount }} 所学校</div>

    <aside v-if="infoModel" class="school-info">
      <button class="si-close" aria-label="关闭" @click="closeInfo">×</button>
      <div class="si-name">{{ infoModel.name }}</div>
      <div class="si-tier">
        <span v-for="b in infoModel.badges" :key="b.cls + b.text" class="badge" :class="b.cls">{{ b.text }}</span>
        <span v-if="infoModel.head">{{ infoModel.head }}</span>
      </div>
      <div v-for="r in infoModel.rows" :key="r.label" class="si-row">
        <span>{{ r.label }}</span>
        <b v-if="r.strong">{{ r.value }}</b>
        <p v-else :class="{ 'si-clamp': r.label === '招生地段' || r.label === '升学路线' }">{{ r.value }}</p>
      </div>
      <div v-if="infoModel.note" class="si-src">{{ infoModel.note }}</div>
      <RouterLink v-if="infoModel.link" :to="infoModel.link.to" class="si-link">{{ infoModel.link.text }}</RouterLink>
    </aside>

    <p class="hint">拖动 / 滚轮 / 双指缩放查看。悬停显示校名，点击点位显示信息卡。独立法人挂牌校（虚线点）不计入口碑学校。高中分类口径：省市属示范 / 区属示范 / 普通（详见卡片内"口径"）。</p>
  </section>
</template>

<style scoped>
/* 浮层：搜索 + 筛选压在地图上方 */
section { position: relative; }
.float-panel { position: absolute; top: 10px; left: 10px; right: 10px; z-index: 1000; }
.search-bar { position: relative; margin-bottom: 8px; }
.search-input {
  width: 100%; box-sizing: border-box; border: 1px solid #e4e3dd; border-radius: 14px;
  background: rgba(255,255,255,0.97); padding: 11px 14px; font-size: 13.5px; outline: none;
  box-shadow: 0 2px 10px rgba(20,30,50,0.12);
}
.search-input:focus { border-color: #9bbbf4; }
.search-drop {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 1300;
  list-style: none; margin: 0; padding: 4px; background: #fff;
  border: 1px solid #e4e3dd; border-radius: 12px; box-shadow: 0 8px 28px rgba(20,30,50,0.16);
  max-height: 320px; overflow-y: auto;
}
.search-drop li {
  display: flex; justify-content: space-between; align-items: center; gap: 10px;
  padding: 9px 10px; font-size: 13px; cursor: pointer; border-radius: 8px;
}
.search-drop li:hover { background: #f2f7ff; }
.search-drop li b { font-weight: 600; color: #1a1b1c; }
.search-drop li .s-badges { color: #6b7280; font-size: 11.5px; white-space: nowrap; }
.search-empty { color: #6b7280; font-size: 12.5px; text-align: center; }
.search-empty:hover { background: none !important; }

/* 筛选器行（贝壳式，弹层横跨整行） */
.filter-bar {
  position: relative; display: flex; gap: 8px;
  background: rgba(255,255,255,0.97); border: 1px solid #e4e3dd;
  border-radius: 14px; padding: 8px;
  box-shadow: 0 2px 10px rgba(20,30,50,0.12);
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
  position: absolute; top: calc(100% + 6px); left: 0; right: 0; z-index: 1300;
  background: #fff; border: 1px solid #e4e3dd; border-radius: 12px;
  box-shadow: 0 8px 28px rgba(20,30,50,0.16); padding: 12px;
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
.pop-foot { display: flex; justify-content: space-between; margin-top: 10px; padding-top: 8px; border-top: 1px dashed #e4e3dd; }
.pop-link { border: none; background: none; color: #1a6bd6; font-size: 12.5px; cursor: pointer; padding: 4px 8px; }
.pop-mask { position: fixed; inset: 0; z-index: 900; background: rgba(0,0,0,0.02); }

.map-count {
  position: absolute; left: 10px; bottom: 12px; z-index: 50;
  background: rgba(255,255,255,0.94); border: 1px solid #e4e3dd; border-radius: 10px;
  padding: 5px 12px; font-size: 12px; color: #444; box-shadow: 0 1px 4px rgba(20,30,50,0.08);
}
.map { height: calc(100vh - 140px); min-height: 560px; border-radius: 14px; border: 1px solid #e4e3dd; z-index: 1; }
.hint { font-size: 12px; color: #6b7280; margin-top: 10px; line-height: 1.6; }

.school-info {
  position: fixed; right: 14px; bottom: 14px;
  width: 360px; max-width: calc(100vw - 28px); max-height: 62vh; overflow-y: auto;
  background: rgba(255,255,255,0.97); border: 1px solid #e4e3dd; border-radius: 14px;
  box-shadow: 0 6px 28px rgba(20,30,50,0.16); padding: 14px 16px 12px; z-index: 1100;
  font-size: 12.5px;
}
.si-close {
  position: absolute; top: 8px; right: 10px; border: none; background: none;
  font-size: 18px; line-height: 1; color: #8a93a3; cursor: pointer; padding: 4px 6px;
}
.si-close:hover { color: #1a1b1c; }
.si-name { font-size: 15px; font-weight: 700; padding-right: 26px; line-height: 1.4; }
.si-tier { margin-top: 8px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: #6b7280; }
.badge { font-size: 12px; font-weight: 700; color: #fff; border-radius: 6px; padding: 2px 9px; }
.badge.sm { font-size: 10.5px; padding: 1px 7px; }
.s-badges { display: inline-flex; gap: 4px; margin-left: 6px; }
.badge.b-district { background: #e5e7eb; color: #374151; }
.badge.b-stage { background: #dbeafe; color: #1e40af; }
.badge.b-tier { background: #e11d48; }
.badge.b-license { background: #4b5563; }
.badge.b-hcity { background: #b45309; }
.badge.b-hdist { background: #0f766e; }
.badge.b-full { background: #e11d48; }
.badge.b-part { background: #f59e0b; }
.badge.b-none { background: #8a94a6; }
.badge.tier-full { background: #e11d48; }
.badge.tier-part { background: #f59e0b; }
.badge.tier-none { background: #8a94a6; }
.badge.license { background: #4b5563; }
.badge.h-city { background: #b45309; }
.badge.h-dist { background: #0f766e; }
.badge.h-normal { background: #57534e; }
.si-row { margin-top: 8px; display: flex; gap: 8px; }
.si-row > span:first-child { flex: none; width: 88px; color: #6b7280; font-size: 11.5px; padding-top: 1px; }
.si-row > b { font-weight: 600; }
.si-row p { margin: 0; line-height: 1.65; }
/* 浮层长文本（招生地段 / 升学路线）：最多展示 4 行，超出省略；完整内容见详情页 */
.si-row p.si-clamp {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  overflow: hidden;
}
.si-src { margin-top: 10px; padding-top: 8px; border-top: 1px dashed #d6d4cc; font-size: 10.5px; color: #9aa0a6; line-height: 1.6; }
.si-link {
  display: inline-block; margin-top: 10px; color: #1a6bd6; text-decoration: none;
  font-size: 12.5px; font-weight: 600; border-bottom: 1px dashed #b9cdea;
}
.si-link:hover { text-decoration: underline; }

@media (max-width: 600px) {
  .school-info { right: 10px; bottom: 10px; left: 10px; width: auto; max-height: 55vh; }
  .map { height: 480px; }
}
</style>

<style>
.poi-tip { font-size: 12px; }
</style>
