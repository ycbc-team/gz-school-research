/**
 * 地图域信息卡模型：选中点位 → 信息卡四分支（高中指标 / 口碑 / 挂牌 / 普通）+ 招生条件 + 升学路线 + 详情跳转。
 * Web 底部抽屉与小程序 cover-view 抽屉共用同一模型。
 */
import { formatPrimarySignals, formatMiddleSignals, formatXiaoshengchuBrief, highScoreRows } from '../../format.js';
import type { Repository } from '../../data/repository.js';
import { districtByAdcode, STAGE_LABEL } from './constants.js';
import type { MapPointFull } from './points.js';

export interface InfoRow { label: string; value: string; strong?: boolean }
export interface InfoLink { text: string; to: string }
export interface InfoModel {
  name: string;
  badges: { text: string; cls: string }[];
  head: string | null;
  rows: InfoRow[];
  note: string | null;
  links: InfoLink[];
}

/** 详情跳转：单学部一个按钮；多学部（完中/同址九年制）按点位实际学部逐学部跳，id 取各学部 POI 实体 */
function detailLinksOf(pt: MapPointFull): { text: string; to: string }[] {
  const STAGE_SHORT: Record<string, string> = { primary: '小学部', middle: '初中部', high: '高中部' };
  const detailUrl = (stage?: string) => {
    const q: string[] = [];
    if (stage) q.push(`stage=${stage}`);
    const sid = stage ? pt.ids[stage as keyof typeof pt.ids] : pt.school_id;
    if (sid) q.push(`id=${encodeURIComponent(sid)}`);
    return `/school/${encodeURIComponent(pt.name)}${q.length ? `?${q.join('&')}` : ''}`;
  };
  return pt.stages.length > 1
    ? pt.stages.map((s) => ({ text: `查看${STAGE_SHORT[s]}详情 →`, to: detailUrl(s) }))
    : [{ text: '查看学校详情 →', to: detailUrl(pt.mainStage) }];
}

/** 小学招生条件行（2026 招生计划：班数 + 对口地段） */
function primaryEnrollRows(repo: Repository, pt: MapPointFull): InfoRow[] {
  const en = repo.matchEnrollment(pt.school_id || pt.name);
  if (!en) return [];
  const rows: InfoRow[] = [];
  if (en.plan_classes != null) rows.push({ label: '2026班数', value: `${en.plan_classes} 个班`, strong: true });
  if (en.zone) rows.push({ label: '招生地段', value: en.zone });
  return rows;
}
/** 小学升学路线行（全量 xiaoshengchu 真源，按小学实体 id 查询，零名字匹配） */
function primaryLinkageRows(repo: Repository, schoolId: string | null | undefined): InfoRow[] {
  const xs = repo.xiaoshengchuOf(schoolId);
  if (!xs || (!xs.direct_feed && !(xs.feed_junior_highs || []).length)) return [];
  return [{ label: '升学路线', value: formatXiaoshengchuBrief(xs) }];
}
/** 初中生源小学摘要行（全量反查，按初中实体 id 查询；无公办对口时给提示） */
function middleFeedRows(repo: Repository, schoolId: string | null | undefined): InfoRow[] {
  const list = repo.middlePrimaryFeed(schoolId);
  if (!list.length) return [{ label: '生源小学', value: '无公办对口名单（民办校以摇号/直升为准）', strong: false }];
  const preview = list.slice(0, 3).map((r) => r.primary).join('、');
  const more = list.length > 3 ? ` 等 ${list.length} 所` : '';
  return [{ label: '生源小学', value: preview + more, strong: true }];
}

