"""构建省市属名额分配矩阵：quota_grid3 → quota_matrix.json + 数学校验"""
import json, re

G = 'data/linkage/raw/quota_grid3.json'
OUT = 'data/linkage/raw/quota_matrix.json'

SZ_NAMES = ['华附石牌','华附知识城','省实荔湾','省实白云','广雅荔湾','广雅花都',
            '执信越秀','执信天河','二中','六中海珠','六中从化','六中花都','侨中',
            '协和','广附','铁一越秀','铁一番禺','铁一白云','广州外国语','清湾智谷','清湾智慧城']

def clean(s):
    if not s: return None
    # 去噪：只保留数字与常见误读字母
    s2 = re.sub(r'[^\dOSIl]', '', s)
    s2 = s2.replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1')
    if not s2: return None
    return s2

def to_int(s):
    if s is None: return None
    try: return int(s)
    except: return None

g = json.load(open(G))
pages_out = {}
all_issues = []
for pno, pg in g.items():
    nrows = len(pg['rows']) // 2
    if not pg['data']:
        pages_out[pno] = {'note': 'no_table'}
        continue
    rows_out = []
    for r in range(nrows):
        # col0 名额考生, col1 省市属名额, col2 区属名额
        kaosheng = to_int(clean(pg['data'].get('0', {}).get(str(r), '')))
        sheng = to_int(clean(pg['data'].get('1', {}).get(str(r), '')))
        qu = to_int(clean(pg['data'].get('2', {}).get(str(r), '')))
        # 省市属 21 列 col3-23
        sz = {}
        for i, nm in enumerate(SZ_NAMES):
            raw = pg['data'].get(str(i+3), {}).get(str(r), '')
            sz[nm] = to_int(clean(raw))
        sz_sum = sum(v for v in sz.values() if v is not None)
        # 校验：省市属名额 = Σ 21 列
        if sheng is not None and sz_sum is not None and sheng != sz_sum:
            # 有些列漏读：标记
            all_issues.append((int(pno), r, '省市属', sheng, sz_sum))
        rows_out.append({'kaosheng': kaosheng, 'sheng_quota': sheng, 'qu_quota': qu,
                         'sz': sz})
    pages_out[pno] = {'nrows': nrows, 'rows': rows_out}
json.dump({'pages': pages_out, 'issues': all_issues}, open(OUT, 'w'), ensure_ascii=False)
print(f'总问题 {len(all_issues)} 条')
for iss in all_issues[:15]:
    print(' ', iss)
