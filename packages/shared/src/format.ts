/**
 * tier1 信号 → 展示文本（信息卡/列表共用）。
 * JSON 真源为结构化字段，此处格式化为可读文本；无值一律回退「未查到」，
 * 与旧版页面展示口径保持一致（民间口径，非官方评价）。
 */
import type { Tier1School, XiaoshengchuRecord } from './types.js';
import type { HighScoreRecord } from './data/types.js';
import type { SchoolScore } from './data/scores.js';

export interface SignalRow {
  label: string;
  value: string;
  strong?: boolean;
}

function val(v: unknown): string {
  return v === null || v === undefined || v === '' ? '未查到' : String(v);
}

/**
 * 全量升学路线记录 → 一行简述（地图浮层 / 支撑度表共用）。
 * 直升优先；否则按派位/对口列对口初中（超过 4 所截断加「等」）；无数据回退「未查到」。
 */
export function formatXiaoshengchuBrief(xs?: XiaoshengchuRecord | null): string {
  if (!xs) return '未查到';
  if (xs.direct_feed) return `对口直升 ${xs.direct_feed}`;
  const all = xs.feed_junior_highs || [];
  if (!all.length) return xs.data_gaps ? '官方未公布对口初中' : '未查到';
  const feed = all.length > 4 ? `${all.slice(0, 4).join('、')}等` : all.join('、');
  const via = /派位/.test(xs.group || '') ? '电脑派位' : '对口';
  return `${via} ${feed}`;
}

/** 小学信号行：教育集团 / 班数 / 学位预警 / 省一级（升学路线改由全量 xiaoshengchu 数据单独承载） */
export function formatPrimarySignals(s: Tier1School): SignalRow[] {
  const rows: SignalRow[] = [];
  if (s.education_group) {
    rows.push({
      label: '教育集团',
      value: `${s.education_group.name}（${s.education_group.role}）`,
      strong: true,
    });
  }
  if (s.plan_classes_2026 != null) {
    rows.push({ label: '2026班数', value: `${s.plan_classes_2026} 个班`, strong: true });
  }
  if (s.degree_warning) rows.push({ label: '学位预警', value: val(s.degree_warning), strong: true });
  if (s.provincial_level_title) {
    const t = s.provincial_level_title;
    const note = (t.note || '').replace(/[（(].*?[)）]/g, '').slice(0, 24);
    rows.push({ label: '省一级', value: `${t.year} 年评定${note ? `（${note}）` : ''}` });
  }
  return rows;
}

/** 初中信号行：中考成绩 / 示范性高中 / 教育集团 / 建校年份 / 指标到校 */
export function formatMiddleSignals(s: Tier1School): SignalRow[] {
  const rows: SignalRow[] = [];
  const zk = s.zhongkao;
  if (zk) {
    rows.push({
      label: '中考成绩',
      value: `${zk.year} 年（${zk.scope}）：${zk.data}${zk.note ? `（${zk.note}）` : ''}`,
    });
  } else {
    rows.push({ label: '中考成绩', value: '未查到' });
  }
  if (s.demonstration_high) {
    rows.push({
      label: '示范性高中',
      value: val(s.demonstration_high.level),
      strong: true,
    });
  }
  if (s.education_group) {
    rows.push({
      label: '教育集团',
      value: `${s.education_group.name}（${s.education_group.role}）`,
    });
  }
  if (s.founded) {
    rows.push({
      label: '建校年份',
      value: `${s.founded.year} 年${s.founded.note ? `（${s.founded.note}）` : ''}`,
      strong: true,
    });
  }
  if (s.quota_allocation) {
    rows.push({ label: '指标到校', value: s.quota_allocation.data });
  }
  return rows;
}

/* ---------- 高中中考录取线（官方分数） ---------- */

/** 校区官方招生单位名 → 短名（括号内容去「校区」；无括号返回空 = 不显示校区前缀） */
function campusShort(officialName: string): string {
  const m = officialName.match(/（([^）]+)）/);
  if (!m) return '';
  return (m[1] || '').replace(/校区$/, '');
}

/** 民办/中外合作记录 → 「最低分547（公费班628）」；仅公费班时只显示公费班 */
function privateScoreText(records: HighScoreRecord[]): string | null {
  const main = records.find((r) => r.kind === 'private' && !r.gongfei);
  const gongfei = records.find((r) => r.kind === 'private' && r.gongfei);
  let t: string | null = main?.min_score != null ? `最低分${main.min_score}` : null;
  if (gongfei?.min_score != null) t = t ? `${t}（公费班${gongfei.min_score}）` : `公费班${gongfei.min_score}`;
  return t;
}

/** 单校区某年全部记录 → 展示文本（公办户籍生优先；民办最低分+公费班；艺术类末位分数兜底） */
function formatYearRecords(records: HighScoreRecord[]): string | null {
  const pub = records.find((r) => r.kind === 'public');
  if (pub) return pub.huji != null ? `户籍生${pub.huji}` : null;
  const privs = records.filter((r) => r.kind === 'private');
  if (privs.length) return privateScoreText(privs);
  const art = records.find((r) => r.kind === 'lang_art');
  if (art) return art.huji_last != null ? `艺术类${art.huji_last}` : null;
  return null;
}

/**
 * 学校（多校区）两年录取线 → 信息行。
 * 行=年份（2025/2026，有分数才出），值=各校区拼接（`石牌 户籍生740 · 知识城 户籍生727`）。
 * 口径：公办=户籍生最低分；民办=最低分（含公费班）；外语艺术类=艺术类末位考生分数。
 */
export function highScoreRows(scores: SchoolScore[]): SignalRow[] {
  if (!scores.length) return [];
  const rows: SignalRow[] = [];
  for (const year of [2025, 2026]) {
    const parts: string[] = [];
    for (const s of scores) {
      const yr = s.years.find((v) => v.year === year);
      if (!yr) continue;
      const text = formatYearRecords(yr.records);
      if (!text) continue;
      const short = campusShort(s.officialName);
      parts.push(short ? `${short} ${text}` : text);
    }
    if (parts.length) rows.push({ label: `中考录取线 ${year}`, value: parts.join(' · '), strong: true });
  }
  return rows;
}
