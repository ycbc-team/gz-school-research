#!/usr/bin/env python3
"""补录交叉校验发现的 10 所缺失初中 POI（九年一贯制/民办/新校，初中 type 搜不到）。
按校名直查高德 place/text，命中后追加到 data/middle/schools-gz.json。"""
import json, os, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def load_key():
    for line in open(os.path.join(ROOT, '.env')):
        if line.startswith('AMAP_WEB_KEY='):
            return line.strip().split('=',1)[1]
    raise SystemExit('no AMAP key')

KEY = load_key()
# (校名, 期望所在区)
TARGETS = [
    ('广州协和学校', '越秀区'),
    ('广州市知用学校', '海珠区'),
    ('广州市为明学校', '白云区'),
    ('广州市源雅学校', '白云区'),
    ('广州市天健学校', '白云区'),
    ('广州市新侨学校', '黄埔区'),
    ('广州市星执学校', '番禺区'),
    ('广州市黄广中学', '花都区'),
    ('广州英豪学校', '从化区'),
    ('广州市香江中学', '增城区'),
]
ADCODE = {'越秀区':'440104','海珠区':'440105','白云区':'440111','黄埔区':'440112','番禺区':'440113','花都区':'440114','从化区':'440117','增城区':'440118'}

def search(name):
    p = {'keywords': name, 'key': KEY, 'types': '141200|141201|141202', 'offset':'10','page':'1'}
    u = 'https://restapi.amap.com/v3/place/text?' + urllib.parse.urlencode(p)
    return json.load(urllib.request.urlopen(u, timeout=20))['pois'] or []

path = os.path.join(ROOT, 'data/middle/schools-gz.json')
data = json.load(open(path))
existing = {s['name'] for s in data['schools']}
added = []
for name, dist in TARGETS:
    hits = search(name)
    time.sleep(0.3)
    pick = None
    for h in hits:
        if name in h['name'] or h['name'] in name:
            pick = h; break
    if not pick and hits:
        pick = hits[0]
    if not pick:
        print(f'  [miss] {name}'); continue
    loc = pick['location'].split(',')
    entry = {'name': pick['name'], 'lng': float(loc[0]), 'lat': float(loc[1]),
             'adcode': ADCODE.get(dist,'440100')}
    if entry['name'] in existing:
        print(f'  [dup] {entry["name"]}'); continue
    data['schools'].append(entry)
    existing.add(entry['name'])
    added.append(entry)
    print(f'  + {entry["name"]} ({dist})')

json.dump(data, open(path,'w'), ensure_ascii=False, indent=2)
print(f'\n新增 {len(added)} 所，总计 {len(data["schools"])}')
