#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建升学通道矩阵：初中 × 省市属高中（体育/艺术/自招考核资格）
- 输入：data/linkage/raw/special/sports_2026.json、arts_2026.json
       data/linkage/raw/autonomy/autonomy_qualify_2026.json
- 输出：data/linkage/special_matrix.json
口径：省市属 11 所（21 校区），含校区匹配；体育/艺术用"招生学校（项目）"前缀匹配；
自招用"自主招生综合能力考核名单"标题匹配。自招为考核资格名单口径（非预录取）。
"""
import json, re, collections

BASE = 'data/linkage/raw'
OUT = 'data/linkage/special_matrix.json'

# 省市属 11 所 → 校区关键词（来自 levels.json / 名额分配表头）
CITY_SCHOOLS = [
    ('华南师范大学附属中学', ['石牌', '知识城']),
    ('广东实验中学', ['荔湾', '白云']),
    ('广东广雅中学', ['荔湾', '花都']),
    ('广州市执信中学', ['执信路', '天河']),
    ('广州市第二中学', ['应元']),
    ('广州市第六中学', ['海珠', '从化', '花都']),
    ('广州大学附属中学', ['黄华路']),
    ('广州市铁一中学', ['越秀', '番禺', '白云']),
    ('广东华侨中学', ['起义路']),
    ('广州市协和中学', []),
    ('清华附中湾区学校', ['智谷', '智慧城']),
]

def match_high(name):
    """把名单里的招生高中名/标题匹配到省市属校区；返回 (高中, 校区) 或 None
    规则：有校区/成员校的学校（华附/省实/广雅/执信/六中/铁一）必须带校区关键词，
    否则成员校（如省实越秀、二中南沙天元、广附南沙实验）会被误配；仅名称恰为学校名
    本身时视为本部。无校区歧义的学校（二中/广附/侨/协和/清湾）直接匹配。
    """
    multi_camp = ['华南师范大学附属中学', '广东实验中学', '广东广雅中学',
                  '广州市执信中学', '广州市第六中学', '广州市铁一中学',
                  '清华附中湾区学校']
    for school, camps in CITY_SCHOOLS:
        if school not in name:
            continue
        # 名称恰为学校名 → 本部
        rest = name[len(school):]
        if not rest:
            return (school, school)
        if school in multi_camp:
            for c in camps:
                if c in name:
                    return (school, school + '（' + c + '）')
            # 有校区/成员校但未匹配到校区关键词 → 排除（成员校）
            return None
        return (school, school)
    return None

def agg_project(rows, key, junior_key='school'):
    """按初中→高中计数"""
    mat = collections.Counter()
    for r in rows:
        hs = match_high(r[key])
        if not hs:
            continue
        mat[(r[junior_key], hs[1])] += 1
    return mat

sports = json.load(open(f'{BASE}/special/sports_2026.json'))
arts = json.load(open(f'{BASE}/special/arts_2026.json'))
auto = json.load(open(f'{BASE}/autonomy/autonomy_qualify_2026.json'))

m_sports = agg_project(sports, 'project')
m_arts = agg_project(arts, 'project')
m_auto = agg_project(auto, 'school_high', junior_key='school_junior')

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

out = {
    'updated': '2026-09-09',
    'scope': '省市属 11 所（21 校区），体育/艺术特长生通过测试名单 + 自招综合能力考核资格名单',
    'note': '体育/艺术=通过专业测试名单（官方发布）；自招=综合能力考核资格名单口径（考核前≤5倍计划，非预录取）。',
    'high_schools': sorted(all_hs),
    'matrix': {j: dict(hs) for j, hs in matrix.items()},
}
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('高中校区数:', len(all_hs))
print('初中学数:', len(matrix))
print('省市属匹配到的记录: 体育', sum(m_sports.values()), '艺术', sum(m_arts.values()), '自招', sum(m_auto.values()))
print('样例:', list(matrix.items())[0])
