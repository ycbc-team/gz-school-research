#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二批次指标结果聚合（省市属/区属最低分 + 指标浪费率 + 近3年最低分均值）。

输入（B 层规范表 / A 层转录）：
  - parsed/batch2_scores_all.json   2026 官方第二批次录取分数全量转录（109 所高中，含空分未录取对）
  - parsed/batch2_scores_2025.json  2025 转录（结构同 2026）
  - parsed/batch2_scores_2024.json  2024 转录（校名带（初中校区/初中部/校本部）后缀，
                                     本脚本做跨年归一）
  - parsed/canonical/batch2_scores.json  省市属 11 所 20 校区规范表（CITY 名单口径真源）
  - parsed/canonical/quota_matrix.json   名额分配计划规范表（初中名单 + school_id/school_ids +
                                         sheng_quota/qu_quota 指标总数）

口径（与 build_linkage_batch2.py 一致，另补广州外国语学校）：
  - 省市属 = build_linkage_batch2.is_city(senior) 的 20 校区 + 「广州外国语学校」
    （市属示范高中，官方名额表 sz 已含但 canonical batch2 的 CITY 名单历史遗漏；聚合层补入，
    canonical batch2 本身不改，缺口以本表为准）。
  - 区属 = 其余全部（区属示范高中，名额分配面向本区初中）。
  - 最低分 = 该校录取对（min_score 非空）中 min_score 的最小值（升学分数门槛，绝对值同场
    中考可比；仅省市属/区属各自维度内比，与指标数/浪费率并列展示）。
  - 近3年最低分均值 = 2024/2025/2026 各年（录取对 min_score 最小值）的时间维算术平均；
    某年无录取记录（未参加名单 / 无数据）不参与平均，均值基于实际有分年。
  - 浪费率 = 未录取对 / 有指标对（对数口径）。官方分数表按「初中×高中」对列出全部有指标的
    对，空 min_score = 有指标但未完成录取（未达控制线/无人报考）。区属名额无逐对明细
    （qu_quota 仅总数），故省市属/区属统一采用对数口径，保证两列可比。

输出：
  - parsed/canonical/quota_outcome.json  规范表（含 school_id/school_ids 与全部调试对数字段、
                                         每年最低分与 3 年均值）
  - dist/quota_outcome.json              运行时精简（ids 优先 + schools 原文兜底；只留
                                         最低分/近3年均值/指标数/浪费率，调试对数/未录取数只进 canonical）
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LINK = ROOT / 'data' / 'linkage'
CANON = LINK / 'parsed' / 'canonical'
DIST = LINK / 'dist'
ALL = LINK / 'parsed' / 'batch2_scores_all.json'
R2025 = LINK / 'parsed' / 'batch2_scores_2025.json'
R2024 = LINK / 'parsed' / 'batch2_scores_2024.json'
NAME_EQ = LINK / 'src' / 'name_equivalents.json'

sys.path.insert(0, str(ROOT / 'data' / 'registry' / 'entity' / 'scripts'))
from school_match import normName as norm, SchoolMatcher

# 与 build_linkage_batch2.py 的 CITY_PREFIX / is_city 保持同源
CITY_PREFIX = [
    '华南师范大学附属中学', '广东实验中学', '广东广雅中学',
    '广州市执信中学', '广州市第二中学', '广州市第六中学',
    '广州大学附属中学', '广州市铁一中学', '广东华侨中学',
    '广州协和学校', '清华附中湾区学校',
]
# 市属示范高中：官方名额分配面向全市（quota sz 已含），canonical batch2 CITY 名单历史遗漏
CITY_EXTRA = {'广州外国语学校'}

