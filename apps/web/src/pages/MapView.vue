<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  filterSchools,
  matchTier1ByPoiName,
  GZ_DISTRICTS,
  type Verdict,
} from '@gz/shared';
import { primarySchools, tier1Schools } from '../data';

const mapEl = ref<HTMLDivElement | null>(null);
const selected = ref<string[]>([]);
const info = ref('');

let map: L.Map | null = null;
let layer: L.LayerGroup | null = null;

const districts = GZ_DISTRICTS.map((d) => ({
  ...d,
  count: primarySchools.schools.filter((s) => s.adcode === d.adcode).length,
}));
const visibleCount = computed(() =>
  filterSchools(primarySchools.schools, { adcodes: selected.value }).length,
);

function tierOf(name: string): { verdict?: Verdict; color: string; label: string } {
  const hit = matchTier1ByPoiName(name, tier1Schools);
  if (!hit) return { color: '#98a1ac', label: '普通' };
  const mapV: Record<Verdict, { color: string; label: string }> = {
    有支撑: { color: '#2f7d1f', label: '有支撑' },
    部分支撑: { color: '#e8a33d', label: '部分支撑' },
    不支撑: { color: '#c9534f', label: '不支撑' },
  };
  return { verdict: hit.conclusion, ...mapV[hit.conclusion] };
}

function render() {
  if (!map || !layer) return;
  layer.clearLayers();
  const list = filterSchools(primarySchools.schools, { adcodes: selected.value });
  for (const s of list) {
    const t = tierOf(s.name);
    L.circleMarker([s.lat, s.lng], {
      radius: 4,
      color: t.color,
      weight: 1,
      fillColor: t.color,
      fillOpacity: 0.85,
    })
      .bindTooltip(`${s.name}${t.verdict ? ` · ${t.label}` : ''}`, {
        direction: 'top',
        offset: L.point(0, -6),
        className: 'poi-tip',
      })
      .addTo(layer);
  }
  info.value = `当前显示 ${list.length} 所小学${selected.value.length ? '（已按区筛选）' : ''}`;
}

function toggle(adcode: string) {
  selected.value = selected.value.includes(adcode)
    ? selected.value.filter((a) => a !== adcode)
    : [...selected.value, adcode];
  render();
}

onMounted(() => {
  if (!mapEl.value) return;
  map = L.map(mapEl.value, { center: [23.13, 113.3], zoom: 11 });
  L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    subdomains: ['1', '2', '3', '4'],
    attribution: '&copy; 高德地图',
    maxZoom: 18,
  }).addTo(map);
  layer = L.layerGroup().addTo(map);
  render();
});

onBeforeUnmount(() => {
  map?.remove();
  map = null;
});
</script>

<template>
  <section>
    <div class="toolbar">
      <button
        v-for="d in districts"
        :key="d.adcode"
        class="chip"
        :class="{ active: selected.includes(d.adcode) }"
        @click="toggle(d.adcode)"
      >
        {{ d.name }} <span class="chip-count">{{ d.count }}</span>
      </button>
    </div>
    <div class="legend">
      <span><i class="dot" style="background:#2f7d1f"></i>有支撑</span>
      <span><i class="dot" style="background:#e8a33d"></i>部分支撑</span>
      <span><i class="dot" style="background:#c9534f"></i>不支撑</span>
      <span><i class="dot" style="background:#98a1ac"></i>普通</span>
      <span class="legend-count">{{ info }}</span>
    </div>
    <div ref="mapEl" class="map"></div>
    <p class="hint">点位：广州 7 区小学 {{ primarySchools.schools.length }} 所（GCJ-02 / 高德瓦片）；梯队标注为民间口径核验，非官方评价。</p>
  </section>
</template>

<style scoped>
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.chip {
  border: 1px solid #d6d4cc; background: #fff; color: #1a1b1c;
  border-radius: 999px; padding: 6px 14px; font-size: 13px; cursor: pointer;
}
.chip.active { background: #3a5396; border-color: #3a5396; color: #fff; }
.chip-count { font-size: 11px; opacity: 0.75; }
.legend {
  display: flex; flex-wrap: wrap; align-items: center; gap: 14px;
  font-size: 12px; color: #444; margin-bottom: 8px;
}
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; }
.legend-count { margin-left: auto; color: #6b7280; }
.map { height: 560px; border-radius: 14px; border: 1px solid #e4e3dd; z-index: 1; }
.hint { font-size: 12px; color: #6b7280; margin-top: 10px; line-height: 1.6; }
</style>

<style>
.poi-tip { font-size: 12px; }
</style>
