#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排行榜数据聚合：初中升学信号三源合并 → data/linkage/ranking_middle.json

输入（只读，不修改任何源文件）：
- data/linkage/quota_matrix.json             指标到校（496 所；以 7 区学校为候选底：
                                              kaosheng 考生数 / sheng_quota 省市属 / qu_quota 区属 / sz 高中名额明细 / district / school_id）
- data/linkage/raw/autonomy/autonomy_qualify_2026.json  自主招生资格名单（按来源初中计数）
- data/high/levels.json                      高中特控率（indicators.tekong_2026/tekong_2025，文本口径，只读）

输出：
- data/linkage/ranking_middle.json          每所初中：考生数/省市属指标/区属指标/自招数/指标到校高中明细（含特控率）
  该文件位于 data/ 下（非 raw），会被 scripts/data/compact.mjs 自动编译进 Web/小程序 compact 产物。

口径说明：
- 候选底：quota_matrix 中 7 区（荔湾/越秀/海珠/天河/白云/黄埔/番禺）全量初中，口碑判定已移除。
- kaosheng：名额分配符合资格考生数（政策按此比例分配指标，全网口径一致）
- 特控率：特殊类型招生控制线（高优线/重本线）上线率，来自 levels.json 喜报/网传文本，
  非官方统一发布；解析为数值仅供横向参考，缺失为 null。
- tekong_quota_rate：Σ(区属高中给该校指标名额 × 该区属高中特控率) / 该校名额分配考生数（kaosheng），
  反映"该校考生经区属指标到校路径、预计能上特控（一本）线的比例"；分子仅计有特控率数据的
  区属高中名额（缺失不计，会低估，note 已说明）。区属高中明细来自 district_quota（data[初中名][高中名]）。
"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'

# 候选底覆盖的 7 个区（与页面 DISTRICTS 顺序一致的区名全称）
SEVEN_DISTRICTS = {'荔湾区', '越秀区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区'}


def load(name: str):
    with open(DATA / name, encoding='utf-8') as f:
        return json.load(f)


def norm(name: str) -> str:
    """去括号内容 + 去 市/省 前缀 → 核心名（用于无歧义匹配）"""
    n = re.sub(r'[（(].*?[)）]', '', name)
    return n.replace('广州市', '').replace('广东', '').replace('广州', '').strip()


def canon_bracket(name: str) -> str:
    """全角括号转半角，用于校区名匹配"""
    return name.replace('（', '(').replace('）', ')').strip()


# ---------------- 集团归属（brand 优先 + education 兜底，口径与 shared 一致） ----------------
def py_norm(s: str) -> str:
    """复刻 TS normName：去「广州市/广东」前缀、括号符号统一去除、去空白（保留括号内文字）"""
    return re.sub(r'[（(]', '(', s).replace('）', ')').replace('(', '').replace(')', '')\
        .replace('广州市', '').replace('广东', '').replace(' ', '').strip()


def py_loose(s: str) -> str:
    """复刻 TS looseNorm：norm 后再去尾部学部/校区后缀（注意：'（本部）' 会残留'本'）"""
    return re.sub(r'(初中部|高中部|小学部|校区|分校|学校|部)$', '', py_norm(s))


def py_loose2(s: str) -> str:
    """更强 loose：去括号及内容 + 去尾部学部/校区后缀（education 兜底用）"""
    n = re.sub(r'[（(].*?[)）]', '', s).replace('广州市', '').replace('广东', '').replace(' ', '')
    return re.sub(r'(初中部|高中部|小学部|校区|分校|学校|部)$', '', n).strip()


brand_groups = load('registry/brand_groups.json')['brands']
# education: group brand + 全部成员名（core_poi/members/campuses 的 name/poi_name）
education_groups = load('registry/education_groups.json')['groups']


