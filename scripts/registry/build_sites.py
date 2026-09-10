#!/usr/bin/env python3
"""从 POI 数据自动生成学校身份注册表（site 粒度）。
POI 名带括号的自动按 base 名归组成法人 → 多 site。
手工别名仍可在 sites.json 的 aliases 字段补充。"""
import json, re, sys
from collections import defaultdict

def base_name(n):
    return re.sub(r'（[^）]*）', '', n).replace('（','(').replace('）',')').split('(')[0].strip()

poi = {}
for stage, f in [('high', 'data/high/schools-gz.json'), ('middle', 'data/middle/schools-gz.json')]:
    for s in json.load(open(f))['schools']:
        poi[s['name']] = (stage, s.get('district',''), s['lng'], s['lat'])

groups = defaultdict(list)
for name, (stage, dist, lng, lat) in poi.items():
    if '(' in name or '（' in name:
        groups[(stage, base_name(name))].append(name)

schools = []
for (stage, base), names in sorted(groups.items()):
    if len(names) < 2:
        continue
    sid = re.sub(r'[\s（）()]+', '', base)[:20]
    sites = []
    for nm in sorted(names):
        st, dist, lng, lat = poi[nm]
        sites.append({
            'id': None,  # 下面填
            'poi_name': nm,
            'district': dist,
            'stage': st,
            'aliases': [],
        })
    for i, s in enumerate(sites):
        s['id'] = f"{sid}-{i+1}"
    schools.append({'id': sid, 'name': base, 'stages': [stage], 'sites': sites})

out = {
    'updated': '2026-09-10',
    'purpose': '自动生成：法人→多校区两层。poi_name 即地图点位；aliases 待手工补坊间/政府别名。',
    'schools': schools,
}
json.dump(out, open('data/registry/sites.json','w'), ensure_ascii=False, indent=2)
print(f"生成 {len(schools)} 个法人 / {sum(len(s['sites']) for s in schools)} 个 site")