# TOP14 指标：省市属 20 校区中排除 6 校区（用户拍板 2026-10-03，三年名额分配控制线低位/新校区，
# 会把强初中的"省市属最低分"拉低到与其实力不符——如铁一番禺被华侨 619 拖累）：
# 广东华侨中学、广州协和学校、六中（从化校区）、六中（花都校区）、清华附中湾区（智谷/智慧城校区）。
TOP14_EXCLUDE_EXACT = {'广东华侨中学', '广州协和学校'}
TOP14_EXCLUDE_SUFFIX = [
    ('广州市第六中学', '从化校区'),
    ('广州市第六中学', '花都校区'),
    ('清华附中湾区学校', '智谷校区'),
    ('清华附中湾区学校', '智慧城校区'),
]

# 2024 官方表特有的校区/学部后缀（2025 起不再写），跨年归一在聚合层去后缀后再匹配
_2024_SUFFIX = re.compile(r'（(初中校区|初中部|校本部)）$')


def is_city(s: str) -> bool:
    if s in CITY_EXTRA:
        return True
    for pfx in CITY_PREFIX:
        if s == pfx:
            return True
        if s.startswith(pfx) and s[len(pfx):].startswith('（'):
            return True
    return False


def is_top14(s: str) -> bool:
    """TOP14 指标：省市属 20 校区中排除 6 校区（不含广州外国语学校，其不在 batch2 20 校区内）。"""
    if s in CITY_EXTRA or not is_city(s):
        return False
    if s in TOP14_EXCLUDE_EXACT:
        return False
    for pfx, suffix in TOP14_EXCLUDE_SUFFIX:
        if s.startswith(pfx) and s[len(pfx):].startswith('（' + suffix + '）'):
            return False
    return True


def year_rows(rows, name, equivalents, matcher):
    """返回官方分数表（rows）中该初中（quota_matrix 名单名）的全部行。

    匹配顺序：norm 全等 → 等价写法（src/name_equivalents.json）→ 去 2024 后缀 →
    SchoolMatcher 实体名/别名反查（跨年/跨写法兜底）。
    """
    keys = [norm(name)]
    keys += [norm(e) for e in equivalents.get(name, [])]
    s = _2024_SUFFIX.sub('', name)
    keys += [norm(s)]
    seen = set()
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        # rows 侧同样剥 2024 特有后缀：norm 删括号但保留括号内文字，
        # 「广州市第一中学（初中校区）」→norm→「广州市第一中学初中校区」，
        # 不剥则与名单名「广州市第一中学」永远不等。
        out = [r for r in rows
               if norm(r['junior']) == k or norm(_2024_SUFFIX.sub('', r['junior'])) == k]
        if out:
            return out
    # SchoolMatcher 兜底：实体名/别名 norm 集合反查
    rid = matcher.resolve_all(s, preferred_stage='初中')
    if rid:
        nm = set()
        for e in rid:
            nm.add(norm(e.get('name') or e.get('school') or ''))
            for a in (e.get('aliases') or []):
                nm.add(norm(a))
        out = [r for r in rows if norm(r['junior']) in nm]
        if out:
            return out
    return []


def summarize(ps):
    """录取对 → min_score（录取对最小值）/ pairs / failed（未录取对数）。"""
    adm = [int(r['min_score']) for r in ps if r.get('min_score')]
    return {
        'min_score': min(adm) if adm else None,
        'pairs': len(ps),
        'failed': sum(1 for r in ps if not r.get('min_score')),
    }


