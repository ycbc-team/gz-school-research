/**
 * tier1 信号 → 展示文本（信息卡/列表共用）。
 * JSON 真源为结构化字段，此处格式化为可读文本；无值一律回退「未查到」，
 * 与旧版页面展示口径保持一致（民间口径，非官方评价）。
 */
import type { Tier1School } from './types.js';

export interface SignalRow {
  label: string;
  value: string;
  strong?: boolean;
}

function val(v: unknown): string {
  return v === null || v === undefined || v === '' ? '未查到' : String(v);
}

/** 小学信号行：出口机制 / 教育集团 / 班数 / 学位预警 / 省一级 */
export function formatPrimarySignals(s: Tier1School): SignalRow[] {
  const rows: SignalRow[] = [];
  const xs = s.xiaoshengchu;
  if (xs) {
    const all = xs.feed_junior_highs || [];
    const feed = all.length > 4 ? `${all.slice(0, 4).join('、')}等` : all.join('、');
    rows.push({
      label: '出口机制',
      value: `派位${xs.group ?? '分组'}${feed ? `（含${feed}）` : ''}`,
    });
  }
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
