"""组装最终名额分配矩阵：quota_grid5b + schoolnames → quota_matrix.json"""
import json, re

G = 'data/linkage/raw/quota_grid_final.json'
SN = 'data/linkage/raw/schoolnames.json'
OUT = 'data/linkage/quota_matrix.json'

SZ_NAMES = ['华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都',
            '执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中',
            '协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城']

def clean(s):
    if not s: return None
    s2 = re.sub(r'[^\dOSIl]', '', str(s)).replace('O','0').replace('o','0').replace('I','1').replace('l','1')
    try: return int(s2) if s2 else None
    except: return None

g = json.load(open(G))
sn = json.load(open(SN))

# 组装
schools = []  # 每校一条
for pno in sorted(g, key=int):
    pg = g[pno]
    nrows = len(pg['rows']) // 2
    if not pg['data'] or nrows == 0: continue
    names = sn.get(pno, [])
    for r in range(nrows):
        name = names[r] if r < len(names) else ''
        if not name: continue
        rec = {
            'page': int(pno), 'row': r, 'school': name,
            'kaosheng': clean(pg['data'].get('0', {}).get(str(r), '')),
            'sheng_quota': clean(pg['data'].get('1', {}).get(str(r), '')),
            'qu_quota': clean(pg['data'].get('2', {}).get(str(r), '')),
        }
        sz = {}
        for i, nm in enumerate(SZ_NAMES):
            sz[nm] = clean(pg['data'].get(str(i+3), {}).get(str(r), ''))
        rec['sz'] = sz
        rec['sz_sum'] = sum(v for v in sz.values() if v is not None)
        schools.append(rec)

# 区归属：区名结尾的行（不论行号）都是区头，不入学校列表
districts = []
schools2 = []
for s in schools:
    nm = s['school']
    if re.match(r'^.{2,4}[区]$', nm):
        s['is_district_head'] = True
        districts.append(s)
    else:
        s['is_district_head'] = False
        schools2.append(s)
schools = schools2

# 给学校补区归属：用区头行的页码边界
bounds = sorted((d['page'], d['school']) for d in districts)
cur = None
for s in schools:
    while bounds and bounds[0][0] <= s['page']:
        cur = bounds.pop(0)[1]
    s['district'] = cur

# 校验（仅数据行）
bad = [s for s in schools if s['sheng_quota'] is not None and s['sz_sum'] != s['sheng_quota']]
print(f'总学校 {len(schools)}，省市属校验不一致 {len(bad)}')
for b in bad[:10]:
    print(f"  {b['page']}页{b['row']}行 {b['school']}: 名额={b['sheng_quota']} Σ={b['sz_sum']}")

print('\n区:', [d['school'] for d in districts])
# 保存
json.dump({'schools': schools, 'districts': [d['school'] for d in districts]},
          open(OUT, 'w'), ensure_ascii=False, indent=1)
print('保存', OUT)
