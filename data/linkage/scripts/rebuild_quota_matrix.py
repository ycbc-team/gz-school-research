#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 quota_matrix 规范表（B 层：parsed/canonical/quota_matrix.json）

数据源：
- data/linkage/parsed/quota_grid_final.json   OCR 网格（行结构 + 补行占位）
- data/linkage/parsed/schoolnames.json         OCR 校名（页 → 名字列表）
- data/linkage/src/quota_vision_values.json    名额三列（考生/省市/区属）视觉权威值（人工目视读取）
- data/linkage/src/name_fix.json               校名人工修正（页,行 → 官方原文名）

本脚本只替换 schools 列表（kaosheng/sheng_quota/qu_quota + 校名修正 + 补缺行），
sz 明细沿用旧规范表（canonical 优先，首次从 dist 引导；sz 为历史 OCR 产物，无独立 raw 源）。
school_id 不在本层生成——统一由 C 层 backfill_school_ids.py 的 SchoolMatcher 匹配回填。

输出：data/linkage/parsed/canonical/quota_matrix.json（清洗后规范表，无 school_id/school_ids）
"""
import json
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LINK = os.path.join(ROOT, 'data', 'linkage')
CANON = os.path.join(LINK, 'parsed', 'canonical', 'quota_matrix.json')
OLD_DIST = os.path.join(LINK, 'dist', 'quota_matrix.json')
GRID = os.path.join(LINK, 'parsed', 'quota_grid_final.json')
SN = os.path.join(LINK, 'parsed', 'schoolnames.json')
SRC_VV = os.path.join(LINK, 'src', 'quota_vision_values.json')
SRC_NF = os.path.join(LINK, 'src', 'name_fix.json')
OUT = CANON

DIST_CODE = {'荔湾区': '440103', '越秀区': '440104', '海珠区': '440105', '天河区': '440106',
             '白云区': '440111', '黄埔区': '440112', '番禺区': '440113', '花都区': '440114',
             '南沙区': '440115', '从化区': '440117', '增城区': '440118'}
PAGE_DIST = {0: '荔湾区', 1: '荔湾区', 2: '越秀区', 3: '越秀区', 4: '海珠区', 5: '海珠区', 6: '天河区', 7: '天河区', 8: '天河区',
             9: '白云区', 10: '白云区', 11: '白云区', 12: '白云区', 13: '黄埔区', 14: '黄埔区', 15: '黄埔区', 16: '番禺区', 17: '番禺区',
             18: '番禺区', 19: '番禺区', 20: '花都区', 21: '花都区', 22: '花都区', 23: '南沙区', 24: '南沙区', 25: '从化区', 26: '从化区',
             27: '增城区', 28: '增城区', 29: '增城区', 30: '增城区'}
HEADER_PAGES = {0, 2, 4, 6, 9, 13, 16, 20, 23, 25, 27}  # 区头所在页

# 官方区头（校验锚点：各区考生/省市/区属合计，来自官方 PDF 区头）
HDR = {'荔湾区': (6417, 332, 2053), '越秀区': (10225, 543, 2686), '海珠区': (8326, 431, 2036),
       '天河区': (10774, 555, 2673), '白云区': (13441, 696, 2272), '黄埔区': (10744, 560, 1984),
       '番禺区': (16024, 838, 4474), '花都区': (11223, 599, 2448), '南沙区': (7017, 362, 1419),
       '从化区': (6717, 355, 1486), '增城区': (14831, 806, 2250)}

# OCR 校名规范化：历史 OCR/录入把「第一一五中学」误写为 U+2014 破折号「第—一五中学」等，统一还原为「一」
def normalize_school_name(name: str) -> str:
    return (name or '').replace('\u2014', '一')


def names_for(sn_data, pno):
    ns = sn_data.get(str(pno), [])
    if len(ns) >= 2 and ns[0] == '' and ns[1].endswith('区'):
        ns = ns[1:]
    return ns


def main():
    os.makedirs(os.path.dirname(CANON), exist_ok=True)
    vv = json.load(open(SRC_VV, encoding='utf-8'))
    P = {int(k): {int(r): v for r, v in rows.items()} for k, rows in vv['P'].items()}
    P16_INSERT = [tuple(x) for x in vv['P16_INSERT']]
    name_fix = {(f['page'], f['row']): f['name'] for f in json.load(open(SRC_NF, encoding='utf-8'))['fixes']}

    # 旧规范表（sz 明细继承）：canonical 优先（本层持久层），首次迁移时从 dist 引导
    old_path = CANON if os.path.exists(CANON) else OLD_DIST
    if os.path.exists(old_path):
        old = json.load(open(old_path, encoding='utf-8'))
        print(f'sz 继承源: {old_path}')
    else:
        old = {'schools': [], 'note': ''}
        print('!! 无旧矩阵（canonical/dist 均不存在），sz 明细将为空')
    old_by = {}
    for s in old['schools']:
        old_by[(s['page'], s['row'])] = s

    grid = json.load(open(GRID, encoding='utf-8'))
    sn_data = json.load(open(SN, encoding='utf-8'))

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
        names = names_for(sn_data, pno)
        # 每页行计划: (grid_row 或 None=插入, 插入名, 插入值)
        plan = []
        if pno == 16:
            for r in range(1, 9):
                plan.append((r, None, None))
            for _, nm, val in P16_INSERT:
                if nm.startswith('广东第二师范学院广州南站'):
                    plan.append((None, nm, val))
            for r in range(9, 18):
                plan.append((r, None, None))
            for _, nm, val in P16_INSERT:
                if nm.startswith('广东第二师范学院番禺附属'):
                    plan.append((None, nm, val))
        else:
            r0 = 1 if pno in HEADER_PAGES else 0
            for r in range(r0, nrows):
                plan.append((r, None, None))
        for item in plan:
            r, ins_name, ins_val = item
            if r is None:
                name = normalize_school_name(ins_name)
                kao, ss, qu = ins_val
                rec = {'page': pno, 'row': None, 'school': name,
                       'kaosheng': kao, 'sheng_quota': ss, 'qu_quota': qu,
                       'sz': {}, 'sz_sum': 0, 'is_district_head': False,
                       'district': dist}
            else:
                name = normalize_school_name(name_fix.get((pno, r)) or (names[r] if r < len(names) else ''))
                if not name:
                    print(f'!! p{pno} r{r} 无校名，跳过'); continue
                val = P.get(pno, {}).get(r)
                if val is None:
                    print(f'!! p{pno} r{r} {name} 无目视值，跳过'); continue
                rec = {'page': pno, 'row': r, 'school': name,
                       'kaosheng': val[0], 'sheng_quota': val[1], 'qu_quota': val[2]}
                o = old_by.get((pno, r))
                if o:
                    rec['sz'] = o.get('sz', {})
                    rec['sz_sum'] = o.get('sz_sum', 0)
                else:
                    rec['sz'] = {}
                    rec['sz_sum'] = 0
                rec['is_district_head'] = False
                rec['district'] = dist
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

    # note 幂等：先剥离历史追加段，再一次性写入
    REBUILD_NOTE = (' 2026-09-15 重建：31页整页目视复核三列（考生/省市/区属），修正6↔9混淆、补回缺行'
                    '（番禺二师南站附属/二师番禺附中、荔湾四中丰宁/海龙博雅、花都清埔初级），修复荔湾西关培英校名错位。')
    SZ_GAP_NOTE = ' 二师南站附属/二师番禺附中为本次补行，sz 分额明细暂缺(sz_sum=0)。'
    base = old.get('note', '')
    for seg in (REBUILD_NOTE, SZ_GAP_NOTE):
        base = base.replace(seg, '')
    out = {
        'title': '名额分配计划表规范表（B 层）',
        'updated': '2026-09-15',
        'note': base.rstrip() + REBUILD_NOTE + SZ_GAP_NOTE,
        'source': '广州市招考办《2026年广州市名额分配招生学校招生总计划和名额分配计划汇总表》（官方 PDF）',
        'schools': schools,
        'districts': districts,
    }
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
    print('保存', OUT)


if __name__ == '__main__':
    main()
