/**
 * 地图域信息卡模型：选中点位 → 信息卡四分支（高中指标 / 口碑 / 挂牌 / 普通）+ 招生条件 + 升学路线 + 详情跳转。
 * Web 底部抽屉与小程序 cover-view 抽屉共用同一模型。
 */
import { normName } from '../../support.js';
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

/** 该校名实际出现在哪些学段（POI 全等）：决定详情跳转按钮（多学部=完中，逐学部跳） */
function nameStagesOf(repo: Repository, name: string): ('primary' | 'middle' | 'high')[] {
  const has = (stage: 'primary' | 'middle' | 'high') =>
    repo.schools[stage].schools.some((s) => normName(s.name) === normName(name));
  const out: ('primary' | 'middle' | 'high')[] = [];
  if (has('primary')) out.push('primary');
  if (has('middle')) out.push('middle');
  if (has('high')) out.push('high');
  return out;
}

/** 小学招生条件行（2026 招生计划：班数 + 对口地段） */
function primaryEnrollRows(repo: Repository, name: string): InfoRow[] {
  const en = repo.matchEnrollment(name);
  if (!en) return [];
  const rows: InfoRow[] = [];
  if (en.plan_classes != null) rows.push({ label: '2026班数', value: `${en.plan_classes} 个班`, strong: true });
  if (en.zone) rows.push({ label: '招生地段', value: en.zone });
  return rows;
}
/** 小学升学路线行（全量 xiaoshengchu 真源，校名全等匹配，跨区同名按 adcode 消歧） */
function primaryLinkageRows(repo: Repository, name: string, adcode?: string): InfoRow[] {
  const xs = repo.xiaoshengchuOf(name, adcode);
  if (!xs || (!xs.direct_feed && !(xs.feed_junior_highs || []).length)) return [];
  return [{ label: '升学路线', value: formatXiaoshengchuBrief(xs) }];
}
/** 初中生源小学摘要行（全量反查；无公办对口时给提示） */
function middleFeedRows(repo: Repository, name: string): InfoRow[] {
  const list = repo.middlePrimaryFeed(name);
  if (!list.length) return [{ label: '生源小学', value: '无公办对口名单（民办校以摇号/直升为准）', strong: false }];
  const preview = list.slice(0, 3).map((r) => r.primary).join('、');
  const more = list.length > 3 ? ` 等 ${list.length} 所` : '';
  return [{ label: '生源小学', value: preview + more, strong: true }];
}

export function buildInfoModel(pt: MapPointFull, repo: Repository): InfoModel {
  const districtName = districtByAdcode[pt.adcode] || '';
  const name = pt.name;
  // 详情跳转：单学部一个按钮；多学部（完中）按学部分别跳对应 tab
  const nameStages = nameStagesOf(repo, name);
  const STAGE_SHORT: Record<string, string> = { primary: '小学部', middle: '初中部', high: '高中部' };
  const detailLinks = nameStages.length > 1
    ? nameStages.map((s) => ({ text: `查看${STAGE_SHORT[s]}详情 →`, to: `/school/${encodeURIComponent(name)}?stage=${s}` }))
    : [{ text: '查看学校详情 →', to: `/school/${encodeURIComponent(name)}` }];

  if (pt.mainStage === 'high') {
    const rec = pt.rec;
    if (!rec) {
      return {
        name,
        badges: repo.schoolBadges('high', { district: districtName, name }),
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
      badges: repo.schoolBadges('high', { district: districtName, rec, name }),
      head: null,
      rows,
      note: '口径：录取线为官方发布（公办户籍生 / 民办最低分）；特控率/高分段为喜报或网传数据。完整出口数据见详情页。',
      links: detailLinks,
    };
  }

  const tier = pt.tier;
  if (tier) {
    // 小学缩略面板优先展示招生条件（班数 + 对口地段）
    const enrollRows = pt.mainStage === 'primary' ? primaryEnrollRows(repo, name) : [];
    // 小学升学路线取全量 xiaoshengchu（全等匹配）；口碑信号另缩略一条
    const linkageRows = pt.mainStage === 'primary' ? primaryLinkageRows(repo, name, pt.adcode) : [];
    if (tier.tier1_eligible === false) {
      return {
        name,
        badges: repo.schoolBadges(pt.mainStage, { district: districtName, tier, name }),
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
      : [...middleFeedRows(repo, name), ...formatMiddleSignals(tier).slice(0, 1)];
    return {
      name,
      badges: repo.schoolBadges(pt.mainStage, { district: districtName, tier, name }),
      head,
      rows: [...enrollRows, ...signalRows],
      note: '完整口碑信号与升学通道见详情页。',
      links: detailLinks,
    };
  }

  return {
    name,
    badges: repo.schoolBadges(pt.mainStage, { district: districtName, name }),
    head: null,
    rows: [
      { label: '学部', value: pt.stages.map((s) => STAGE_LABEL[s]).join('、') },
      { label: '所在区', value: districtName || '—' },
      ...(pt.mainStage === 'primary' ? primaryEnrollRows(repo, name) : []),
      ...(pt.mainStage === 'primary' ? primaryLinkageRows(repo, name, pt.adcode) : []),
      ...(pt.mainStage === 'middle' ? middleFeedRows(repo, name) : []),
    ],
    note: null,
    links: detailLinks,
  };
}
