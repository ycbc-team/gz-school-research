/**
 * 小程序 marker 图标生成（构建期）：按 @gz/shared STAGE_COLOR 唯一真源生成 PNG。
 * - 单学部：学段色圆点（小学紫 / 初中红 / 高中绿）
 * - 多学部：同圆垂直分色（stages 升序 p→m→h 决定段序，与点位一致）
 * 纯 Node 实现 PNG 编码（zlib deflate），无 canvas 依赖。
 * 产物：apps/miniprogram/assets/markers/marker-{p|m|h|pm|ph|mh|pmh}.png（48×48）
 */
import { deflateSync } from 'node:zlib';
import { mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const require = createRequire(import.meta.url);

// 颜色唯一真源：@gz/shared（build:mp 前置已构建 shared）
const { STAGE_COLOR } = require(join(ROOT, 'packages', 'shared', 'dist', 'cjs', 'index.js'));

const SIZE = 48;      // 图标画布
const D = 30;         // 圆直径（留边距给触控）
const STROKE = '#FFFFFF';

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
  ihdr[8] = 8;  // bit depth
  ihdr[9] = 6;  // color type RGBA
  // 每行前置 filter byte 0
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

/* ---------- 圆点绘制（平滑边缘） ---------- */
const CENTER = SIZE / 2;
function inCircle(x, y, r) {
  const dist = Math.hypot(x - CENTER, y - CENTER);
  const aa = 0.6; // 抗锯齿过渡带
  if (dist >= r) return 0;
  if (dist <= r - aa) return 1;
  return (r - dist) / aa;
}
/** 多学部垂直分色：stages 升序（p→m→h），段内颜色采样 */
function draw(stages) {
  const colors = stages.map((s) => hexToRgb(STAGE_COLOR[s]));
  const r = D / 2;
  const buf = Buffer.alloc(SIZE * SIZE * 4);
  const n = colors.length;
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const a = inCircle(x, y, r);
      if (a <= 0) continue;
      // 描边：距圆边缘 1px 内为白色
      const dist = Math.hypot(x - CENTER, y - CENTER);
      let rgb;
      if (dist > r - 1.4) {
        rgb = [255, 255, 255];
      } else {
        const seg = Math.min(Math.floor((y - (CENTER - r)) / ((2 * r) / n)), n - 1);
        rgb = colors[seg];
      }
      const i = (y * SIZE + x) * 4;
      buf[i] = rgb[0]; buf[i + 1] = rgb[1]; buf[i + 2] = rgb[2];
      buf[i + 3] = Math.round(a * 255);
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
const outDir = join(ROOT, 'apps', 'miniprogram', 'assets', 'markers');
mkdirSync(outDir, { recursive: true });
for (const [key, stages] of Object.entries(COMBO)) {
  const png = encodePng(SIZE, draw(stages));
  const file = join(outDir, `marker-${key}.png`);
  writeFileSync(file, png);
  console.log(`[markers] ${key} (${stages.join('+')}) → ${file} ${png.length}B`);
}
