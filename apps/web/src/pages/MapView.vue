<script setup lang="ts">
/**
 * 七区中小学·高中分布地图（Vue3 + Leaflet）：
 * - 业务逻辑（点位构建/筛选状态机/信息卡模型/搜索）来自 @gz/shared domain/map，双端单点维护
 * - 本组件只保留：地图渲染（Leaflet）、选中态高亮、底部抽屉交互、筛选浮层 UI
 * - 信息卡为底部抽屉（与小程序 cover-view 抽屉对齐，2026-09-11 决策）
 */
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

/** 组件名：App.vue 的 KeepAlive 按此名只缓存本页 */
defineOptions({ name: 'MapView' });
import {
  DISTRICTS,
  STAGE_COLOR,
  STAGE_LABEL,
  STAGE_TABS,
  GRADE_GROUPS,
  districtByAdcode,
  initialFilterState,
  toggleDistrict,
  toggleStage,
  toggleGrade,
  flipDistricts,
  flipStages,
  flipGrades,
  districtAll,
  stageAll,
  gradeAll,
  isVisible,
  searchSchools,
  buildInfoModel,
  type SchoolStage,
  type ClsKey,
  type MapPointFull,
} from '@gz/shared';
import { mapPoints, repository } from '../data';

/* ========== 筛选状态（共享纯 TS 状态机，Web 用 ref 承载响应式） ========== */
const filterState = initialFilterState();
const selectedDistricts = ref(filterState.selectedDistricts);
const selectedStages = ref(filterState.selectedStages);
const selectedGrades = ref(filterState.selectedGrades);
const openMenu = ref<null | 'district' | 'stage' | 'grade'>(null);
const state = () => ({
  selectedDistricts: selectedDistricts.value,
  selectedStages: selectedStages.value,
  selectedGrades: selectedGrades.value,
});
function toggleDistrictAd(ad: string) { selectedDistricts.value = toggleDistrict(state(), ad).selectedDistricts; }
function toggleStageTab(v: SchoolStage) { selectedStages.value = toggleStage(state(), v).selectedStages; }
function toggleGradeCls(v: ClsKey) { selectedGrades.value = toggleGrade(state(), v).selectedGrades; }
function flipDistrictSet() { selectedDistricts.value = flipDistricts(state()).selectedDistricts; }
function flipStageSet() { selectedStages.value = flipStages(state()).selectedStages; }
function flipGradeSet() { selectedGrades.value = flipGrades(state()).selectedGrades; }
const districtAllOn = computed(() => districtAll(state()));
const stageAllOn = computed(() => stageAll(state()));
const gradeAllOn = computed(() => gradeAll(state()));
const flipDistrictLabel = computed(() => (districtAllOn.value ? '全不选' : '全选'));
const flipStageLabel = computed(() => (stageAllOn.value ? '全不选' : '全选'));
const flipGradeLabel = computed(() => (gradeAllOn.value ? '全不选' : '全选'));
function isVisiblePt(pt: MapPointFull): boolean { return isVisible(state(), pt); }

