<script setup lang="ts">
/**
 * 七区中小学·高中分布地图（Vue3 + Leaflet，功能对齐旧版 map/index.html）：
 * - 七类点位配色：小学普通/口碑、初中普通/口碑、高中普通/区属示范/省市属示范
 * - 有支撑加粗+晕光、部分支撑加粗、独立法人挂牌校虚线点
 * - 7 类筛选 + 全选/全不选；各区小学/初中/高中三栏统计（全量，不随勾选变化）
 * - 点击点位信息卡：高中（分类/指标/口径）、小学初中（梯队信号/判定依据）、普通（学段/区）
 * - 高德瓦片 GCJ-02 同坐标系；区边界 + 核心四区初始视野 + 半径随缩放
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  buildAliasTable,
  matchTier1ByPoiName,
  normName,
  formatPrimarySignals,
  formatMiddleSignals,
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
function tierOf(stage: 'primary' | 'middle', name: string): Tier1School | undefined {
  return matchTier1ByPoiName(name, stage === 'primary' ? tier1Schools : middleTier1Schools, tierTables[stage]);
}
/** 独立法人挂牌校（tier1_eligible=false）不计入口碑学校 */
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
    const t = tierOf('primary', s.name);
    allPoints.push({
      name: s.name, lat: s.lat, lng: s.lng, adcode: s.adcode,
      stage: 'primary', cls: isTierRecord(t) ? 'pT' : 'pN', tier: t ?? null,
    });
    if (t) tierByName[t.name] = true;
  }
  for (const s of middleSchools.schools) {
    if (!districtByAdcode[s.adcode]) continue;
    const t = tierOf('middle', s.name);
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

/* ========== 统计（全量，不随筛选变化） ========== */
const counts = reactive<Record<ClsKey, number>>({ pN: 0, pT: 0, mN: 0, mT: 0, hN: 0, hD: 0, hM: 0 });
const distStats = reactive<Array<{ name: string; p: number; m: number; h: number }>>(
  DISTRICTS.map((d) => ({ name: d.name, p: 0, m: 0, h: 0 })),
);
const totalText = computed(() => {
  const p = counts.pN + counts.pT;
  const m = counts.mN + counts.mT;
  const h = counts.hN + counts.hD + counts.hM;
  return `已标注 ${p + m + h} 所：小学 ${p} · 初中 ${m} · 高中 ${h}`;
});
function computeStats() {
  for (const k of Object.keys(counts) as ClsKey[]) counts[k] = 0;
  for (const d of distStats) { d.p = 0; d.m = 0; d.h = 0; }
  for (const pt of allPoints) {
    counts[pt.cls]++;
    const row = distStats.find((d) => d.name === districtByAdcode[pt.adcode]);
    if (!row) continue;
    if (pt.stage === 'primary') row.p++;
    else if (pt.stage === 'middle') row.m++;
    else row.h++;
  }
}

/* ========== 筛选状态 ========== */
const filters = reactive<Record<ClsKey, boolean>>({ pN: true, pT: true, mN: true, mT: true, hN: true, hD: true, hM: true });
const classList = Object.entries(CLASS_CFG) as Array<[ClsKey, { stage: string; color: string; label: string }]>;
function setAll(v: boolean) {
  for (const k of Object.keys(filters) as ClsKey[]) filters[k] = v;
  applyFilters();
}
function applyFilters() {
  if (!map) return;
  for (const k of Object.keys(filters) as ClsKey[]) {
    const g = groups[k];
    if (!g) continue;
    if (filters[k]) { if (!map.hasLayer(g)) g.addTo(map); }
    else if (map.hasLayer(g)) map.removeLayer(g);
  }
}

/* ========== 地图 ========== */
const mapEl = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;
const groups: Partial<Record<ClsKey, L.LayerGroup>> = {};
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
  for (const k of Object.keys(CLASS_CFG) as ClsKey[]) groups[k] = L.layerGroup();
  for (const pt of allPoints) {
    const g = groups[pt.cls]!;
    const m = L.circleMarker([pt.lat, pt.lng], markerStyle(pt.cls, pt.tier)).addTo(g);
    const tier = pt.tier;
    if (tier && tier.conclusion === '有支撑' && tier.tier1_eligible !== false) {
      L.circleMarker([pt.lat, pt.lng], {
        radius: radiusForZoom(map?.getZoom() ?? 13) + 4,
        color: GLOW_COLOR[pt.stage],
        weight: 2,
        fill: false,
        interactive: false,
      }).addTo(g);
    }
    m.bindTooltip(
      `${pt.name}${tier && tier.tier1_eligible === false ? ' · 挂牌校' : ''}`,
      { direction: 'top', offset: L.point(0, -8), opacity: 0.95, className: 'poi-tip' },
    );
    m.on('click', (e) => {
      if (e.originalEvent && 'stopPropagation' in e.originalEvent) e.originalEvent.stopPropagation();
      showInfo(pt);
    });
    markers.push(m);
  }
}
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
  computeStats();
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
  if (unionSW && unionNE) {
    map.setMaxBounds(L.latLngBounds([unionSW.lat, unionSW.lng], [unionNE.lat, unionNE.lng]).pad(0.5));
  }
  applyFilters();
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

