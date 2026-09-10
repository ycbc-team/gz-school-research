# -*- coding: utf-8 -*-
"""解析 2026 第二批次录取分数 PDF（初中×高中 上岸分数）→ raw JSON"""
import json, re, sys
import pdfplumber

RAW = 'data/linkage/raw/batch2_scores.pdf'
OUT = 'data/linkage/raw/batch2_scores_all.json'

def norm(s):
    return re.sub(r'\s+', '', (s or '')).strip()

rows = []
with pdfplumber.open(RAW) as pdf:
    for page in pdf.pages:
        for t in page.extract_tables() or []:
            for r in t:
                if not r or not r[0]:
                    continue
                if '送生学校' in norm(r[0]):
                    continue  # 表头
                if len(r) < 7:
                    continue
                rows.append({
                    'junior': norm(r[0]),
                    'senior': norm(r[1]),
                    'min_score': norm(r[2]),
                    'min_seq': norm(r[3]),
                    'last_score': norm(r[4]),
                    'last_vol_seq': norm(r[5]),
                    'last_seq': norm(r[6]),
                })

json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('总行数:', len(rows))
# 招生学校唯一值
seniors = {}
for r in rows:
    seniors.setdefault(r['senior'], 0)
    seniors[r['senior']] += 1
print('招生学校种类:', len(seniors))
for k, v in sorted(seniors.items(), key=lambda x: -x[1])[:40]:
    print(f'  {k}  {v}')
