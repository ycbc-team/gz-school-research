"""重建 quota_matrix.json 三列(名额考生/省市/区属)
数据源：31 页官方 PDF 逐页整页目视 OCR（quota_vision_values.P），
覆盖此前逐格 Vision / 整行 OCR 的 6↔9 混淆、缺行、校名错位等问题。
本脚本只替换 schools 列表（kaosheng/sheng_quota/qu_quota + 校名修正 + 补缺行），
sz 明细与 school_id 尽量沿用旧矩阵；新增行按注册表已有 id 或按规则生成。
"""
import json, hashlib, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota_vision_values as VV  # P: {page: {row: [kao, ss, qu]}}, P16_INSERT

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OLD = os.path.join(ROOT, 'data/linkage/quota_matrix.json')
GRID = os.path.join(ROOT, 'data/linkage/raw/quota_grid_final.json')
SN = os.path.join(ROOT, 'data/linkage/raw/schoolnames.json')
OUT = OLD

DIST_CODE = {'荔湾区':'440103','越秀区':'440104','海珠区':'440105','天河区':'440106',
             '白云区':'440111','黄埔区':'440112','番禺区':'440113','花都区':'440114',
             '南沙区':'440115','从化区':'440117','增城区':'440118'}
PAGE_DIST = {0:'荔湾区',1:'荔湾区',2:'越秀区',3:'越秀区',4:'海珠区',5:'海珠区',6:'天河区',7:'天河区',8:'天河区',
 9:'白云区',10:'白云区',11:'白云区',12:'白云区',13:'黄埔区',14:'黄埔区',15:'黄埔区',16:'番禺区',17:'番禺区',
 18:'番禺区',19:'番禺区',20:'花都区',21:'花都区',22:'花都区',23:'南沙区',24:'南沙区',25:'从化区',26:'从化区',
 27:'增城区',28:'增城区',29:'增城区',30:'增城区'}
HEADER_PAGES = {0,2,4,6,9,13,16,20,23,25,27}  # 区头所在页

# 官方区头
HDR = {'荔湾区':(6417,332,2053),'越秀区':(10225,543,2686),'海珠区':(8326,431,2036),
       '天河区':(10774,555,2673),'白云区':(13441,696,2272),'黄埔区':(10744,560,1984),
       '番禺区':(16024,838,4474),'花都区':(11223,599,2448),'南沙区':(7017,362,1419),
       '从化区':(6717,355,1486),'增城区':(14831,806,2250)}

# 校名修正（页行 -> 正确名）
NAME_FIX = {
    (0,6): '广州市第四中学丰宁学校',
    (0,7): '广州市西关培英中学',
    (18,10): '广州市铁一中学（番禺校区）',
    (19,16): '广州市番禺区北正华学校',
    (28,18): '广州市斐思学校',
    (20,6): '广州市花都区新雅街清埔初级中学',
}

def names_for(pno):
    g = json.load(open(SN, encoding='utf-8'))
    ns = g.get(str(pno), [])
    if len(ns) >= 2 and ns[0] == '' and ns[1].endswith('区'):
        ns = ns[1:]
    return ns

def sid_for(name, dist, existing):
    if name in existing:
        return existing[name]
    code = DIST_CODE[dist]
    h = hashlib.md5(name.encode('utf-8')).hexdigest()[:8]
    return f'gz-{code}-{h}'

