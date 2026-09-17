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
      矩阵 key 使用名单原文（可溯源）；业务关联同时产出 high_school_ids，
      前端/共享层必须用该实体外键，不得再按高中名称二次匹配。
"""
import json
import sys, re, collections, os

BASE = 'data/linkage/raw'

# 统一匹配库：norm 本体收敛至 school_match.normName（原"复刻 shared normName"定义已删）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry"))
from school_match import normName as norm
OUT = 'data/linkage/special_matrix.json'
SOURCE_MAP = 'data/registry/source_name_mappings.json'
SOURCE = 'gzzk-special-2026'


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


# ---------------- 高中实体别名表（entities.json stage=high，名字匹配唯一宿主） ----------------
entities = json.load(open('data/registry/entities.json'))['entities']
entity_by_id = {e['school_id']: e for e in entities if e.get('stage') == 'high'}
source_mappings = json.load(open(SOURCE_MAP)).get('mappings', [])
source_id_by_raw_name = {
    r['raw_name']: r['school_id']
    for r in source_mappings
    if r.get('source') == SOURCE and r.get('raw_name') and r.get('school_id')
}
high_aliases: dict[str, list[dict]] = collections.defaultdict(list)  # 归一化别名 → 高中实体候选
for e in entities:
    if e.get('stage') != 'high':
        continue
    for a in [e['name']] + (e.get('aliases') or []):
        na = norm(a)
        if na:
            high_aliases[na].append(e)


def resolve_entity(name: str):
    """名单高中原文 → 唯一高中实体。

    这是唯一允许用名称解析第一批招生单位的构建期入口。候选必须收敛到唯一
    school_id；未命中或歧义一律返回 None，留在审计输出，禁止取第一个候选。
    """
    mapped_id = source_id_by_raw_name.get(name)
    if mapped_id:
        return entity_by_id.get(mapped_id)
    candidates = {e['school_id']: e for e in high_aliases.get(norm(name), [])}
    return next(iter(candidates.values())) if len(candidates) == 1 else None


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

# 高中原文 → 实体名/ID（审计：未命中说明名单名与实体表有出入，需人工复核）
high_entities = {}
high_school_ids = {}
unresolved = []
for h in sorted(all_hs):
    ent = resolve_entity(h)
    high_entities[h] = ent['name'] if ent else None
    high_school_ids[h] = ent['school_id'] if ent else None
    if ent is None:
        unresolved.append(h)

# 保留由 backfill_school_ids 生成的初中外键；本生成器只负责第一批事实和高中外键。
try:
    previous = json.load(open(OUT))
except FileNotFoundError:
    previous = {}

# ---------------- 2026 自主招生计划（官方汇总表，按校区/法人公布） ----------------
plan_raw = json.load(open('data/linkage/raw/autonomy/plan_2026.json'))
autonomy_plan = {s['name']: s['plan'] for s in plan_raw['schools']}
plan_norm = {norm(k): v for k, v in autonomy_plan.items()}

out = {
    'updated': '2026-09-17',
    'scope': '全部有名单的高中（含区属/中职），体育/艺术特长生通过测试名单 + 自招综合能力考核资格名单',
    'note': (
        '体育/艺术=通过专业测试名单（官方发布）；自招=综合能力考核资格名单口径（考核前≤5倍计划，非预录取）。'
        '收录范围=官方名单出现的全部招生高中（不再限省市属 11 所）；矩阵键=名单原文（可溯源），'
        'high_school_ids=名单原文→高中实体 school_id，是第一批招生关联唯一外键；'
        '值为 null 表示未收录对应高中实体，仅保留原文展示，不得名称兜底。'
        'autonomy_plan=2026官方自主招生计划数（按校区公布），计划数≠资格名单人数≠录取人数。'
    ),
    'high_schools': sorted(all_hs),
    'high_entities': high_entities,
    'high_school_ids': high_school_ids,
    'autonomy_plan': autonomy_plan,
    'autonomy_plan_norm': plan_norm,
    'autonomy_plan_source': plan_raw['source_url'],
    'matrix': {j: dict(hs) for j, hs in matrix.items()},
}
if previous.get('middle_school_ids'):
    out['middle_school_ids'] = previous['middle_school_ids']
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('高中招生单位数:', len(all_hs))
print('初中学数:', len(matrix))
print('收录记录: 体育', sum(m_sports.values()), '艺术', sum(m_arts.values()), '自招', sum(m_auto.values()))
print('未匹配到高中实体的名单名（需人工复核）:', len(unresolved))
for u in unresolved:
    print('  !', u)
