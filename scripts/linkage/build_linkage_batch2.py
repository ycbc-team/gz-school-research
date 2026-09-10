# -*- coding: utf-8 -*-
"""从全量第二批次数据过滤省市属 11 所高中，生成结构化 JSON
说明：分数表为"初中-高中对"聚合行；空分数=有指标但未完成录取（未达控制线/无人报考）。
指标计划数 n_ji 需与名额分配计划明细表合并（quota 表）。"""
import json, re
from collections import defaultdict

ALL = 'data/linkage/raw/batch2_scores_all.json'
OUT = 'data/linkage/batch2_scores.json'

CITY_PREFIX = [
    '华南师范大学附属中学', '广东实验中学', '广东广雅中学',
    '广州市执信中学', '广州市第二中学', '广州市第六中学',
    '广州大学附属中学', '广州市铁一中学', '广东华侨中学',
    '广州协和学校', '清华附中湾区学校',
]

def is_city(s):
    # 仅接受本部名（恰等）或带括号的正式校区；排除"越秀学校/南沙天元"等成员校
    for pfx in CITY_PREFIX:
        if s == pfx:
            return True
        if s.startswith(pfx) and s[len(pfx):].startswith('（'):
            return True
    return False

rows = json.load(open(ALL, encoding='utf-8'))
kept = [r for r in rows if is_city(r['senior'])]
print('省市属高中记录:', len(kept), '/', len(rows))

by_school = defaultdict(list)
for r in kept:
    by_school[r['senior']].append(r)

out = {}
empty_total = 0
for senior, recs in by_school.items():
    by_junior = defaultdict(list)
    for r in recs:
        by_junior[r['junior']].append(r)
    out[senior] = {}
    for junior, rr in sorted(by_junior.items()):
        scores = [int(x['min_score']) for x in rr if x['min_score']]
        last_scores = [int(x['last_score']) for x in rr if x['last_score']]
        admitted = len(scores) > 0
        if not admitted:
            empty_total += 1
        out[senior][junior] = {
            'admitted': admitted,
            'min_score': min(scores) if scores else None,
            'last_score': min(last_scores) if last_scores else None,
            'rows': len(rr),   # 分数表行数（该对聚合行数，一般为1）
        }

juniors = set()
for senior in out.values():
    juniors.update(senior.keys())
print('覆盖初中数:', len(juniors), '| 未录取对:', empty_total)

meta = {
    'updated': '2026-09-09',
    'scope': '省市属示范11所（含全部校区）',
    'source': '广州市招考办《2026年广州市高中阶段学校招生录取分数（第二批次招生学校）（按初中学校排序）》',
    'source_url': 'https://gzzk.gz.gov.cn/attachment/8/8050/8050473/10908461.pdf',
    'note': 'min_score/last_score=该初中通过名额分配实际录取到该校的最低分（未录取为null，指有指标但无人完成录取）；指标计划数 n_ji 需与名额分配计划表合并',
    'data': out,
}
json.dump(meta, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('已写入', OUT)
for k, v in out.items():
    n_adm = sum(1 for x in v.values() if x['admitted'])
    print(f'  {k}: {len(v)} 所初中 / 录取 {n_adm} 对')