def main():
    old = json.load(open(OLD, encoding='utf-8'))
    grid = json.load(open(GRID, encoding='utf-8'))
    # 旧矩阵 (page,row) -> rec
    old_by = {}
    for s in old['schools']:
        old_by[(s['page'], s['row'])] = s
    # 注册表已有 school_id（按校名）
    existing_sid = {}
    try:
        reg = json.load(open(os.path.join(ROOT, 'data/registry/entities.json'), encoding='utf-8'))
        for e in reg:
            nm = e.get('name') or ''
            if nm and e.get('school_id'):
                existing_sid[nm] = e['school_id']
    except Exception:
        pass
    try:
        sg = json.load(open(os.path.join(ROOT, 'data/middle/schools-gz.json'), encoding='utf-8'))
        items = sg if isinstance(sg, list) else sg.get('schools', [])
        for e in items:
            nm = e.get('name') or e.get('school') or ''
            if nm and (e.get('school_id') or e.get('id')):
                existing_sid[nm] = e.get('school_id') or e.get('id')
    except Exception:
        pass

    schools = []
    districts = []
    for pno in sorted(PAGE_DIST):
        dist = PAGE_DIST[pno]
        if pno in HEADER_PAGES and dist not in districts:
            districts.append(dist)
        g = grid[str(pno)]
        nrows = len(g['rows']) // 2
        if nrows == 0:
            continue
        names = names_for(pno)
        # 每页行计划: (grid_row 或 None=插入, 插入名, 插入值)
        plan = []
        if pno == 16:
            for r in range(1, 9):
                plan.append((r, None, None))
            for _, nm, val in VV.P16_INSERT:
                if nm.startswith('广东第二师范学院广州南站'):
                    plan.append((None, nm, val))
            for r in range(9, 18):
                plan.append((r, None, None))
            for _, nm, val in VV.P16_INSERT:
                if nm.startswith('广东第二师范学院番禺附属'):
                    plan.append((None, nm, val))
        else:
            r0 = 1 if pno in HEADER_PAGES else 0
            for r in range(r0, nrows):
                plan.append((r, None, None))
        for item in plan:
            r, ins_name, ins_val = item
            if r is None:
                name = ins_name
                kao, ss, qu = ins_val
                rec = {'page': pno, 'row': None, 'school': name,
                       'kaosheng': kao, 'sheng_quota': ss, 'qu_quota': qu,
                       'sz': {}, 'sz_sum': 0, 'is_district_head': False,
                       'district': dist}
            else:
                name = NAME_FIX.get((pno, r)) or (names[r] if r < len(names) else '')
                if not name:
                    print(f'!! p{pno} r{r} 无校名，跳过'); continue
                val = VV.P.get(pno, {}).get(r)
                if val is None:
                    print(f'!! p{pno} r{r} {name} 无目视值，跳过'); continue
                rec = {'page': pno, 'row': r, 'school': name,
                       'kaosheng': val[0], 'sheng_quota': val[1], 'qu_quota': val[2]}
                o = old_by.get((pno, r))
                if o:
                    rec['sz'] = o.get('sz', {})
                    rec['sz_sum'] = o.get('sz_sum', 0)
                    if o.get('school_id'):
                        rec['school_id'] = o['school_id']
                else:
                    rec['sz'] = {}
                    rec['sz_sum'] = 0
                rec['is_district_head'] = False
                rec['district'] = dist
            if 'school_id' not in rec:
                rec['school_id'] = sid_for(rec['school'], dist, existing_sid)
            schools.append(rec)

    # 校验区级合计
    agg = {}
    for s in schools:
        d = agg.setdefault(s['district'], [0, 0, 0])
        d[0] += s['kaosheng'] or 0
        d[1] += s['sheng_quota'] or 0
        d[2] += s['qu_quota'] or 0
    ok_all = True
    for d, t in HDR.items():
        a = agg.get(d, [0, 0, 0])
        ok = tuple(a) == t
        ok_all = ok_all and ok
        mark = '✓' if ok else '✗'
        print(f'{d}: 考生{a[0]}/{t[0]} 省市{a[1]}/{t[1]} 区属{a[2]}/{t[2]} {mark}')
    print(f'总学校 {len(schools)}，区级合计{"全部对齐" if ok_all else "存在残差"}')

    out = dict(old)
    out['schools'] = schools
    out['districts'] = districts
    out['updated'] = '2026-09-15'
    out['note'] = (old.get('note', '') + ' 2026-09-15 重建：31页整页目视复核三列（考生/省市/区属），修正6↔9混淆、补回缺行'
                   '（番禺二师南站附属/二师番禺附中、荔湾四中丰宁/海龙博雅、花都清埔初级），修复荔湾西关培英校名错位。')
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print('保存', OUT)

if __name__ == '__main__':
    main()