def group_of(school_name: str):
    n = py_norm(school_name)
    # 1. brand（8 大品牌，全等）
    for g in brand_groups:
        for u in g.get('units', []):
            cands = [u.get('name')] + (u.get('poi_names') or [])
            if any(py_norm(c) == n for c in cands if c):
                return {'brand': g['brand'], 'source': 'brand'}
    # 2. education（85 集团，loose 全等；'（本部）' 类括号残留需第二层去括号内容）
    ln = py_loose(school_name)
    ln2 = py_loose2(school_name)
    for g in education_groups:
        names = []
        for p in g.get('core_poi') or []:
            names += [p.get('name'), p.get('poi_name')]
        for m in g.get('members') or []:
            names += [m.get('name'), m.get('poi_name')]
            for c in m.get('campuses') or []:
                names += [c.get('name'), c.get('poi_name')]
        if any(py_loose(x) == ln or (ln2 and py_loose2(x) == ln2) for x in names if x):
            return {'brand': g['brand'], 'source': 'education'}
    return None


# ---------------- 载入 ----------------
quota = load('linkage/quota_matrix.json')
autonomy = load('linkage/raw/autonomy/autonomy_qualify_2026.json')
levels = load('high/levels.json')
district_quota = load('linkage/district_quota.json')
# 民办身份唯一真源：registry/entities.json（nature='民办'；公办不写字段）
MINBAN_IDS = {e['school_id'] for e in load('registry/entities.json').get('entities', []) if e.get('nature') == '民办'}

# ---------------- 自招按来源初中计数 ----------------
aut_cnt = Counter(a['school_junior'] for a in autonomy)

# ---------------- 特控率解析 ----------------
def parse_tekong(text):
    """文本 → 数值百分比：'特控率60%'→60、'超75%'→75、'九成'→90、无数字→None。
    排除'提升4%'/'同比增长'类误读（只认明确口径或裸百分比）。"""
    if not text:
        return None
    # 1. 明确"率"口径：特控/上线/重本/一本/高优/本科率 [间隔≤6字] 数字%
    m = re.search(r'(?:特控|上线|重本|一本|高优|本科)率[^0-9]{0,6}?(\d+(?:\.\d+)?)\s*%', text)
    if m:
        return float(m.group(1))
    # 2. 超/达/约/近 + 数字%
    m = re.search(r'(?:超|达|约|近)\s*(\d+(?:\.\d+)?)\s*%', text)
    if m:
        return float(m.group(1))
    # 3. 数字成（九成→90）
    m = re.search(r'([0-9一二三四五六七八九]+)\s*成', text)
    if m:
        cn = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
        s = m.group(1)
        v = int(s) if s.isdigit() else cn.get(s, None)
        if v is not None:
            return v * 10.0
    # 4. 兜底裸百分比（排除'提升/增长/降低/减少/同比/多'等前导的误读）
    m = re.search(r'(?<![提升增长降低减少多同])(\d+(?:\.\d+)?)\s*%', text)
    if m:
        return float(m.group(1))
    return None

# 建立 高中校区名(canon) / 官方名 → 特控率（优先 2026，兜底 2025）
tekong_by_name = {}
for sc in levels.get('schools', []):
    ind = sc.get('indicators', {})
    rate = parse_tekong(ind.get('tekong_2026')) or parse_tekong(ind.get('tekong_2025'))
    if rate is None:
        continue
    for cn in [sc.get('name')] + sc.get('campuses', []):
        if cn:
            tekong_by_name[canon_bracket(cn)] = rate

