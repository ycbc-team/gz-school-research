/**
 * tier1 信号 → 展示文本（信息卡/列表共用）。
 * JSON 真源为结构化字段，此处格式化为可读文本；无值一律回退「未查到」，
 * 与旧版页面展示口径保持一致（民间口径，非官方评价）。
 */
import type { Tier1School, XiaoshengchuRecord } from './types.js';

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