export function buildInfoModel(pt: MapPointFull, repo: Repository): InfoModel {
  const districtName = districtByAdcode[pt.adcode] || '';
  const name = pt.name;
  const detailLinks = detailLinksOf(pt);

  if (pt.mainStage === 'high') {
    const rec = pt.rec;
    if (!rec) {
      return {
        name,
        badges: repo.schoolBadges('high', { district: districtName, name, stages: pt.stages }),
        head: null,
        rows: [
          { label: '学部', value: pt.stages.map((s) => STAGE_LABEL[s]).join('、') },
          { label: '所在区', value: districtName || '—' },
        ],
        note: '该点位暂未匹配到高中分类（可能为未收录学校）。',
        links: detailLinks,
      };
    }
    const ind = rec.indicators || {};
    const rows: Array<{ label: string; value: string; strong?: boolean }> = [];
    const put = (k: string, label: string, strong = false) => {
      const v = ind[k];
      if (v !== undefined && v !== null && v !== '') rows.push({ label, value: String(v), strong });
    };
    // 中考录取线：官方分数（2025/2026 两年，按校区实体 school_id 引用）；公办=户籍生最低分，民办=最低分（含公费班）
    rows.push(...highScoreRows(repo.scoresOfSchool(name, rec.campuses || [])));
    put('tekong_2026', '特控线上线率 2026');
    put('gaofen_2026', '高分段 2026');
    return {
      name,
      badges: repo.schoolBadges('high', { district: districtName, rec, name, stages: pt.stages }),
      head: null,
      rows,
      note: '口径：录取线为官方发布（公办户籍生 / 民办最低分）；特控率/高分段为喜报或网传数据。完整出口数据见详情页。',
      links: detailLinks,
    };
  }

  const tier = pt.tier;
  if (tier) {
    // 小学缩略面板优先展示招生条件（班数 + 对口地段）；多学部合并点按实际学部全展示
    const enrollRows = pt.stages.includes('primary') ? primaryEnrollRows(repo, pt) : [];
    // 小学升学路线取全量 xiaoshengchu（实体 id）；口碑信号另缩略一条
    const linkageRows = pt.stages.includes('primary') ? primaryLinkageRows(repo, pt.ids.primary) : [];
    if (tier.tier1_eligible === false) {
      return {
        name,
        badges: repo.schoolBadges(pt.mainStage, { district: districtName, tier, name, stages: pt.stages }),
        head: '网传"口碑学校" · 独立法人，未计入口碑学校',
        rows: [
          ...enrollRows,
          ...linkageRows,
          ...(tier.exclude_reason ? [{ label: '未计入原因', value: tier.exclude_reason }] : []),
        ],
        note: null,
        links: detailLinks,
      };
    }
    const head =
      '网传"口碑学校" · 民间口径非官方' +
      (tier.entity_relation === '同法人校区' ? ' · 与本部同一法人' : '');
    const signalRows = pt.mainStage === 'primary'
      ? [...linkageRows, ...formatPrimarySignals(tier).slice(0, 1)]
      : [...(pt.stages.includes('middle') ? middleFeedRows(repo, pt.ids.middle) : []), ...formatMiddleSignals(tier).slice(0, 1)];
    return {
      name,
      badges: repo.schoolBadges(pt.mainStage, { district: districtName, tier, name, stages: pt.stages }),
      head,
      rows: [...enrollRows, ...signalRows],
      note: '完整口碑信号与升学通道见详情页。',
      links: detailLinks,
    };
  }

  return {
    name,
    badges: repo.schoolBadges(pt.mainStage, { district: districtName, name, stages: pt.stages }),
    head: null,
    rows: [
      { label: '学部', value: pt.stages.map((s) => STAGE_LABEL[s]).join('、') },
      { label: '所在区', value: districtName || '—' },
      ...(pt.stages.includes('primary') ? primaryEnrollRows(repo, pt) : []),
      ...(pt.stages.includes('primary') ? primaryLinkageRows(repo, pt.ids.primary) : []),
      ...(pt.stages.includes('middle') ? middleFeedRows(repo, pt.ids.middle) : []),
    ],
    note: null,
    links: detailLinks,
  };
}