# ---------------- 别名表 ----------------
# 历史口碑校区名 → quota_matrix school 名（招考办口径）。
# 现候选底直接用 quota_matrix 的 school 名，此表主要用于：
#   1) group_of 反查（quota 校区名未命中集团时，回退到口碑口径名再匹配）；
#   2) EXTRA_SCHOOLS 补充学校解析。
QUOTA_ALIAS = {
    '广东实验中学（初中部）': '广东实验中学（越秀校区）',
    '广州市执信中学（执信路校区）': '广州市执信中学（越秀校区）',
    '广州市第二中学（初中部）': '广州市第二中学（越秀校区）',
    '广州市第七中学（本部）': '广州市第七中学',
    '广州市第十六中学（本部）': '广州市第十六中学',
    '广东广雅中学（初中部）': '广东广雅中学（荔湾校区）',
    '广州市真光中学（校本部）': '广州市真光中学',
    '广州市第六中学（本部）': '广州市第六中学（海珠校区）',
    '广州市第五中学（本部）': '广州市第五中学',
    '广州市南武中学（本部）': '广州市南武中学',
    '华南师范大学附属中学（初中部）': '华南师范大学附属中学（五山校区）',
    '广州市培正中学（初中部）': '广州市培正中学',
    '广东仲元中学（初中部）': '广东仲元中学',
    '广州市铁一中学（番禺校区/亚运城）': '广州市铁一中学（番禺校区）',
    '广州市白云区铁一学校（白云铁一）': '广州市铁一中学（白云校区）',
    '华南师范大学附属中学（知识城校区）': '华南师范大学附属中学（知识城校区）',
    '广州市番禺区广铁一中铁英学校（番禺铁英）': '广州市番禺区广铁一中铁英学校',
    '广州市番禺区桥城中学': '广州市番禺区市桥桥城中学',
    '广州市番禺执信中学（星执学校，民办）': '广州市星执学校',
    '广州市白云区金广实验学校（金广附/广大附中实验中学）': '广州市白云区广大附中实验中学',
    '广州市白云实验学校（白云省实，民办）': '广州市白云区白云实验学校',
    '广州市天河外国语学校（珠江新城校区）': '广州市天河外国语学校',
    '广州大学附属中学（黄华路校区）': '广州大学附属中学（越秀校区）',
    '广东实验中学永平校区（省实永平）': '广东实验中学（白云校区）',
    '广州大学附属中学（大学城校区）': '广州大学附属中学（番禺校区）',
    '广州市第一中学': '广州市第一中学',
    '广州市第四中学': '广州市第四中学',
    '广州市西关外国语学校': '广州市西关外国语学校',
    '广州市天河中学': '广州市天河中学',
    '广州市第一一三中学': '广州市第一一三中学',
    '广州市第八十六中学': '广州市第八十六中学',
    '清华附中湾区学校': '清华附中湾区学校',
    '中山大学附属中学': '中山大学附属中学',
    '广州中学': '广州中学',
    '广州市越秀区育才实验学校': '广州市越秀区育才实验学校',
    '广州市天河区汇景实验学校': '广州市天河区汇景实验学校',
    '广州市海珠外国语实验中学': '广州市海珠外国语实验中学',
    '北京师范大学广州实验学校': '北京师范大学广州实验学校',
    '广东实验中学荔湾学校（省实荔湾）': '广东实验中学荔湾学校',
    '广州市荔湾区西关广雅实验学校（西雅）': '广州市荔湾区西关广雅实验学校',
    '广州市白云区华赋学校（民办）': '广州市白云区华赋学校',
    '广州市白云区云雅实验学校（云雅/白云广雅，民办）': '广州市白云区云雅实验学校',
    '广州天省实验学校（民办）': '广州天省实验学校',
    '广州市第二中学（科学城校区）': '广州市第二中学（科学城校区）',
    '广州市黄埔区苏元学校（二中苏元）': '广州市黄埔区苏元学校',
    '广州市黄埔区铁英学校（黄埔铁英）': '广州市黄埔区铁英中学',
    '广州市番禺区祈福新邨学校（小金龙，民办）': '广州市番禺区祈福新邨学校',
    '广州市番禺区恒润实验学校（民办）': '广州市番禺区恒润实验学校',
    '广州市番禺区番外外国语学校（番外，民办）': '广州市番禺区番外外国语学校',
    '广州大学附属中学黄埔实验学校（黄埔广附）': '广大附中黄埔实验学校',
}
# 自招名单用校区名（与 quota 相同的招考办口径，多数同名；个别不同单独列出）
AUT_ALIAS = {
    '广东实验中学（初中部）': '广东实验中学（越秀校区）',
    '广州市执信中学（执信路校区）': '广州市执信中学（越秀校区）',
    '广州市第二中学（初中部）': '广州市第二中学（越秀校区）',
    '广东广雅中学（初中部）': '广东广雅中学（荔湾校区）',
    '广州市真光中学（校本部）': '广州市真光中学',
    '广州市第六中学（本部）': '广州市第六中学（海珠校区）',
    '广州市第五中学（本部）': '广州市第五中学',
    '广州市南武中学（本部）': '广州市南武中学',
    '华南师范大学附属中学（初中部）': '华南师范大学附属中学（五山校区）',
    '广东仲元中学（初中部）': '广东仲元中学',
    '广州市第七中学（本部）': '广州市第七中学',
    '广州市第十六中学（本部）': '广州市第十六中学',
    '广州市培正中学（初中部）': '广州市培正中学',
    '广州市天河外国语学校（珠江新城校区）': '广州市天河外国语学校（珠江新城校区）',
    '广州大学附属中学（黄华路校区）': '广州大学附属中学（越秀校区）',
    '广东实验中学永平校区（省实永平）': '广东实验中学（白云校区）',
    '广州大学附属中学（大学城校区）': '广州大学附属中学（番禺校区）',
    '广州市白云区金广实验学校（金广附/广大附中实验中学）': '广州市白云区广大附中实验中学',
    '广州市白云实验学校（白云省实，民办）': '广州市白云区白云实验学校',
    '广州市铁一中学（番禺校区/亚运城）': '广州市铁一中学（番禺校区）',
    '广州市番禺区桥城中学': '广州市番禺区市桥桥城中学',
    '广州市番禺执信中学（星执学校，民办）': '广州市星执学校',
    '广州市黄埔区铁英学校（黄埔铁英）': '广州市黄埔区铁英中学',
    '广州大学附属中学黄埔实验学校（黄埔广附）': '广大附中黄埔实验学校',
    '广州市白云区铁一学校（白云铁一）': '广州市铁一中学（白云校区）',
    # quota 名与官方自招名单名差「市」字：显式归一（保留括号精确匹配，避免 norm 去括号撞多校区）
    '广州铁一中学（番禺校区）': '广州市铁一中学（番禺校区）',
    # 新校区：自招名单无独立条目（越秀校区≠科学城校区，强制 0 避免 norm 误配）
    '广州市第二中学（科学城校区）': '',
}

