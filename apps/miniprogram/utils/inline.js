/**
 * 长文页（隐私政策 / 免责声明）轻量富文本
 *
 * 文案用 "普通**加粗**普通" 写法维护，运行时拆成 [{ id, t, b }] 分段，由 WXML 逐段 <text> 渲染。
 * 不用 rich-text：rich-text 内部节点不吃外部 WXSS 类，字号 / 行距 / 颜色会与全站长文版式脱节。
 */
function toRuns(s) {
  const runs = [];
  const re = /\*\*([^*]+)\*\*/g;
  let last = 0;
  let m = re.exec(s);
  while (m) {
    if (m.index > last) runs.push({ id: runs.length, t: s.slice(last, m.index), b: false });
    runs.push({ id: runs.length, t: m[1], b: true });
    last = m.index + m[0].length;
    m = re.exec(s);
  }
  if (last < s.length) runs.push({ id: runs.length, t: s.slice(last), b: false });
  return runs;
}

/** 段落数组 → 渲染数组（每段带 id 供 wx:key） */
function toParas(list) {
  return (list || []).map((s, i) => ({ id: i, runs: toRuns(s) }));
}

/** 章节数组（{ h, ps[] }）→ 渲染数组 */
function toSections(list) {
  return (list || []).map((sec, i) => ({ id: i, h: sec.h, ps: toParas(sec.ps) }));
}

module.exports = { toRuns, toParas, toSections };
