/**
 * 首页专用 marker 图标生成（构建期）：按 UI 稿《知性蓝》学段分色生成 PNG。
 * 与 map 页的 gen-markers.mjs 同源逻辑，仅替换「学段分色」唯一真源与输出目录，
 * 不改动 map 页任何文件。产物：apps/miniprogram/assets/markers-index/
 *   普通 marker-{p|m|h|pm|ph|mh|pmh}.png + 同名 -sel.png（选中态，知性蓝光晕）
 */
import { deflateSync, inflateSync } from 'node:zlib';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

// 学段分色唯一真源：UI 稿《知性蓝》—— 小学蓝 / 初中橙 / 高中绿
const STAGE_COLOR = {
  primary: '#2F5CD6',
  middle: '#E8850C',
  high: '#0F9D58',
};
// 选中态描边光晕色：知性蓝 ib-500
const SELECTED_COLOR = '#2F5CD6';

const SIZE = 48;
const D = 30;
const STROKE = '#FFFFFF';
const FILL_ALPHA = 0.92;
const STROKE_W = 1.4;      // 常态白描边
const SEL_STROKE_W = 2.2;  // 选中态白描边（略加粗，让彩色圆点更实）
// 选中态「知性蓝光晕」：软光晕 + 外缘实心环，明显区别于常态白描边圆点。
// 注：图标以 48px 画布生成、地图上按 22px 显示（缩放 ≈0.46），
// 故环宽需按画布尺寸给足，否则缩到 22px 后只剩 1px 细线、看不出区别（旧版 SEL_STROKE_W=3.4 即此问题）。
const HALO_IN = 16.0;      // 光晕内缘半径（圆点 r=15，留 1px 呼吸位）
const HALO_MID = 20.5;     // 软光晕 → 实心外环 分界
const HALO_OUT = 23.0;     // 光晕外缘半径（离 48px 画布边 1px）
const HALO_GLOW_A = 0.42;  // 光晕内缘不透明度
const HALO_RING_A = 0.95;  // 外缘实心环不透明度

/* ---------- PNG 编码（最小实现，与 gen-markers.mjs 同构） ---------- */
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
  const aa = 0.6;
  if (dist >= r) return 0;
  if (dist <= r - aa) return 1;
  return (r - dist) / aa;
}
function draw(stages, selected) {
  const colors = stages.map((s) => hexToRgb(STAGE_COLOR[s]));
  const r = D / 2;
  const buf = Buffer.alloc(SIZE * SIZE * 4);
  const n = colors.length;
  const blue = hexToRgb(SELECTED_COLOR);
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