quota_by_name = {s['school']: s for s in quota['schools']}
# 反查表：quota 名 → 历史口碑口径名（用于 group_of 回退匹配）
QUOTA_REVERSE = {v: k for k, v in QUOTA_ALIAS.items()}


def find_quota(name: str):
    qn = QUOTA_ALIAS.get(name)
    if qn and qn in quota_by_name:
        return qn, quota_by_name[qn]
    if name in quota_by_name:
        return name, quota_by_name[name]
    c = norm(name)
    hits = [(qn, sv) for qn, sv in quota_by_name.items() if norm(qn) == c]
    if len(hits) == 1:
        return hits[0]
    return None, None


def find_aut(name: str) -> int:
    an = AUT_ALIAS.get(name, name)
    if an and an in aut_cnt:
        return aut_cnt[an]
    if name in aut_cnt:
        return aut_cnt[name]
    # 唯一核心名兜底（避免漏计；歧义校区已在 AUT_ALIAS 显式处理）
    c = norm(name)
    hits = [cnt for an2, cnt in aut_cnt.items() if norm(an2) == c]
    return hits[0] if len(hits) == 1 else 0


def tekong_of(high_name: str):
    """按校区名（规范化括号）查特控率"""
    return tekong_by_name.get(canon_bracket(high_name))


def group_resolve(name: str):
    """集团匹配：先按 quota 校区名直查；未命中则回退到历史口碑口径名（QUOTA_REVERSE）再查。"""
    g = group_of(name)
    if g:
        return g
    legacy = QUOTA_REVERSE.get(name)
    if legacy:
        return group_of(legacy)
    return None


