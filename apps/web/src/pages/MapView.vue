<script setup lang="ts">
/**
 * 七区中小学·高中分布地图（Vue3 + Leaflet，功能对齐旧版 map/index.html）：
 * - 三类点位配色：小学紫 / 初中红 / 高中绿；多学部学校（同 school_id）圆点垂直分色；点位统一样式
 * - 7 类筛选 + 全选/全不选；点击点位有选中态（浮层关闭后消失）
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
  middlePrimaryFeed,
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
/** 学段点色（用户要求：小学一种颜色、初中一种颜色、高中一种颜色；小学紫避免与品牌蓝撞色） */
const STAGE_COLOR: Record<SchoolStage, string> = {
  primary: '#8B5CF6', // 小学 · 紫
  middle: '#DC2626', // 初中 · 红
  high: '#10B981', // 高中 · 绿
};
/** 学段优先级：多学部点主学部取最高（信息卡用主学部） */
const STAGE_PRIORITY: Record<SchoolStage, number> = { primary: 0, middle: 1, high: 2 };

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

/* ========== 点位聚合（多学部学校按 school_id 合并为一个点） ========== */
interface Pt {
  name: string;
  lat: number;
  lng: number;
  adcode: string;
  /** 该点位覆盖的学部（升序：小学→初中→高中，决定垂直分色顺序） */
  stages: SchoolStage[];
  /** 各学部自己的分级类（口碑/普通、示范/普通） */
  clsOf: Record<SchoolStage, ClsKey>;
  /** 各学部梯队记录（小学/初中口碑校） */
  tierOf: Partial<Record<SchoolStage, Tier1School | null>>;
  /** 高中分类记录（高中学部） */
  rec: HighLevelSchool | null;
  /** 主学部：stages 中优先级最高的（信息卡/描边/晕光判定用） */
  mainStage: SchoolStage;
  /** 主学部梯队记录（= tierOf[mainStage]） */
  tier: Tier1School | null;
}

