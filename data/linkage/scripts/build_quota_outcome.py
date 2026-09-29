#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二批次指标结果聚合（省市属/区属最低分 + 指标浪费率）。

输入（B 层规范表）：
  - parsed/batch2_scores_all.json   官方第二批次录取分数全量转录（109 所高中，含空分未录取对）
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
  - 浪费率 = 未录取对 / 有指标对（对数口径）。官方分数表按「初中×高中」对列出全部有指标的
    对，空 min_score = 有指标但未完成录取（未达控制线/无人报考）。区属名额无逐对明细
    （qu_quota 仅总数），故省市属/区属统一采用对数口径，保证两列可比。

输出：
  - parsed/canonical/quota_outcome.json  规范表（含 school_id/school_ids 与全部调试对数字段）
  - dist/quota_outcome.json              运行时精简（ids 优先 + schools 原文兜底；只留
                                         最低分/指标数/浪费率，调试对数/未录取数只进 canonical）
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
NAME_EQ = LINK / 'src' / 'name_equivalents.json'

sys.path.insert(0, str(ROOT / 'data' / 'registry' / 'entity' / 'scripts'))
from school_match import normName as norm

# 与 build_linkage_batch2.py 的 CITY_PREFIX / is_city 保持同源
CITY_PREFIX = [
    '华南师范大学附属中学', '广东实验中学', '广东广雅中学',
    '广州市执信中学', '广州市第二中学', '广州市第六中学',
    '广州大学附属中学', '广州市铁一中学', '广东华侨中学',
    '广州协和学校', '清华附中湾区学校',
]
# 市属示范高中：官方名额分配面向全市（quota sz 已含），canonical batch2 CITY 名单历史遗漏
CITY_EXTRA = {'广州外国语学校'}


def is_city(s: str) -> bool:
    if s in CITY_EXTRA:
        return True
    for pfx in CITY_PREFIX:
        if s == pfx:
            return True
        if s.startswith(pfx) and s[len(pfx):].startswith('（'):
            return True
    return False


def main() -> int:
    rows = json.load(open(ALL, encoding='utf-8'))
    q = json.load(open(CANON / 'quota_matrix.json', encoding='utf-8'))

    # 初中官方名单 → norm 索引（quota_matrix.schools 是全部参与名额分配的初中）
    idx = defaultdict(list)
    for s in q['schools']:
        idx[norm(s['school'])].append(s)

    # 官方两表同校异写校正（src/name_equivalents.json：quota 行名 → 录取分数表等价写法）
    neq = json.load(open(NAME_EQ, encoding='utf-8'))['equivalents'] if NAME_EQ.exists() else {}

    # 每初中聚合（以 quota_matrix 行键，ALL junior 原文名 norm 匹配，含等价写法兜底）
    agg = {}
    unmatched = []
    for s in q['schools']:
        name = s['school']
        names = [name] + neq.get(name, [])
        nset = {norm(n) for n in names}
        pairs = [r for r in rows if norm(r['junior']) in nset]
        if not pairs:
            unmatched.append(name)
        sheng = [r for r in pairs if is_city(r['senior'])]
        qu = [r for r in pairs if not is_city(r['senior'])]

        def summarize(ps):
            adm = [int(r['min_score']) for r in ps if r.get('min_score')]
            return {
                'min_score': min(adm) if adm else None,
                'pairs': len(ps),
                'failed': sum(1 for r in ps if not r.get('min_score')),
            }

        sh, quh = summarize(sheng), summarize(qu)
        agg[name] = {
            'school': name,
            'school_id': s.get('school_id'),
            'school_ids': s.get('school_ids'),
            'sheng_min_score': sh['min_score'],
            'qu_min_score': quh['min_score'],
            'sheng_quota': s.get('sheng_quota'),
            'qu_quota': s.get('qu_quota'),
            'sheng_pairs': sh['pairs'],
            'sheng_failed': sh['failed'],
            'qu_pairs': quh['pairs'],
            'qu_failed': quh['failed'],
            'sheng_waste_rate': round(sh['failed'] / sh['pairs'], 4) if sh['pairs'] else None,
            'qu_waste_rate': round(quh['failed'] / quh['pairs'], 4) if quh['pairs'] else None,
        }

    total = len(agg)
    with_min = sum(1 for v in agg.values() if v['sheng_min_score'] is not None or v['qu_min_score'] is not None)
    print(f'初中总数 {total} | 有最低分 {with_min} | 未命中 ALL 初中名 {len(unmatched)}')

    canon = {
        'title': '第二批次指标结果聚合（省市属/区属最低分 + 指标浪费率）',
        'updated': '2026-09-29',
        'source': '广州市招考办《2026年广州市高中阶段学校招生录取分数（第二批次招生学校）（按初中学校排序）》+ 名额分配计划汇总表',
        'note': '省市属 = 11 所 20 校区 + 广州外国语学校（市属，canonical batch2 CITY 名单历史遗漏，聚合层补入）；区属 = 其余示范高中。最低分 = 该校录取对 min_score 最小值（升学分数门槛，同场中考绝对值可比）。浪费率 = 未录取对 / 有指标对（对数口径；区属无名额逐对明细，统一对数口径保证两列可比）；调试字段 sheng_pairs/sheng_failed/qu_pairs/qu_failed 仅 canonical，dist 删除。',
        'data': agg,
    }
    (CANON / 'quota_outcome.json').write_text(
        json.dumps(canon, ensure_ascii=False, indent=1), 'utf-8')

    # dist：ids（唯一 id 一份）/ schools（无 id 原文 + 多名同 id 且数据不同的冲突行保底原文，
    # 与 backfill district_quota 的 id_conflicts 同款：数据不同不合并、不丢行）。
    # 例：南悦中学/景泰中学官方名单两行均匹配实体 2186a02a（景泰白云湖校区，南悦别名并入），
    # 但两行指标数据不同——冲突行走 schools 原文各自保留。
    DIST_FIELDS = ['sheng_min_score', 'qu_min_score', 'sheng_quota', 'qu_quota',
                   'sheng_waste_rate', 'qu_waste_rate']
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
    for name in ['中山大学附属中学', '广州华联外语实验学校', '广州市第一一三中学']:
        if name in agg:
            v = agg[name]
            print(f'  样例 {name}: 省市属最低分={v["sheng_min_score"]} 区属最低分={v["qu_min_score"]} '
                  f'省市属浪费率={v["sheng_waste_rate"]} 区属浪费率={v["qu_waste_rate"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