/* ========== 学校搜索 ========== */
const kw = ref('');
const searchOpen = ref(false);
const searchResults = computed(() => searchSchools(mapPoints, kw.value));
function badgesOf(pt: MapPointFull) {
  return repository.schoolBadges(pt.mainStage, { district: districtByAdcode[pt.adcode] || '', tier: pt.tier, rec: pt.rec, name: pt.name });
}
function pickResult(pt: MapPointFull) {
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
interface RenderedItem { pt: MapPointFull; marker: L.Marker }
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
function markerStyle(pt: MapPointFull): L.CircleMarkerOptions {
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
/** 选中态描边（品牌蓝，抽屉打开时高亮当前点位） */
const SELECTED_COLOR = '#1a6bd6';
/** 多学部点：SVG 圆内垂直分色（2 段=上/下，3 段=上/中/下），白描边，统一样式 */
function buildMultiIcon(pt: MapPointFull, r: number, selected = false): L.DivIcon {
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
  for (const pt of mapPoints) {
    const m: L.Marker = (pt.stages.length === 1
      ? L.circleMarker([pt.lat, pt.lng], markerStyle(pt))
      : L.marker([pt.lat, pt.lng], { icon: buildMultiIcon(pt, radiusForZoom(map?.getZoom() ?? 13)) })) as unknown as L.Marker;
    const item: RenderedItem = { pt, marker: m };
    m.bindTooltip(pt.name, { direction: 'top', offset: L.point(0, -8), opacity: 0.95, className: 'poi-tip' });
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
    const vis = isVisiblePt(it.pt);
    const inMap = map.hasLayer(it.marker);
    if (vis && !inMap) {
      it.marker.addTo(map);
    } else if (!vis && inMap) {
      map.removeLayer(it.marker);
      // 选中的点被筛掉：清除选中态并关闭抽屉，避免抽屉指向地图上看不到的点
      if (it === activeItem) {
        clearSelection();
        active.value = null;
      }
    }
  }
}
watch([selectedDistricts, selectedStages, selectedGrades], applyFilters);
function renderBoundaries() {
  for (const dd of repository.schools.primary.districts || []) {
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
  for (const dd of repository.schools.primary.districts || []) {
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

/* ========== 信息卡（底部抽屉，与小程序 cover-view 抽屉对齐） ========== */
const active = ref<MapPointFull | null>(null);
const route = useRoute();
const router = useRouter();

/** 当前选中点位（抽屉联动）：打开时点位高亮，关闭/切换时清除 */
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
function showInfo(pt: MapPointFull) {
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
  const pt = mapPoints.find((p) => p.name === name) || mapPoints.find((p) => p.name.includes(name));
  if (!pt || !map) return;
  showInfo(pt);
  // 定位后清掉 focus 参数：用户再点其他学校→详情→返回时，回到当前地图视图而非重新 flyTo 旧 focus
  router.replace({ query: {} });
}
watch(() => route.query.focus, (v) => { if (typeof v === 'string' && v) focusSchool(v); });

/** 信息卡模型（共享 buildInfoModel，双端一致） */
const infoModel = computed(() => (active.value ? buildInfoModel(active.value, repository) : null));
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
          区域<em v-if="!districtAllOn" class="fb-badge">{{ selectedDistricts.size }}</em><span class="arr">▾</span>
        </button>
      </div>
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'stage' }" @click="openMenu = openMenu === 'stage' ? null : 'stage'">
          学段<em v-if="!stageAllOn" class="fb-badge">{{ selectedStages.size }}</em><span class="arr">▾</span>
        </button>
      </div>
      <div class="fb-col">
        <button class="fb-btn" :class="{ on: openMenu === 'grade' }" @click="openMenu = openMenu === 'grade' ? null : 'grade'">
          分级<em v-if="!gradeAllOn" class="fb-badge">{{ selectedGrades.size }}</em><span class="arr">▾</span>
        </button>
      </div>

      <!-- 区域多选 -->
      <div v-if="openMenu === 'district'" class="fb-pop">
        <div class="pop-chips">
          <button v-for="d in DISTRICTS" :key="d.adcode" class="pop-chip" :class="{ on: selectedDistricts.has(d.adcode) }" @click="toggleDistrictAd(d.adcode)">{{ d.name.replace('区', '') }}</button>
        </div>
        <div class="pop-foot">
          <button class="pop-link" @click="flipDistrictSet()">{{ flipDistrictLabel }}</button>
          <button class="pop-link" @click="openMenu = null">完成</button>
        </div>
      </div>
      <!-- 学段多选 -->
      <div v-if="openMenu === 'stage'" class="fb-pop">
        <div class="pop-chips">
          <button v-for="o in STAGE_TABS" :key="o.v" class="pop-chip" :class="{ on: selectedStages.has(o.v) }" @click="toggleStageTab(o.v)">{{ o.l }}</button>
        </div>
        <div class="pop-foot">
          <button class="pop-link" @click="flipStageSet()">{{ flipStageLabel }}</button>
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
          <button class="pop-link" @click="flipGradeSet()">{{ flipGradeLabel }}</button>
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

  <!-- 底部抽屉信息卡（对齐小程序 cover-view 抽屉） -->
  <div v-if="infoModel" class="si-mask" @click="closeInfo"></div>
  <aside v-if="infoModel" class="school-info">
    <div class="si-handle"></div>
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

/* 底部抽屉信息卡（对齐小程序 cover-view 抽屉） */
.si-mask {
  position: fixed; inset: 0; z-index: 1050;
  background: rgba(15,23,42,0.25);
}
.school-info {
  position: fixed; left: 50%; transform: translateX(-50%); bottom: 12px;
  width: min(720px, calc(100vw - 24px)); max-height: 62vh; overflow-y: auto;
  background: rgba(255,255,255,0.98); border: 1px solid #e4e3dd;
  border-radius: 16px 16px 14px 14px; box-shadow: 0 -6px 28px rgba(20,30,50,0.18);
  padding: 8px 16px 12px; z-index: 1100;
  font-size: 12.5px;
}
.si-handle {
  width: 44px; height: 4px; border-radius: 2px; background: #d6d4cc;
  margin: 0 auto 8px;
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
.si-row { margin-top: 8px; display: flex; gap: 8px; }
.si-row > span:first-child { flex: none; width: 88px; color: #6b7280; font-size: 11.5px; padding-top: 1px; }
.si-row > b { font-weight: 600; }
.si-row p { margin: 0; line-height: 1.65; }
/* 抽屉长文本（招生地段 / 升学路线）：最多展示 4 行，超出省略；完整内容见详情页 */
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
  .school-info { width: calc(100vw - 12px); bottom: 6px; max-height: 58vh; }
  .map { height: 480px; }
}
</style>

<style>
.poi-tip { font-size: 12px; }
/* 多学部 divIcon：去除 Leaflet 默认白底边框 */
.poi-multi { background: transparent !important; border: none !important; }
</style>