# ---------------- 聚合 ----------------
def build_row(name: str, district: str, school_id=None):
    """单校聚合：quota / 区属指标×特控率 / 自招 / 集团。quota 缺行 → 数值字段置 null。"""
    qn, qv = find_quota(name)
    aut_n = find_aut(name)
    if qv is None:
        kaosheng = sheng_quota = qu_quota = None
        sz = []
    else:
        kaosheng = qv.get('kaosheng') or 0
        sheng_quota = qv.get('sheng_quota') or 0
        qu_quota = qv.get('qu_quota') or 0
        sz = [
            {'high': hn, 'count': int(c), 'tekong': tekong_of(hn)}
            for hn, c in (qv.get('sz') or {}).items()
        ]
    # 指标×特控率：该校考生经"区属指标到校"预计上特控线的比例
    #   = Σ(区属高中给该校指标名额 × 该区属高中特控率) ÷ 该校考生数
    # 区属高中明细来自 district_quota（data[初中名][高中名]=名额）；sz 为省市属明细（不参与此指标）
    # 分子仅计有特控率数据的区属高中名额；缺失低估，note 已说明
    dq = (district_quota.get('data') or {}).get(qn or '') or {}
    qw = [{'high': hn, 'count': int(c), 'tekong': tekong_of(hn)} for hn, c in dq.items()]
    w = [x for x in qw if x['tekong'] is not None]
    if w and kaosheng:
        tekong_quota_rate = round(sum(x['count'] * x['tekong'] for x in w) / kaosheng, 1)
    else:
        tekong_quota_rate = None
    return {
        'name': name,
        'school_id': school_id,
        'district': district,
        'minban': bool(school_id and school_id in MINBAN_IDS),
        'group': group_resolve(name),
        'kaosheng': kaosheng,
        'sheng_quota': sheng_quota,
        'qu_quota': qu_quota,
        'autonomy_count': aut_n,
        'sz': sz,
        'tekong_quota_rate': tekong_quota_rate,
    }


# ---------------- 候选底：quota_matrix 7 区全量初中 ----------------
out_schools = []
missing_quota = []
for qs in quota['schools']:
    if qs.get('district') not in SEVEN_DISTRICTS:
        continue
    out_schools.append(build_row(qs['school'], qs['district'], qs.get('school_id')))

# 补充学校机制保留（候选底已为全量，正常为空；仅用于个别未进名额分配表但有自招信号的学校）
EXTRA_SCHOOLS = []
for e in EXTRA_SCHOOLS:
    out_schools.append(build_row(e['name'], e['district'], e.get('school_id')))

result = {
    'title': '广州初中升学信号明细基础表（自招 / 指标到校 / 特控率）',
    'updated': '2026-09-15',
    'note': (
        '7区全量初中（荔湾/越秀/海珠/天河/白云/黄埔/番禺，以名额分配 quota_matrix 为底），口碑判定已移除。'
        'kaosheng=名额分配符合资格考生数（政策按此比例分配指标）；sheng_quota=省市属高中指标数；'
        'qu_quota=区属高中指标数；autonomy_count=2026 自主招生考核资格名单按来源初中计数；'
        'sz[].tekong=目标高中特控（高优/重本）上线率，喜报/网传口径解析为数值，null=无数据；'
        'tekong_quota_rate=Σ(区属高中给该校指标名额×该高中特控率)/该校考生数，即该校考生经区属指标到校'
        '预计上特控线的比例；分子仅计有特控率数据的区属高中名额，特控率缺失会低估。'
        'minban=民办办学性质标识（唯一真源 registry/entities.json nature，公办=false）。'
    ),
    'source': {
        'quota': '广州市招考办《2026年广州市名额分配招生学校招生总计划和名额分配计划汇总表》（7区全量初中）',
        'autonomy': '2026年广州市普通高中学校自主招生综合能力考核资格考生名单（13866条）',
        'tekong': 'data/high/levels.json indicators.tekong_2026/tekong_2025（喜报/网传口径）',
    },
    'schools': out_schools,
}
with open(DATA / 'linkage' / 'ranking_middle.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

from collections import Counter as _C
_dist = _C(s['district'] for s in out_schools)
print(f'输出 {len(out_schools)} 所初中 → data/linkage/ranking_middle.json')
print('7区分布:', {k: _dist[k] for k in ['荔湾区', '越秀区', '海珠区', '天河区', '白云区', '黄埔区', '番禺区']})
print('quota 未匹配:', missing_quota if missing_quota else '无')
# 校验：抽查
for s in out_schools[:6]:
    print(f"  {s['name']} | 考生={s['kaosheng']} 省={s['sheng_quota']} 区={s['qu_quota']} 自招={s['autonomy_count']} 特控={s['tekong_quota_rate']} group={s['group']}")
