# -*- coding: utf-8 -*-
"""解析第二批次录取分数 PDF（初中×高中 上岸分数）→ parsed JSON（支持多年度）。

用法：
  python3 parse_batch2.py            # 2026（默认，向后兼容：raw/batch2_scores.pdf → parsed/batch2_scores_all.json）
  python3 parse_batch2.py --year 2025 # raw/batch2_scores_2025.pdf → parsed/batch2_scores_2025.json
  python3 parse_batch2.py --year 2024 # raw/batch2_scores_2024.pdf → parsed/batch2_scores_2024.json

官方源均为「按初中学校排序」的第二批次录取分数表（送生学校/招生学校/最低分数/
最低分数同分序号/末位考生分数/末位考生志愿序号/末位考生分数同分序号）。
2026 沿用历史产物名 batch2_scores_all.json，2024/2025 带年份后缀。
"""
import argparse
import json
import re
import pdfplumber

# 年份 → (raw PDF, parsed OUT)；2026 保持历史命名
YEAR_MAP = {
    '2026': ('data/linkage/raw/batch2_scores.pdf', 'data/linkage/parsed/batch2_scores_all.json'),
    '2025': ('data/linkage/raw/batch2_scores_2025.pdf', 'data/linkage/parsed/batch2_scores_2025.json'),
    '2024': ('data/linkage/raw/batch2_scores_2024.pdf', 'data/linkage/parsed/batch2_scores_2024.json'),
}


def norm(s):
    return re.sub(r'\s+', '', (s or '')).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', choices=sorted(YEAR_MAP), default='2026')
    args = ap.parse_args()
    raw, out = YEAR_MAP[args.year]

    rows = []
    with pdfplumber.open(raw) as pdf:
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

    json.dump(rows, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'[{args.year}] 总行数: {len(rows)} → {out}')
    # 招生学校唯一值
    seniors = {}
    for r in rows:
        seniors.setdefault(r['senior'], 0)
        seniors[r['senior']] += 1
    print(f'[{args.year}] 招生学校种类: {len(seniors)}')
    for k, v in sorted(seniors.items(), key=lambda x: -x[1])[:40]:
        print(f'  {k}  {v}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