/* ========== 信息卡 ========== */
const active = ref<Pt | null>(null);
function showInfo(pt: Pt) { active.value = pt; }
function closeInfo() { active.value = null; }

interface InfoRow { label: string; value: string; strong?: boolean }
interface InfoModel {
  name: string;
  badge: { text: string; cls: string } | null;
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
        badge: null,
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
      badge: { text: rec.category, cls: rec.category === '省市属示范' ? 'h-city' : rec.category === '区属示范' ? 'h-dist' : 'h-normal' },
      head: `${rec.demo || ''} · ${rec.affiliation || ''}`,
      rows,
      note: '口径：录取线为官方发布；特控率/高分段为喜报或网传数据。完整出口数据见详情页。',
      link: detailLink,
    };
  }
  const tier = pt.tier;
  if (tier) {
    const rows = pt.stage === 'primary' ? formatPrimarySignals(tier) : formatMiddleSignals(tier);
    if (tier.tier1_eligible === false) {
      return {
        name,
        badge: { text: '独立法人挂牌校', cls: 'license' },
        head: '网传"口碑学校" · 独立法人，未计入口碑学校',
        rows: tier.exclude_reason ? [{ label: '未计入原因', value: tier.exclude_reason }] : [],
        note: null,
        link: detailLink,
      };
    }
    const head =
      '网传"口碑学校" · 民间口径非官方' +
      (tier.entity_relation === '同法人校区' ? ' · 与本部同一法人' : '');
    return {
      name,
      badge: {
        text: tier.conclusion,
        cls: tier.conclusion === '有支撑' ? 'tier-full' : tier.conclusion === '部分支撑' ? 'tier-part' : 'tier-none',
      },
      head,
      rows: rows.slice(0, 2),
      note: '完整口碑信号与升学通道见详情页。',
      link: detailLink,
    };
  }
  return {
    name,
    badge: null,
    head: null,
    rows: [
      { label: '学段', value: pt.stage === 'primary' ? '小学' : pt.stage === 'middle' ? '初中' : '高中' },
      { label: '所在区', value: districtName || '—' },
    ],
    note: null,
    link: detailLink,
  };
});
</script>