def main() -> int:
    rows26 = json.load(open(ALL, encoding='utf-8'))
    rows25 = json.load(open(R2025, encoding='utf-8'))
    rows24 = json.load(open(R2024, encoding='utf-8'))
    q = json.load(open(CANON / 'quota_matrix.json', encoding='utf-8'))

    # 初中官方名单 → norm 索引（quota_matrix.schools 是全部参与名额分配的初中）
    idx = defaultdict(list)
    for s in q['schools']:
        idx[norm(s['school'])].append(s)

    # 官方两表同校异写校正（src/name_equivalents.json：quota 行名 → 录取分数表等价写法）
    neq = json.load(open(NAME_EQ, encoding='utf-8'))['equivalents'] if NAME_EQ.exists() else {}
    matcher = SchoolMatcher.load()

    # 每初中聚合（以 quota_matrix 行键，三年 junior 原文名逐级匹配）
    agg = {}
    unmatched = []
    for s in q['schools']:
        name = s['school']
        names = [name] + neq.get(name, [])
        nset = {norm(n) for n in names}
        pairs26 = [r for r in rows26 if norm(r['junior']) in nset]
        if not pairs26:
            unmatched.append(name)

        def dims(ps):
            return summarize([r for r in ps if is_city(r['senior'])]), \
                   summarize([r for r in ps if not is_city(r['senior'])]), \
                   summarize([r for r in ps if is_top14(r['senior'])])

        sh, quh, t14 = dims(pairs26)
        # 2025 / 2024 各年（跨年归一，只取最低分门槛；浪费率口径逐年名单不同不可比，不进产物）
        sh25, qu25, t1425 = dims(year_rows(rows25, name, neq, matcher))
        sh24, qu24, t1424 = dims(year_rows(rows24, name, neq, matcher))

        def avg(*vals):
            vs = [v for v in vals if v is not None]
            return round(sum(vs) / len(vs), 1) if vs else None

        agg[name] = {
            'school': name,
            'school_id': s.get('school_id'),
            'school_ids': s.get('school_ids'),
            'sheng_min_score': sh['min_score'],
            'qu_min_score': quh['min_score'],
            'top14_min_score': t14['min_score'],
            'sheng_min_2024': sh24['min_score'],
            'sheng_min_2025': sh25['min_score'],
            'sheng_min_2026': sh['min_score'],
            'sheng_min_3y_avg': avg(sh24['min_score'], sh25['min_score'], sh['min_score']),
            'qu_min_2024': qu24['min_score'],
            'qu_min_2025': qu25['min_score'],
            'qu_min_2026': quh['min_score'],
            'qu_min_3y_avg': avg(qu24['min_score'], qu25['min_score'], quh['min_score']),
            'top14_min_2024': t1424['min_score'],
            'top14_min_2025': t1425['min_score'],
            'top14_min_2026': t14['min_score'],
            'top14_min_3y_avg': avg(t1424['min_score'], t1425['min_score'], t14['min_score']),
            'sheng_quota': s.get('sheng_quota'),
            'qu_quota': s.get('qu_quota'),
            'top14_quota': sum(v for k, v in (s.get('sz') or {}).items() if is_top14(k)),
            'sheng_pairs': sh['pairs'],
            'sheng_failed': sh['failed'],
            'qu_pairs': quh['pairs'],
            'qu_failed': quh['failed'],
            'top14_pairs': t14['pairs'],
            'top14_failed': t14['failed'],
            'sheng_waste_rate': round(sh['failed'] / sh['pairs'], 4) if sh['pairs'] else None,
            'qu_waste_rate': round(quh['failed'] / quh['pairs'], 4) if quh['pairs'] else None,
            'top14_waste_rate': round(t14['failed'] / t14['pairs'], 4) if t14['pairs'] else None,
        }

    total = len(agg)
    with_min = sum(1 for v in agg.values() if v['sheng_min_score'] is not None or v['qu_min_score'] is not None)
    with_3y = sum(1 for v in agg.values() if v['sheng_min_3y_avg'] is not None or v['qu_min_3y_avg'] is not None)
    print(f'初中总数 {total} | 有最低分 {with_min} | 有3年均值 {with_3y} | 未命中 2026 ALL 初中名 {len(unmatched)}')

    canon = {
        'title': '第二批次指标结果聚合（省市属/TOP14/区属最低分 + 指标浪费率 + 近3年最低分均值）',
        'updated': '2026-10-03',
        'source': '广州市招考办《2024/2025/2026年广州市高中阶段学校招生录取分数（第二批次招生学校）（按初中学校排序）》+ 名额分配计划汇总表',
        'note': '省市属 = 11 所 20 校区 + 广州外国语学校（市属，canonical batch2 CITY 名单历史遗漏，聚合层补入）；区属 = 其余示范高中。TOP14 = 省市属 20 校区中排除 6 校区（广东华侨中学、广州协和学校、六中从化/花都校区、清华附中湾区智谷/智慧城校区，三年名额分配控制线低位或新校区）后的 14 所头部校区，不含广州外国语学校；用户拍板 2026-10-03，用于避免弱校把强初中最低分拉低（如铁一番禺被华侨 619 拖累，TOP14 口径 726）。最低分 = 该校录取对 min_score 最小值（升学分数门槛，同场中考绝对值可比）。近3年最低分均值 = 2024/2025/2026 各年最低分（录取对 min_score 最小值）的时间维算术平均；某年无录取记录不参与平均（初中名单逐年变化，均值基于实际有分年）。浪费率 = 未录取对 / 有指标对（对数口径，2026 一年）；区属无名额逐对明细，统一对数口径保证两列可比。top14_quota = quota_matrix.sz 中 14 校区指标数求和（与 sheng_quota 同源口径，21 校区 sz 求和 = sheng_quota）；top14 浪费率 = top14_failed / top14_pairs（对数口径）。调试字段（pairs/failed/每年最低分）仅 canonical，dist 删除（dist 只留 top14_min_score/3年均值/指标数/浪费率）。',
        'data': agg,
    }
    (CANON / 'quota_outcome.json').write_text(
        json.dumps(canon, ensure_ascii=False, indent=1), 'utf-8')

    # dist：ids（唯一 id 一份）/ schools（无 id 原文 + 多名同 id 且数据不同的冲突行保底原文，
    # 与 backfill district_quota 的 id_conflicts 同款：数据不同不合并、不丢行）。
    DIST_FIELDS = ['sheng_min_score', 'qu_min_score', 'top14_min_score',
                   'sheng_min_3y_avg', 'qu_min_3y_avg', 'top14_min_3y_avg',
                   'sheng_quota', 'qu_quota', 'top14_quota',
                   'sheng_waste_rate', 'qu_waste_rate', 'top14_waste_rate']
    ids, schools = {}, {}
    for name, v in agg.items():
        slim = {k: v[k] for k in DIST_FIELDS}
        if v['school_id']:
            if v['school_id'] in ids:
                if ids[v['school_id']] != slim:
                    schools[name] = slim  # 同 id 数据不同：冲突名保底原文，不合并
                # 数据相同（同法人多校区行值一致）：ids 一份足够，忽略
            else:
                ids[v['school_id']] = slim
        else:
            schools[name] = slim
    dist = {'ids': ids, 'schools': schools}
    (DIST / 'quota_outcome.json').write_text(
        json.dumps(dist, ensure_ascii=False, indent=1), 'utf-8')

    print(f'canonical 写入（{total} 初中）→ dist ids({len(ids)})/schools({len(schools)})')
    # 抽样验证
    for name in ['中山大学附属中学', '广州市第一中学', '广州市绿翠现代实验学校', '广州市铁一中学（番禺校区）']:
        if name in agg:
            v = agg[name]
            print(f'  样例 {name}: 省市属最低分={v["sheng_min_score"]} TOP14最低分={v["top14_min_score"]} '
                  f'TOP14 3年均值={v["top14_min_3y_avg"]} '
                  f'（24:{v["top14_min_2024"]} 25:{v["top14_min_2025"]} 26:{v["top14_min_2026"]}） '
                  f'TOP14指标数={v["top14_quota"]} TOP14浪费率={v["top14_waste_rate"]} '
                  f'省市属3年均值={v["sheng_min_3y_avg"]} '
                  f'区属最低分={v["qu_min_score"]} 区属3年均值={v["qu_min_3y_avg"]} '
                  f'省市属浪费率={v["sheng_waste_rate"]} 区属浪费率={v["qu_waste_rate"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
