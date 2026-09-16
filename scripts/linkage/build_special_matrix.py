#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建升学通道矩阵：初中 × 高中（体育/艺术/自招考核资格）
- 输入：data/linkage/raw/special/sports_2026.json、arts_2026.json
       data/linkage/raw/autonomy/autonomy_qualify_2026.json
       data/registry/entities.json（高中实体别名表，用于名字匹配与审计）
- 输出：data/linkage/special_matrix.json
口径：全部有名单的高中（含区属/中职，不再限省市属 11 所）；
      自招为考核资格名单口径（非预录取）。
      体育/艺术 project 去掉末尾"（项目）"得到招生高中（校区）；自招标题去"2026年"前缀。
      矩阵 key 使用名单原文（可溯源）；前端跳转通过实体表 resolvePoiName 归一。
"""
import json, re, collections

BASE = 'data/linkage/raw'
OUT = 'data/linkage/special_matrix.json'


def strip_2026(name: str) -> str:
    """去"2026年"前缀 → 高中名原文"""
    return re.sub(r'^2026年', '', name).strip()


def strip_project(project: str) -> str:
    """去末尾项目片段 → 招生学校（校区）原文。
    两种官方格式：①闭合「…（项目）」（如「广州市铁一中学（越秀校区）（舞蹈）」）；
    ②PDF 解析截断「…（项目名截断」（299 条，无闭合括号），去最后一个未闭合「（…」片段。
    """
    p = project.strip()
    if p.endswith('）'):
        return re.sub(r'（[^（）]*）$', '', p)
    idx = p.rfind('（')
    return p[:idx] if idx > 0 else p


def norm(s: str) -> str:
    """复刻 shared normName：去「广州市」前缀、全半角括号统一去除、去空白（保留括号内文字）"""
    return re.sub(r'[（(]', '(', s).replace('）', ')').replace('(', '').replace(')', '')\
        .replace('广州市', '').replace(' ', '').strip()


# ---------------- 高中实体别名表（entities.json stage=high，名字匹配唯一宿主） ----------------
entities = json.load(open('data/registry/entities.json'))['entities']
high_aliases: dict[str, str] = {}  # 归一化别名 → 实体名
for e in entities:
    if e.get('stage') != 'high':
        continue
    for a in [e['name']] + (e.get('aliases') or []):
        na = norm(a)
        if na and na not in high_aliases:
            high_aliases[na] = e['name']


def resolve_entity(name: str):
    """名单高中原文 → 实体名（实体表别名全等匹配）；未命中返回 None（仅审计用，不阻塞收录）"""
    return high_aliases.get(norm(name))


# 已知截断/异常名单名 → 完整高中名（PDF 解析截断，显式修复、可审计）
HIGH_NAME_FIX = {
    '广州市第一': '广州市第一中学',  # sports/arts 23 条 project 截断，招生校为广州市第一中学
}


def fix_high(name: str) -> str:
    return HIGH_NAME_FIX.get(name, name)


# ---------------- 聚合 ----------------
def agg_autonomy(rows):
    """自招：school_high 去「2026年」前缀；校区括号必须保留（如「（校本部）」「（广钢校区）」）"""
    mat = collections.Counter()
    for r in rows:
        h = fix_high(strip_2026(r['school_high']))
        if not h:
            continue
        mat[(r['school_junior'], h)] += 1
    return mat


def agg_project(rows):
    """体育/艺术：project 去末尾「（项目）」片段 → 招生学校（校区）原文"""
    mat = collections.Counter()
    for r in rows:
        h = fix_high(strip_project(r['project']))
        if not h:
            continue
        mat[(r['school'], h)] += 1
    return mat


sports = json.load(open(f'{BASE}/special/sports_2026.json'))
arts = json.load(open(f'{BASE}/special/arts_2026.json'))
auto = json.load(open(f'{BASE}/autonomy/autonomy_qualify_2026.json'))

# sports/arts：初中=school 字段；autonomy：初中=school_junior 字段
m_sports = agg_project(sports)
m_arts = agg_project(arts)
m_auto = agg_autonomy(auto)

# 合并结构：matrix[初中][高中] = {sports, arts, autonomy}
matrix = collections.defaultdict(lambda: collections.defaultdict(dict))
all_hs = set()
for (j, h), v in m_sports.items():
    matrix[j][h]['sports'] = v
    all_hs.add(h)
for (j, h), v in m_arts.items():
    matrix[j][h]['arts'] = v
    all_hs.add(h)
for (j, h), v in m_auto.items():
    matrix[j][h]['autonomy'] = v
    all_hs.add(h)

# 高中原文 → 实体名（审计：所有高中应能匹配到实体；未命中说明名单名与实体表有出入，需人工复核）
high_entities = {}
unresolved = []
for h in sorted(all_hs):
    ent = resolve_entity(h)
    high_entities[h] = ent
    if ent is None:
        unresolved.append(h)

out = {
    'updated': '2026-09-15',
    'scope': '全部有名单的高中（含区属/中职），体育/艺术特长生通过测试名单 + 自招综合能力考核资格名单',
    'note': (
        '体育/艺术=通过专业测试名单（官方发布）；自招=综合能力考核资格名单口径（考核前≤5倍计划，非预录取）。'
        '收录范围=官方名单出现的全部招生高中（不再限省市属 11 所）；矩阵键=名单原文（可溯源），'
        'high_entities=名单原文→实体表高中名（未命中=名单名与实体表有出入，见审计输出）。'
    ),
    'high_schools': sorted(all_hs),
    'high_entities': high_entities,
    'matrix': {j: dict(hs) for j, hs in matrix.items()},
}
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('高中招生单位数:', len(all_hs))
print('初中学数:', len(matrix))
print('收录记录: 体育', sum(m_sports.values()), '艺术', sum(m_arts.values()), '自招', sum(m_auto.values()))
print('未匹配到高中实体的名单名（需人工复核）:', len(unresolved))
for u in unresolved:
    print('  !', u)
