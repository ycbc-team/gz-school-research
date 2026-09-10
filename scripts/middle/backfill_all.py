#!/usr/bin/env python3
"""批量补录：官方名额分配初中名单 × POI 库 交叉校验，未收录者按校名高德直查补点。
只补 7 个中心城区（与现有采集口径一致），远郊四区跳过。"""
import json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEY=[l.split('=',1)[1].strip() for l in open(os.path.join(ROOT,'.env')) if l.startswith('AMAP_WEB_KEY=')][0]
SEVEN = ['荔湾','越秀','海珠','天河','白云','黄埔','番禺']
FAR = ['花都','从化','增城','南沙']

def norm(s):
    s = re.sub(r'^(广州市|广州|广东|广大附中)','',s)
    s = re.sub(r'（[^）]*）','',s); s=re.sub(r'\([^)]*\)','',s)
    s = re.sub(r'(小学部|初中部|高中部|校本部|分校区)$','',s)
    return s.strip()

qm = json.load(open(os.path.join(ROOT,'data/linkage/quota_matrix.json')))['schools']
poi_path = os.path.join(ROOT,'data/middle/schools-gz.json')
poi = json.load(open(poi_path))
existing_norms = {norm(s['name']) for s in poi['schools']}
existing_names = {s['name'] for s in poi['schools']}

def search(name):
    p={'keywords':name,'key':KEY,'offset':'8'}
    u='https://restapi.amap.com/v3/place/text?'+urllib.parse.urlencode(p)
    return json.load(urllib.request.urlopen(u,timeout=20)).get('pois') or []

# 待补：7区、norm后未命中、名字非脏数据
todo=[]
for s in qm:
    nm = s['school']
    if any(f in nm for f in FAR): continue
    on = norm(nm)
    if len(on)<2: continue
    if on in existing_norms:
        continue
    todo.append(nm)

print(f"待补 {len(todo)} 所")
added, failed = [], []
for i, nm in enumerate(todo):
    hits = search(nm); time.sleep(0.25)
    pick = None
    for h in hits:
        if norm(h['name']) == norm(nm) or norm(nm) in norm(h['name']) or norm(h['name']) in norm(nm):
            pick=h; break
    if not pick and hits: pick=hits[0]
    if not pick:
        failed.append(nm); continue
    loc=pick['location'].split(',')
    if len(loc)!=2: failed.append(nm); continue
    if pick['name'] in existing_names: continue
    poi['schools'].append({'name':pick['name'],'lng':float(loc[0]),'lat':float(loc[1]),'adcode':'440100'})
    existing_names.add(pick['name']); added.append(pick['name'])
    if (i+1)%20==0: print(f"  进度 {i+1}/{len(todo)}")

json.dump(poi,open(poi_path,'w'),ensure_ascii=False,indent=2)
print(f"\n新增 {len(added)}，失败 {len(failed)}，总 POI {len(poi['schools'])}")
print("失败:", failed[:30])
