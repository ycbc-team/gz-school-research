# -*- coding: utf-8 -*-
"""v3: 合并 RapidOCR + Vision OCR，重建名额分配表（表头列并集 + 双源数字）"""
import json, glob, re
from collections import Counter

RAPID_DIR = 'data/linkage/raw/ocr_pages'
VIS_DIR = 'data/linkage/raw/vision_pages'
OUT = 'data/linkage/raw/quota_parsed_raw.json'

COL_MAP = [
    (re.compile(r'华附石牌|华附石碑|华附石'), '华南师范大学附属中学（石牌校区）'),
    (re.compile(r'华附知识'), '华南师范大学附属中学（知识城校区）'),
    (re.compile(r'省实荔湾'), '广东实验中学（荔湾校区）'),
    (re.compile(r'省实白云'), '广东实验中学（白云校区）'),
    (re.compile(r'广雅荔湾'), '广东广雅中学（荔湾校区）'),
    (re.compile(r'广雅花都'), '广东广雅中学（花都校区）'),
    (re.compile(r'执信越秀|执信路'), '广州市执信中学（执信路校区）'),
    (re.compile(r'执信天河'), '广州市执信中学（天河校区）'),
    (re.compile(r'二中'), '广州市第二中学'),
    (re.compile(r'六中海珠'), '广州市第六中学（海珠校区）'),
    (re.compile(r'六中从化'), '广州市第六中学（从化校区）'),
    (re.compile(r'六中花'), '广州市第六中学（花都校区）'),
    (re.compile(r'侨中'), '广东华侨中学'),
    (re.compile(r'协和'), '广州协和学校'),
    (re.compile(r'铁一越秀'), '广州市铁一中学（越秀校区）'),
    (re.compile(r'铁一番禺'), '广州市铁一中学（番禺校区）'),
    (re.compile(r'铁一白云'), '广州市铁一中学（白云校区）'),
    (re.compile(r'清湾智谷'), '清华附中湾区学校（智谷校区）'),
    (re.compile(r'清湾智慧'), '清华附中湾区学校（智慧城校区）'),
    (re.compile(r'广州外国语'), '广州外国语学校'),
]

def map_col(t):
    for pat, name in COL_MAP:
        if pat.search(t):
            return name
    return None

def is_school_name(t):
    return bool(re.search(r'(中学|学校|实验|附属|外语|书院|体校|职校|高中|初中|华侨|培正|育才|协和|广雅|执信|省实|华附|六中|铁一|二中|外国语|教育)', t)) and len(t) > 4

DISTRICT_RE = re.compile(r'(荔湾区|越秀区|海珠区|天河区|白云区|黄埔区|番禺区|南沙区|花都区|从化区|增城区)')

def cluster_cols(items, ymax):
    """表头区按 x 聚类成列，返回 [{x, name}]"""
    head = [it for it in items if it['y0'] < ymax]
    head.sort(key=lambda i: i['x0'])
    cols = []
    for it in head:
        placed = False
        for c in cols:
            if abs(it['x0'] - c['x']) < 52:
                c['x'] = (c['x'] + (it['x0']+it['x1'])/2) / 2
                c['items'].append(it)
                placed = True
                break
        if not placed:
            cols.append({'x': (it['x0']+it['x1'])/2, 'items': [it]})
    out = []
    for c in sorted(cols, key=lambda c: c['x']):
        c['items'].sort(key=lambda i: i['y0'])
        name = ''.join(i['text'] for i in c['items'])
        std = map_col(name)
        if std:
            out.append({'x': c['x'], 'std': std, 'raw': name})
    return out

rows_all = []
current_district = None

for pf in sorted(glob.glob(f'{VIS_DIR}/page_*.json')):
    pageno = pf.split('_')[1].split('.')[0]
    rp = f'{RAPID_DIR}/page_{pageno}.json'
    vision = json.load(open(pf, encoding='utf-8'))
    rapid = json.load(open(rp, encoding='utf-8')) if __import__('os').path.exists(rp) else []
    rapid = [it for it in rapid if it['conf'] >= 0.3]
    vision = [it for it in vision if it['conf'] >= 0.3]
    # --- 列定义：双源并集（按 x 去重） ---
    col_candidates = cluster_cols(rapid, 460) + cluster_cols(vision, 460)
    col_defs = {}
    for c in col_candidates:
        key = c['std']
        if key not in col_defs:
            col_defs[key] = c
        # 同列取更靠数据区的（x 参考）
    col_list = sorted(col_defs.values(), key=lambda c: c['x'])
    # --- 数据 items 合并 ---
    all_items = vision + rapid
    all_items = [it for it in all_items if it['y0'] >= 460]
    lines = []
    for it in sorted(all_items, key=lambda i: (i['y0'], i['x0'])):
        placed = False
        for ln in lines:
            if abs(ln['y'] - it['y0']) < 36:
                ln['items'].append(it)
                ln['y'] = (ln['y'] + it['y0']) / 2
                placed = True
                break
        if not placed:
            lines.append({'y': it['y0'], 'items': [it]})
    for ln in sorted(lines, key=lambda l: l['y']):
        its = sorted(ln['items'], key=lambda i: i['x0'])
        text = ''.join(i['text'] for i in its).replace(' ', '')
        m_dist = None
        for i in its:
            t = i['text'].strip()
            if DISTRICT_RE.fullmatch(t):
                m_dist = t
                break
        if m_dist:
            current_district = m_dist
            continue
        if '注:' in text or ('第' in text and '页' in text) or '名额分配结果' in text or '考' in text and len(text) < 3:
            continue
        school = None
        for i in its:
            if 280 <= i['x0'] <= 840 and is_school_name(i['text']):
                school = i['text']
                break
        if not school:
            continue
        rec = {'district': current_district, 'junior': school, 'quota': {}}
        for cd in col_list:
            best = None; best_d = 999
            for i in its:
                d = abs((i['x0']+i['x1'])/2 - cd['x'])
                if d < best_d:
                    best_d = d; best = i
            if best and best_d < 70:
                t = best['text'].strip()
                if re.fullmatch(r'\d+', t):
                    rec['quota'][cd['std']] = int(t)
                elif best_d < 45:
                    rec.setdefault('_unparsed', []).append((cd['raw'], t))
        rows_all.append(rec)

json.dump(rows_all, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('总行数:', len(rows_all))
print('区分布:', dict(Counter(r['district'] for r in rows_all)))
print('未解析行数:', sum(1 for r in rows_all if r.get('_unparsed')))