<template>
  <section>
    <div class="toolbar">
      <label v-for="[k, c] in classList" :key="k" class="f-row">
        <input type="checkbox" v-model="filters[k]" @change="applyFilters" />
        <i class="dot" :style="{ background: c.color }"></i>
        <span>{{ c.label }}</span>
        <span class="f-count">{{ counts[k] }}</span>
      </label>
      <div class="f-btns">
        <button @click="setAll(true)">全选</button>
        <button @click="setAll(false)">全不选</button>
      </div>
    </div>

    <div class="dist-stats">
      <div class="block-title">各区学校 · 小学 / 初中 / 高中</div>
      <div class="d-heads"><span></span><span>小学</span><span>初中</span><span>高中</span></div>
      <div v-for="d in distStats" :key="d.name" class="d-row">
        <span class="d-name">{{ d.name.replace('区', '') }}</span>
        <span class="d-p">{{ d.p }}</span><span class="d-m">{{ d.m }}</span><span class="d-h">{{ d.h }}</span>
      </div>
    </div>

    <div class="status">{{ totalText }}</div>
    <div ref="mapEl" class="map"></div>

    <aside v-if="infoModel" class="school-info">
      <button class="si-close" aria-label="关闭" @click="closeInfo">×</button>
      <div class="si-name">{{ infoModel.name }}</div>
      <div v-if="infoModel.badge" class="si-tier">
        <span class="badge" :class="infoModel.badge.cls">{{ infoModel.badge.text }}</span>
        <span>{{ infoModel.head }}</span>
      </div>
      <div v-else-if="infoModel.head" class="si-tier"><span>{{ infoModel.head }}</span></div>
      <div v-for="r in infoModel.rows" :key="r.label" class="si-row">
        <span>{{ r.label }}</span>
        <b v-if="r.strong">{{ r.value }}</b>
        <p v-else>{{ r.value }}</p>
      </div>
      <div v-if="infoModel.note" class="si-src">{{ infoModel.note }}</div>
      <RouterLink v-if="infoModel.link" :to="infoModel.link.to" class="si-link">{{ infoModel.link.text }}</RouterLink>
    </aside>

    <p class="hint">拖动 / 滚轮 / 双指缩放查看。悬停显示校名，点击点位显示信息卡。独立法人挂牌校（虚线点）不计入口碑学校。高中分类口径：省市属示范 / 区属示范 / 普通（详见卡片内"口径"）。</p>
  </section>
</template>

<style scoped>
.toolbar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 4px 14px;
  background: rgba(255,255,255,0.94); border: 1px solid #e4e3dd;
  border-radius: 14px; padding: 10px 14px; margin-bottom: 10px;
}
.f-row { display: flex; align-items: center; gap: 6px; font-size: 12.5px; cursor: pointer; user-select: none; }
.f-row input { width: 13px; height: 13px; accent-color: #2563eb; cursor: pointer; }
.dot { width: 9px; height: 9px; border-radius: 50%; box-shadow: 0 0 0 1.5px rgba(255,255,255,0.9), 0 1px 2px rgba(0,0,0,0.25); }
.f-count { margin-left: auto; color: #6b7280; font-variant-numeric: tabular-nums; }
.f-btns { display: flex; gap: 6px; margin-left: auto; }
.f-btns button {
  font-size: 11.5px; padding: 3px 12px; border: 1px solid #d6d4cc; background: #fff;
  border-radius: 7px; color: #1a1b1c; cursor: pointer;
}
.f-btns button:hover { background: #f2f7ff; border-color: #9bbbf4; }

.dist-stats {
  background: rgba(255,255,255,0.94); border: 1px solid #e4e3dd;
  border-radius: 14px; padding: 10px 14px; margin-bottom: 10px;
}
.block-title { font-size: 11px; color: #6b7280; font-weight: 600; letter-spacing: 0.06em; margin-bottom: 6px; }
.d-heads, .d-row {
  display: grid; grid-template-columns: 1fr 46px 46px 46px;
  column-gap: 6px; font-size: 12px; align-items: center;
}
.d-heads { color: #6b7280; font-size: 10.5px; font-weight: 600; text-align: right; }
.d-row { padding: 1px 0; }
.d-name { color: #6b7280; }
.d-p, .d-m, .d-h { text-align: right; font-variant-numeric: tabular-nums; }
.d-p { color: #2563eb; } .d-m { color: #dc2626; } .d-h { color: #f59e0b; }

.status { font-size: 13px; color: #444; margin-bottom: 8px; }
.map { height: 620px; border-radius: 14px; border: 1px solid #e4e3dd; z-index: 1; }
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
