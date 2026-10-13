/**
 * 首页 marker 图标生成（构建期）：按 @gz/shared 学段分色唯一真源生成 PNG（与 Web MapView 共用，2026-09-30 双端统一）。
 * 与已下线的老地图页 marker 生成脚本（gen-markers.mjs）同源逻辑，仅保留首页一套产物。
 * 产物：apps/miniprogram/assets/markers-index/
 *   普通 marker-{p|m|h|pm|ph|mh|pmh}.png + 同名 -sel.png（选中态，知性蓝光晕）
 */
import { deflateSync, inflateSync } from 'node:zlib';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const require = createRequire(import.meta.url);

// 颜色唯一真源：@gz/shared（STAGE_COLOR / MARKER_SELECTED_COLOR，与 Web MapView 共用；build:mp 前置已构建 shared）
const { STAGE_COLOR, MARKER_SELECTED_COLOR } = require(join(ROOT, 'packages', 'shared', 'dist', 'cjs', 'index.js'));

// 高清化：源图从 48px 提升到 120px（SCALE=2.5）。真机 devicePixelRatio 多为 2~3，
// 显示 38px 需 ~114px 源图，旧 48px 源被放大→糊（用户反馈「小圆圈放大就糊」）。
// 显示尺寸（28/38 逻辑 px）由 index.js 的 MARKER_OFF/MARKER_ON 控制、与本源分辨率无关——
// 现在 120px 源按 28/38 显示是「缩」而非「放」，边缘自然清晰（与 UI 稿矢量画法对齐）。
const SCALE = 2.5;
const SIZE = Math.round(48 * SCALE);   // 120
const D = 30 * SCALE;
const STROKE = '#FFFFFF';
const FILL_ALPHA = 0.92;
const STROKE_W = 1.4 * SCALE;        // 常态白描边
const SEL_STROKE_W = 2.2 * SCALE;    // 选中态白描边（略加粗，让彩色圆点更实）
// 选中态「知性蓝光晕」：软光晕 + 外缘实心环，明显区别于常态白描边圆点。
// 几何均按 SCALE 放大，保持与旧 48px 版完全一致的视觉比例（只是更清晰）。
const HALO_IN = 16.0 * SCALE;        // 光晕内缘半径（圆点 r=15·SCALE，留 1px 呼吸位）
const HALO_MID = 20.5 * SCALE;       // 软光晕 → 实心外环 分界
const HALO_OUT = 23.0 * SCALE;       // 光晕外缘半径（离 120px 画布边 = 2.5px）
const HALO_GLOW_A = 0.42;            // 光晕内缘不透明度
const HALO_RING_A = 0.95;            // 外缘实心环不透明度

/* ---------- PNG 编码（最小实现） ---------- */
const CRC_TABLE = (() => {
  const t = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c;
  }
  return t;
})();
function crc32(buf) {
  let c = 0xffffffff;
  for (const b of buf) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const t = Buffer.from(type, 'ascii');
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([t, data])));
  return Buffer.concat([len, t, data, crc]);
}
function encodePng(size, rgba) {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0); ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; ihdr[9] = 6;
  const raw = Buffer.alloc(size * (1 + size * 4));
  for (let y = 0; y < size; y++) {
    raw[y * (1 + size * 4)] = 0;
    rgba.copy(raw, y * (1 + size * 4) + 1, y * size * 4, (y + 1) * size * 4);
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}
function pngPixels(png) {
  let offset = 8;
  const idat = [];
  while (offset < png.length) {
    const size = png.readUInt32BE(offset);
    const type = png.subarray(offset + 4, offset + 8).toString('ascii');
    if (type === 'IDAT') idat.push(png.subarray(offset + 8, offset + 8 + size));
    offset += size + 12;
  }
  return inflateSync(Buffer.concat(idat));
}
function hasSamePixels(file, next) {
  try { return pngPixels(readFileSync(file)).equals(pngPixels(next)); }
  catch { return false; }
}

/* ---------- 圆点绘制 ---------- */
const CENTER = SIZE / 2;
function inCircle(x, y, r) {
  const dist = Math.hypot(x - CENTER, y - CENTER);
  const aa = 0.6 * SCALE;
  if (dist >= r) return 0;
  if (dist <= r - aa) return 1;
  return (r - dist) / aa;
}
function draw(stages, selected) {
  const colors = stages.map((s) => hexToRgb(STAGE_COLOR[s]));
  const r = D / 2;
  const buf = Buffer.alloc(SIZE * SIZE * 4);
  const n = colors.length;
  const blue = hexToRgb(MARKER_SELECTED_COLOR);
  const white = hexToRgb(STROKE);
  const strokeW = selected ? SEL_STROKE_W : STROKE_W;
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const dist = Math.hypot(x - CENTER, y - CENTER);
      let rgb = null;
      let alpha = 0;

      // 1) 选中态：先在圆点之外铺一层知性蓝光晕（内软外实 + 外缘实心环）
      if (selected && dist > HALO_IN - 0.5) {
        const oa = inCircle(x, y, HALO_OUT); // 仅外缘做抗锯齿
        if (oa > 0) {
          rgb = blue;
          if (dist >= HALO_MID) {
            alpha = HALO_RING_A * oa;                        // 外缘实心环
          } else {
            const t = Math.min(1, (dist - HALO_IN) / (HALO_MID - HALO_IN)); // 0 内 → 1 外
            alpha = (HALO_GLOW_A - 0.24 * t) * oa;           // 软光晕：内浓外淡
          }
        }
      }

      // 2) 圆点本体：白描边 + 学段分色扇形（多学段按学段数拼圆）
      const a = inCircle(x, y, r);
      if (a > 0) {
        if (dist > r - strokeW) {
          rgb = white;
          alpha = 1;
        } else {
          const seg = Math.min(Math.floor((y - (CENTER - r)) / ((2 * r) / n)), n - 1);
          rgb = colors[seg];
          alpha = FILL_ALPHA;
        }
        alpha *= a;
      }

      if (rgb === null || alpha <= 0) continue;
      const i = (y * SIZE + x) * 4;
      buf[i] = rgb[0]; buf[i + 1] = rgb[1]; buf[i + 2] = rgb[2];
      buf[i + 3] = Math.round(Math.min(1, alpha) * 255);
    }
  }
  return buf;
}
function hexToRgb(h) {
  return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
}

/* ---------- 输出 ---------- */
const COMBO = {
  p: ['primary'],
  m: ['middle'],
  h: ['high'],
  pm: ['primary', 'middle'],
  ph: ['primary', 'high'],
  mh: ['middle', 'high'],
  pmh: ['primary', 'middle', 'high'],
};
const outDir = join(ROOT, 'apps', 'miniprogram', 'assets', 'markers-index');
mkdirSync(outDir, { recursive: true });
for (const [key, stages] of Object.entries(COMBO)) {
  for (const selected of [false, true]) {
    const png = encodePng(SIZE, draw(stages, selected));
    const file = join(outDir, `marker-${key}${selected ? '-sel' : ''}.png`);
    if (!hasSamePixels(file, png)) writeFileSync(file, png);
    console.log(`[markers-index] ${key}${selected ? '-sel' : ''} (${stages.join('+')}) → ${png.length}B`);
  }
}
