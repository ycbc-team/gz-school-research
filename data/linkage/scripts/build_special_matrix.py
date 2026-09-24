#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建升学通道矩阵：初中 × 高中（体育/艺术/自招考核资格）
- 输入：data/linkage/parsed/special/sports_2026.json、arts_2026.json
       data/linkage/parsed/autonomy/autonomy_qualify_2026.json
       data/registry/entity/dist/entities.json（高中实体别名表，用于名字匹配与审计）
- 输出：data/linkage/dist/special_matrix.json
口径：全部有名单的高中（含区属/中职，不再限省市属 11 所）；
      自招为考核资格名单口径（非预录取）。
      体育/艺术 project 去掉末尾"（项目）"得到招生高中（校区）；自招标题去"2026年"前缀。
      矩阵 key 使用名单原文（可溯源）；业务关联同时产出 high_school_ids，
      前端/共享层必须用该实体外键，不得再按高中名称二次匹配。
"""
import json
import sys, re, collections, os

BASE = 'data/linkage/parsed'

# 统一匹配库：norm 本体收敛至 school_match.normName（原"复刻 shared normName"定义已删）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "data", "registry", "entity", "scripts"))
from school_match import matchNorm, normName as norm  # 归一收敛至统一匹配库：剥区名 + 去括号变体
# （2026-09-21 别名瘦身后「区+名字」形态不再生成；带区名名单名由 matchNorm 剥区兜底，
#  仍保持「实体表高中别名唯一收敛」语义——法人名多校区宁缺，由实体别名表精确归位）
OUT = sys.argv[1] if len(sys.argv) > 1 else 'data/linkage/dist/special_matrix.json'
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
entities = json.load(open('data/registry/entity/dist/entities.json'))['entities']
entity_by_id = {e['school_id']: e for e in entities if e.get('stage') == 'high'}
high_aliases: dict[str, list[dict]] = collections.defaultdict(list)  # 归一化别名 → 高中实体候选
high_aliases_exact: dict[str, list[dict]] = collections.defaultdict(list)  # normName（带区精确）键，剥区歧义回退用
for e in entities:
    if e.get('stage') != 'high':
        continue
    for a in [e['name']] + (e.get('aliases') or []):
        na = matchNorm(a)
        if na:
            high_aliases[na].append(e)
            _flat = na.replace('(', '').replace(')', '')
            if _flat != na:
                high_aliases[_flat].append(e)
        _na = norm(a)
        if _na:
            high_aliases_exact[_na].append(e)


def resolve_entity(name: str):
    """名单高中原文 → 唯一高中实体。

    这是唯一允许用名称解析第一批招生单位的构建期入口。候选必须收敛到唯一
    school_id；未命中或歧义一律返回 None，留在审计输出，禁止取第一个候选。
    统一先套 SPECIAL_NAME_FIX（裸名多校区歧义显式归位；2026-09-21 由
    source_name_mappings 退役迁移），所有调用点（high_entities/自招/特长生）一致受益。
    """
    name = SPECIAL_NAME_FIX.get(name, name)
    n = matchNorm(name)
    candidates = {e['school_id']: e for e in high_aliases.get(n, [])}
    if not candidates:
        _flat = n.replace('(', '').replace(')', '')
        if _flat != n:
            candidates = {e['school_id']: e for e in high_aliases.get(_flat, [])}
    if not candidates:
        # 名单名带校区括号（如「广州市海珠外国语实验中学（校本部）」）而实体无括号：normName
        # 删括号精确键回退（多校区 norm 撞车时 >1 候选宁缺，不走错配）
        candidates = {e['school_id']: e for e in high_aliases_exact.get(norm(name), [])}
    if len(candidates) > 1:
        # 剥区歧义回退 normName 精确键（带区名）：如「广州市白云艺术中学」matchNorm「艺术中学」
        # 撞越秀/白云两家 → normName「白云艺术中学」唯一收敛（2026-09-21 别名瘦身暴露）
        candidates = {e['school_id']: e for e in high_aliases_exact.get(norm(name), [])}
    return next(iter(candidates.values())) if len(candidates) == 1 else None


# 已知截断/异常名单名 → 完整高中名（PDF 解析截断，显式修复、可审计）
HIGH_NAME_FIX = {
    '广州市第一': '广州市第一中学',  # sports/arts 23 条 project 截断，招生校为广州市第一中学
}

# 特长生计划表学校名 → 招生高中（校区）原文（领军龙单列无括号名，显式修复、可审计）
SPECIAL_NAME_FIX = {
    '华南师范大学附属中学': '华南师范大学附属中学（石牌校区）',  # 领军龙男足单列，主校区石牌
    # —— 裸名多校区歧义显式归位（2026-09-21 由 source_name_mappings 退役迁移，历史已确认）——
    '广东华侨中学': '广东华侨中学(起义路校区)',                # 特长生按起义路（完中本部）
    '广州市天河外国语学校': '广州市天河外国语学校（智慧城校区）',  # 特长生按智慧城
    '广州市第二中学': '广州市第二中学(应元路校区)',            # 特长生按应元路（本部）
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

# sports/arts：初中=school 字段；autonomy：初中=school_junior 字段。
# 名单只用于构建 all_hs（名单高中原文集合 → high_school_ids 外键，供升学路径页跳转）。
# 资格名单计数矩阵（matrix）已废弃：初中第一批模块与高中第一批覆盖表均已移除，
# 前端不再消费"每所初中升入各高中的资格人数"，故不再输出。
m_sports = agg_project(sports)
m_arts = agg_project(arts)
m_auto = agg_autonomy(auto)

all_hs = set()
for (j, h) in m_sports.keys():
    all_hs.add(h)
for (j, h) in m_arts.keys():
    all_hs.add(h)
for (j, h) in m_auto.keys():
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
PREV = sys.argv[2] if len(sys.argv) > 2 else OUT
try:
    previous = json.load(open(PREV))
except FileNotFoundError:
    previous = {}

# ---------------- 2026 自主招生计划（官方汇总表，按校区/法人公布） ----------------
plan_raw = json.load(open('data/linkage/parsed/autonomy/plan_2026.json'))
autonomy_plan = {s['name']: s['plan'] for s in plan_raw['schools']}
plan_norm = {norm(k): v for k, v in autonomy_plan.items()}
# 实体名变体：官方原文（全角"（校本部）"）与实体 POI 名（半角"（本部校区）"）存在名称差异，
# 前端按实体名反查计划时必须命中。构建期一次映射，避免运行时名称兜底。
for k, v in autonomy_plan.items():
    ent = resolve_entity(k)
    if ent and norm(ent['name']) not in plan_norm:
        plan_norm[norm(ent['name'])] = v

# ---------------- 2026 体育/艺术特长生计划（官方计划表附件1，按校区+项目） ----------------
sp_raw = json.load(open('data/linkage/parsed/special/plan_special_2026.json'))
sp_by_name = collections.defaultdict(
    lambda: {'sports': [], 'arts': [], 'sports_total': 0, 'arts_total': 0})
for s in sp_raw['schools']:
    key = SPECIAL_NAME_FIX.get(s['school'], s['school'])
    d = sp_by_name[key]
    d['sports'] += s['sports']
    d['arts'] += s['arts']
    d['sports_total'] += s.get('sports_total') or 0
    d['arts_total'] += s.get('arts_total') or 0
special_plan = {}
special_plan_unresolved = []
for name, d in sp_by_name.items():
    ent = resolve_entity(SPECIAL_NAME_FIX.get(name, name))
    if ent:
        special_plan[ent['school_id']] = {
            'name': ent['name'],
            'sports': d['sports_total'],
            'arts': d['arts_total'],
            'sports_projects': d['sports'],
            'arts_projects': d['arts'],
        }
    else:
        special_plan_unresolved.append(name)
# 审计口径：官方体育 1905（不含领军龙116）/ 艺术 1741
sp_summary = {
    'sports': sum(s.get('sports_total') or 0 for s in sp_raw['schools']
                  if not s.get('football_special')),
    'arts': sum(s.get('arts_total') or 0 for s in sp_raw['schools']),
    'football_special': sum(s.get('sports_total') or 0 for s in sp_raw['schools']
                            if s.get('football_special')),
}

out = {
    'updated': '2026-09-17',
    'scope': '全部有名单的高中（含区属/中职），名单仅用于构建"名单原文→实体 school_id"外键；资格名单计数矩阵已废弃不输出',
    'note': (
        '体育/艺术=通过专业测试名单（官方发布）；自招=综合能力考核资格名单口径（考核前≤5倍计划，非预录取）。'
        '收录范围=官方名单出现的全部招生高中（不再限省市属 11 所）；high_school_ids=名单原文→高中实体 school_id，'
        '是第一批招生关联唯一外键；值为 null 表示未收录对应高中实体，仅保留原文展示，不得名称兜底。'
        'autonomy_plan=2026官方自主招生计划数（按校区公布），计划数≠资格名单人数≠录取人数；'
        'special_plan=2026官方体育/艺术特长生计划数（按校区+项目，含领军龙足球试点单列），'
        '计划数=录取数口径（按计划投档）。'
    ),
    'high_schools': sorted(all_hs),
    'high_entities': high_entities,
    'high_school_ids': high_school_ids,
    'autonomy_plan': autonomy_plan,
    'autonomy_plan_norm': plan_norm,
    'autonomy_plan_source': plan_raw['source_url'],
    'special_plan': special_plan,
    'special_plan_source': sp_raw['url'],
    'special_plan_summary': sp_summary,
}
if previous.get('middle_school_ids'):
    out['middle_school_ids'] = previous['middle_school_ids']
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('高中招生单位数:', len(all_hs))
print('收录记录: 体育', sum(m_sports.values()), '艺术', sum(m_arts.values()), '自招', sum(m_auto.values()))
print('未匹配到高中实体的名单名（需人工复核）:', len(unresolved))
for u in unresolved:
    print('  !', u)
print('特长生计划未匹配实体:', len(special_plan_unresolved))
for u in special_plan_unresolved:
    print('  !', u)
print('特长生计划审计: 体育', sp_summary['sports'], '(不含领军龙) / 艺术', sp_summary['arts'],
      '/ 领军龙足球', sp_summary['football_special'])