const allPoints: Pt[] = [];
const ptByKey = new Map<string, Pt>();
const tierByName: Record<string, true> = {};
function addSchool(
  s: { name: string; lat: number; lng: number; adcode: string; school_id?: string; note?: string },
  stage: SchoolStage,
  cls: ClsKey,
  tier: Tier1School | null,
  rec: HighLevelSchool | null,
) {
  if (!districtByAdcode[s.adcode]) return;
  // 同 school_id = 同校区多学部；补点无 school_id 时按名合并
  const key = s.school_id || `name:${s.name}`;
  let pt = ptByKey.get(key);
  if (!pt) {
    pt = {
      name: s.name, lat: s.lat, lng: s.lng, adcode: s.adcode,
      stages: [], clsOf: {} as Record<SchoolStage, ClsKey>,
      tierOf: {}, rec: null, mainStage: stage, tier: null,
    };
    ptByKey.set(key, pt);
    allPoints.push(pt);
  }
  if (!pt.stages.includes(stage)) {
    pt.stages.push(stage);
    pt.clsOf[stage] = cls;
    pt.tierOf[stage] = tier;
  }
  if (stage === 'high' && rec) pt.rec = rec;
}
function buildPoints() {
  for (const s of primarySchools.schools) {
    const t = tierOf('primary', s.name, s.note);
    addSchool(s, 'primary', isTierRecord(t) ? 'pT' : 'pN', t ?? null, null);
    if (t) tierByName[t.name] = true;
  }
  for (const s of middleSchools.schools) {
    const t = tierOf('middle', s.name, s.note);
    addSchool(s, 'middle', isTierRecord(t) ? 'mT' : 'mN', t ?? null, null);
    if (t) tierByName[t.name] = true;
  }
  for (const s of highSchools.schools) {
    const rec = highRecord(s);
    addSchool(s, 'high', highCls(rec), null, rec ?? null);
  }
  // 补点：tier1 内手工坐标（小学 3 所 + 初中 14 所），按名去重
  const addExtra = (snapshot: { districts: Record<string, { schools: Tier1School[] }> }, stage: 'primary' | 'middle') => {
    for (const sc of Object.values(snapshot.districts).flatMap((d) => d.schools)) {
      if (!sc.coords || tierByName[sc.name]) continue;
      addSchool(
        { name: sc.name, lat: sc.coords.lat, lng: sc.coords.lng, adcode: adcodeByDistrict[sc.district ?? ''] || '' },
        stage,
        isTierRecord(sc) ? (stage === 'primary' ? 'pT' : 'mT') : (stage === 'primary' ? 'pN' : 'mN'),
        sc,
        null,
      );
      tierByName[sc.name] = true;
    }
  };
  addExtra(primaryTier1, 'primary');
  addExtra(middleTier1, 'middle');
  // 统一：stages 升序、主学部取最高优先级、主学部 tier
  for (const pt of allPoints) {
    pt.stages.sort((a, b) => STAGE_PRIORITY[a] - STAGE_PRIORITY[b]);
    pt.mainStage = pt.stages[pt.stages.length - 1]!;
    pt.tier = pt.tierOf[pt.mainStage] ?? null;
  }
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
const GRADE_GROUPS: Array<{ title: string; stage: SchoolStage; items: Array<{ v: ClsKey; l: string }> }> = [
  { title: '小学', stage: 'primary', items: [{ v: 'pT', l: '口碑学校' }, { v: 'pN', l: '普通学校' }] },
  { title: '初中', stage: 'middle', items: [{ v: 'mT', l: '口碑学校' }, { v: 'mN', l: '普通学校' }] },
  { title: '高中', stage: 'high', items: [
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
  // 多学部点：任一学部在学段+分级筛选中可见即显示（色段固定展示全部学部）
  return pt.stages.some((s) => selectedStages.value.has(s) && selectedGrades.value.has(pt.clsOf[s]));
}
const builtAt = ref(0);

/* ========== 学校搜索 ========== */
const kw = ref('');
const searchOpen = ref(false);
const searchResults = computed(() => {
  const k = kw.value.trim();
  if (!k) return [];
  return allPoints.filter((p) => p.name.includes(k)).slice(0, 12);
});
function badgesOf(pt: Pt) {
  return schoolBadges(pt.mainStage, { district: districtByAdcode[pt.adcode] || '', tier: pt.tier, rec: pt.rec, name: pt.name });
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
interface RenderedItem { pt: Pt; marker: L.Marker }
const rendered: RenderedItem[] = [];
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
/** 单学部点：学段单色圆点，统一样式（不再区分口碑/普通/挂牌） */
function markerStyle(pt: Pt): L.CircleMarkerOptions {
  return {
    radius: radiusForZoom(map?.getZoom() ?? 13),
    color: 'rgba(255,255,255,0.85)',
    weight: 1.2,
    fillColor: STAGE_COLOR[pt.mainStage],
    fillOpacity: 0.9,
    bubblingMouseEvents: false,
  };
}
let iconUid = 0;
/** 选中态描边（品牌蓝，浮层打开时高亮当前点位） */
const SELECTED_COLOR = '#1a6bd6';
/** 多学部点：SVG 圆内垂直分色（2 段=上/下，3 段=上/中/下），白描边，统一样式 */
function buildMultiIcon(pt: Pt, r: number, selected = false): L.DivIcon {
  const size = r * 2;
  const center = size / 2;
  const rr = r - 0.6;
  const n = pt.stages.length;
  const uid = 'poiClip' + (++iconUid);
  const weight = selected ? 3.5 : 1.2;
  const stroke = selected ? SELECTED_COLOR : 'rgba(255,255,255,0.85)';
  const segs = pt.stages
    .map((st, i) => {
      const y = center - rr + (i * (rr * 2)) / n;
      return `<rect x="${center - rr}" y="${y}" width="${rr * 2}" height="${(rr * 2) / n}" fill="${STAGE_COLOR[st]}" opacity="0.9"/>`;
    })
    .join('');
  const html =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">` +
    `<defs><clipPath id="${uid}"><circle cx="${center}" cy="${center}" r="${rr}"/></clipPath></defs>` +
    `<circle cx="${center}" cy="${center}" r="${rr}" fill="none" stroke="${stroke}" stroke-width="${weight}"/>` +
    `<g clip-path="url(#${uid})">${segs}</g>` +
    `</svg>`;
  return L.divIcon({
    className: 'poi-multi',
    html,
    iconSize: L.point(size, size),
    iconAnchor: L.point(center, center),
  });
}
function renderPoints() {
  for (const pt of allPoints) {
    const m: L.Marker = (pt.stages.length === 1
      ? L.circleMarker([pt.lat, pt.lng], markerStyle(pt))
      : L.marker([pt.lat, pt.lng], { icon: buildMultiIcon(pt, radiusForZoom(map?.getZoom() ?? 13)) })) as unknown as L.Marker;
    const item: RenderedItem = { pt, marker: m };
    const tier = pt.tier;
    m.bindTooltip(
      `${pt.name}${tier && tier.tier1_eligible === false ? ' · 挂牌校' : ''}`,
      { direction: 'top', offset: L.point(0, -8), opacity: 0.95, className: 'poi-tip' },
    );
    m.on('click', (e) => {
      if (e.originalEvent && 'stopPropagation' in e.originalEvent) e.originalEvent.stopPropagation();
      showInfo(pt);
    });
    rendered.push(item);
  }
}
function applyFilters() {
  if (!map) return;
  for (const it of rendered) {
    const vis = isVisible(it.pt);
    const inMap = map.hasLayer(it.marker);
    if (vis && !inMap) {
      it.marker.addTo(map);
    } else if (!vis && inMap) {
      map.removeLayer(it.marker);
      // 选中的点被筛掉：清除选中态并关闭浮层，避免浮层指向地图上看不到的点
      if (it === activeItem) {
        clearSelection();
        active.value = null;
      }
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
    attributionControl: false,
    preferCanvas: true,
  });
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    subdomains: ['1', '2', '3', '4'],
    maxZoom: 18,
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
    for (const it of rendered) {
      if (it.pt.stages.length === 1) (it.marker as unknown as L.CircleMarker).setRadius(r);
      else it.marker.setIcon(buildMultiIcon(it.pt, r, it === activeItem));
    }
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

/** 当前选中点位（浮层联动）：浮层打开时点位高亮，关闭/切换时清除 */
let activeItem: RenderedItem | null = null;
function setSelected(item: RenderedItem, on: boolean) {
  if (item.pt.stages.length === 1) {
    const m = item.marker as unknown as L.CircleMarker;
    if (on) m.setStyle({ weight: 3.5, color: SELECTED_COLOR });
    else m.setStyle(markerStyle(item.pt));
  } else {
    item.marker.setIcon(buildMultiIcon(item.pt, radiusForZoom(map?.getZoom() ?? 13), on));
  }
}
function clearSelection() {
  if (activeItem) setSelected(activeItem, false);
  activeItem = null;
}
function showInfo(pt: Pt) {
  clearSelection();
  activeItem = rendered.find((it) => it.pt === pt) ?? null;
  if (activeItem) setSelected(activeItem, true);
  active.value = pt;
  // 点击点位：放大并居中到屏幕中央（多学部垂直分色在小缩放下看不清）
  if (map) {
    map.flyTo([pt.lat, pt.lng], Math.max(map.getZoom(), 16), { duration: 0.6 });
  }
}
function closeInfo() {
  clearSelection();
  active.value = null;
}

/** 详情页"在地图中查看"：按校名定位并弹出信息卡 */
function focusSchool(name: string) {
  const pt = allPoints.find((p) => p.name === name) || allPoints.find((p) => p.name.includes(name));
  if (!pt || !map) return;
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
/** 初中生源小学摘要行（全量反查；无公办对口时给提示） */
function middleFeedRows(name: string): InfoRow[] {
  const list = middlePrimaryFeed(name);
  if (!list.length) return [{ label: '生源小学', value: '无公办对口名单（民办校以摇号/直升为准）', strong: false }];
  const preview = list.slice(0, 3).map((r) => r.primary).join('、');
  const more = list.length > 3 ? ` 等 ${list.length} 所` : '';
  return [{ label: '生源小学', value: preview + more, strong: true }];
}

interface InfoRow { label: string; value: string; strong?: boolean }
interface InfoModel {
  name: string;
  badges: { text: string; cls: string }[];
  head: string | null;
  rows: InfoRow[];
  note: string | null;
  links: { text: string; to: string }[];
}

const infoModel = computed<InfoModel | null>(() => {
  const pt = active.value;
  if (!pt) return null;
  const districtName = districtByAdcode[pt.adcode] || '';
  const name = pt.name;
  // 详情跳转：单学部一个按钮；多学部（完中）按学部分别跳对应 tab
  const nameStages = [
    ...(primarySchools.schools.some((s) => normName(s.name) === normName(name)) ? ['primary'] : []),
    ...(middleSchools.schools.some((s) => normName(s.name) === normName(name)) ? ['middle'] : []),
    ...(highSchools.schools.some((s) => normName(s.name) === normName(name)) ? ['high'] : []),
  ];
  const STAGE_SHORT: Record<string, string> = { primary: '小学部', middle: '初中部', high: '高中部' };
  const detailLinks = nameStages.length > 1
    ? nameStages.map((s) => ({ text: `查看${STAGE_SHORT[s]}详情 →`, to: `/school/${encodeURIComponent(name)}?stage=${s}` }))
    : [{ text: '查看学校详情 →', to: `/school/${encodeURIComponent(name)}` }];
  if (pt.mainStage === 'high') {
    const rec = pt.rec;
    if (!rec) {
      return {
        name,
        badges: schoolBadges('high', { district: districtName, name }),
        head: null,
        rows: [
          { label: '学部', value: pt.stages.map((s) => STAGE_LABEL[s]).join('、') },
          { label: '所在区', value: districtName || '—' },
        ],
        note: '该点位暂未匹配到高中分类（可能为未收录学校）。',
        links: detailLinks,
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
      links: detailLinks,
    };
  }
  const tier = pt.tier;
  if (tier) {
    // 小学缩略面板优先展示招生条件（班数 + 对口地段）
    const enrollRows = pt.mainStage === 'primary' ? primaryEnrollRows(name) : [];
    // 小学升学路线取全量 xiaoshengchu（全等匹配）；口碑信号另缩略一条
    const linkageRows = pt.mainStage === 'primary' ? primaryLinkageRows(name, pt.adcode) : [];
    if (tier.tier1_eligible === false) {
      return {
        name,
        badges: schoolBadges(pt.mainStage, { district: districtName, tier, name }),
        head: '网传"口碑学校" · 独立法人，未计入口碑学校',
        rows: [
          ...enrollRows,
          ...linkageRows,
          ...(tier.exclude_reason ? [{ label: '未计入原因', value: tier.exclude_reason }] : []),
        ],
        note: null,
        links: detailLinks,
      };
    }
    const head =
      '网传"口碑学校" · 民间口径非官方' +
      (tier.entity_relation === '同法人校区' ? ' · 与本部同一法人' : '');
    // 小学：升学路线（全量）+ 一条口碑信号；初中：生源小学摘要 + 一条中考信号
    const signalRows = pt.mainStage === 'primary'
      ? [...linkageRows, ...formatPrimarySignals(tier).slice(0, 1)]
      : [...middleFeedRows(name), ...formatMiddleSignals(tier).slice(0, 1)];
    return {
      name,
      badges: schoolBadges(pt.mainStage, { district: districtName, tier, name }),
      head,
      rows: [...enrollRows, ...signalRows],
      note: '完整口碑信号与升学通道见详情页。',
      links: detailLinks,
    };
  }
  return {
    name,
    badges: schoolBadges(pt.mainStage, { district: districtName, name }),
    head: null,
    rows: [
      { label: '学部', value: pt.stages.map((s) => STAGE_LABEL[s]).join('、') },
      { label: '所在区', value: districtName || '—' },
      ...(pt.mainStage === 'primary' ? primaryEnrollRows(name) : []),
      ...(pt.mainStage === 'primary' ? primaryLinkageRows(name, pt.adcode) : []),
      ...(pt.mainStage === 'middle' ? middleFeedRows(name) : []),
    ],
    note: null,
    links: detailLinks,
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

  <!-- 图例：点位颜色含义 -->
  <div class="map-legend">
    <div class="lg-row"><span class="lg-dot" :style="{ background: STAGE_COLOR.primary }"></span>小学</div>
    <div class="lg-row"><span class="lg-dot" :style="{ background: STAGE_COLOR.middle }"></span>初中</div>
    <div class="lg-row"><span class="lg-dot" :style="{ background: STAGE_COLOR.high }"></span>高中</div>
    <div class="lg-row">
      <span class="lg-dot lg-multi"><i :style="{ background: STAGE_COLOR.middle }"></i><i :style="{ background: STAGE_COLOR.high }"></i></span>
      多学部
    </div>
  </div>

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
      <RouterLink v-for="l in infoModel.links" :key="l.to" :to="l.to" class="si-link" style="display:block;margin-top:6px;">{{ l.text }}</RouterLink>
    </aside>
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

/* 图例：学段颜色 */
.map-legend {
  position: absolute; left: 10px; bottom: 12px; z-index: 60;
  background: rgba(255,255,255,0.95); border: 1px solid #e4e3dd; border-radius: 10px;
  padding: 8px 12px; font-size: 11.5px; color: #444;
  box-shadow: 0 1px 4px rgba(20,30,50,0.08);
}
.lg-row { display: flex; align-items: center; gap: 7px; line-height: 1.7; }
.lg-dot { width: 12px; height: 12px; border-radius: 50%; flex: none; display: inline-block; }
.lg-multi { display: inline-flex; flex-direction: column; overflow: hidden; border: 1px solid rgba(0,0,0,0.15); }
.lg-multi i { flex: 1; }
.map { height: calc(100vh - 140px); min-height: 560px; border-radius: 14px; border: 1px solid #e4e3dd; z-index: 1; }
/* 缩小 Leaflet 右下角缩放控件（默认 30px 按钮） */
:deep(.leaflet-control-zoom) {
  border: none !important;
  border-radius: 8px !important;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(20,30,50,0.12);
}
:deep(.leaflet-control-zoom a) {
  width: 24px !important;
  height: 24px !important;
  line-height: 24px !important;
  font-size: 15px !important;
  border: 1px solid #e4e3dd !important;
  color: #1a1b1c !important;
  background: rgba(255,255,255,0.95) !important;
}
:deep(.leaflet-control-zoom a:hover) { background: #f2f7ff !important; }

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
/* 多学部 divIcon：去除 Leaflet 默认白底边框 */
.poi-multi { background: transparent !important; border: none !important; }
</style>
