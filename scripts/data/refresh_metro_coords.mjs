// 一次性脚本：用高德地铁图 API（GCJ-02）刷新 data/region/metro.json 的站点坐标
// 旧坐标为 2-3 位小数的占位值（误差可达数公里），导致按站筛学校映射错乱。
import { readFileSync, writeFileSync } from 'node:fs';

const amap = JSON.parse(readFileSync('/tmp/gz_amap_subway.json', 'utf8'));
const metro = JSON.parse(readFileSync('data/region/metro.json', 'utf8'));

const norm = (s) => s.replace(/\s+/g, '');
// 站名别名：高德写法 ← 本库写法（官方 rare 字/括号后缀差异）
const ALIAS = {
  '机场南': '机场南(1号航站楼)',
  '机场北': '机场北(T2)',
  '清㘵': '清布',
  '𧒽岗': '礌岗',
};
const parse = (sl) => { const [lng, lat] = sl.split(',').map(Number); return { lng, lat }; };

// 全局站名 → 坐标候选（可能多条线路同名=换乘站，坐标应基本一致）
const byName = new Map();
for (const ln of amap.l) {
  for (const st of ln.st) {
    const n = norm(st.n);
    if (!st.sl) continue;
    if (!byName.has(n)) byName.set(n, []);
    byName.get(n).push(parse(st.sl));
  }
}

// 线名匹配（normalize：去空格、北延段/支线别名）
function matchLine(name) {
  const n = norm(name);
  if (n === '3号线北延段') return amap.l.filter((l) => norm(l.ln) === '3号线' && l.st.length === 15);
  if (n === '14号线知识城支线') return amap.l.filter((l) => norm(l.ln).includes('知识城'));
  return amap.l.filter((l) => norm(l.ln) === n);
}

let matched = 0, fallback = 0, missed = [];
const report = [];
const dist = (a, b, c, d) => {
  const R = 6371, rad = (x) => (x * Math.PI) / 180;
  const dLat = rad(c - a), dLng = rad(d - b);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a)) * Math.cos(rad(c)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
};

for (const line of metro.lines) {
  const candLines = matchLine(line.name);
  for (const st of line.stations) {
    const n = norm(ALIAS[st.name] || st.name);
    // 优先：同名站里取本线候选线中的坐标；其次全局
    let coord = null, src = '';
    for (const cl of candLines) {
      const hit = cl.st.find((s) => norm(s.n) === n && s.sl);
      if (hit) { coord = parse(hit.sl); src = `line:${line.name}`; break; }
    }
    if (!coord && byName.has(n)) {
      const list = byName.get(n);
      // 若全局候选坐标离散（>1.5km）说明同名不同站，取第一个但记录
      const c0 = list[0];
      const spread = list.some((c) => dist(c0.lat, c0.lng, c.lat, c.lng) > 1.5);
      coord = c0; src = spread ? 'GLOBAL_CONFLICT' : 'global';
      fallback++;
    }
    if (!coord) { missed.push(`${line.name}:${st.name}`); continue; }
    const dKm = dist(st.lat, st.lng, coord.lat, coord.lng);
    if (dKm > 2) report.push(`${line.name} ${st.name}: 旧(${st.lng},${st.lat}) → 新(${coord.lng},${coord.lat}) 移动 ${dKm.toFixed(1)}km [${src}]`);
    st.lng = Math.round(coord.lng * 1e6) / 1e6;
    st.lat = Math.round(coord.lat * 1e6) / 1e6;
    matched++;
  }
}

console.log(`matched=${matched} (line-pref=${matched - fallback}, global-fallback=${fallback})`);
console.log(`missed=${missed.length}`);
if (missed.length) console.log('MISS:', missed.join(', '));
console.log('--- 大位移（>2km，重点复核）---');
for (const r of report) console.log(r);
writeFileSync('data/region/metro.json', JSON.stringify(metro, null, 2) + '\n');
console.log('written data/region/metro.json');
