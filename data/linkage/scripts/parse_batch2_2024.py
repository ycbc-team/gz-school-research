#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 2024 第二批次录取分数 PDF（按初中排序）→ parsed/batch2_scores_2024.json。

2024 官方 PDF 排版差：单元格内校名跨行（"华南师范大学附属中学（石牌校\\n区）"、
"市\\n广州市第一中学（初中校区）"），页眉"广州市招生考试委员会办公室"残片
（委/考/试/生/招/员/公/办/室/会）混入校名与分数（如"员\\n638"）。
extract_tables 每行 = 一条记录（含 0-5 个数字列，0 数字 = 未录取对），
本脚本做显式清洗：
  1) 校名去 \\n（跨行拼接）；
  2) 校名前导残片删除（市/州/区/广广/委/考/试/生/招/员/公/办/室/会）；
  3) 数字字段去非数字（保留空 = 未录取对）。
输出结构与 2026/2025 完全一致（junior/senior/min_score/min_seq/
last_score/last_vol_seq/last_seq）。
"""
import json
import re
import pdfplumber

RAW = 'data/linkage/raw/batch2_scores_2024.pdf'
OUT = 'data/linkage/parsed/batch2_scores_2024.json'

# 前导残片（跨行/页眉混入），可多次出现；「广」的重复前缀由 clean_name 的
# while 循环逐字删（避免误删「广东X」的广——"广广东"只应删首字成"广东"）
LEAD_JUNK = re.compile(r'^(市|州|区|委|考|试|生|招|员|公|办|室|会)+')
DIGIT_ONLY = re.compile(r'\d+')


def clean_name(n: str) -> str:
    if not n:
        return ''
    n = n.replace('\n', '')          # 跨行拼接
    n = LEAD_JUNK.sub('', n)         # 前导残片
    # 重复前缀字符兜底（如 '广广…' 已覆盖，再防 '广州市' 被拆两字粘连）
    while len(n) >= 3 and n[0] == n[1] and n[0] in '广州市':
        n = n[1:]
    # 跨行粘连的孤立「广」残片（"广北京师范大学…"）：广后非 东南大/州市 才删
    # （保留 广东/广州/广大附中 等正常名）
    if n.startswith('广') and not re.match(r'^广(东南大|州市)', n):
        n = n[1:]
    # 跨行丢「广」前缀（"东仲元…/州协和…/大附中…" 实为 广东/广州/广大附中）
    if n.startswith('州'):
        n = '广' + n
    elif n.startswith('东') and not n.startswith('东莞'):
        n = '广' + n
    elif n.startswith('大附中'):
        n = '广' + n
    return n.strip()


def dig(cell) -> str:
    """单元格取第一个连续数字串；空单元格保留空（= 未录取对）。"""
    if not (cell or '').strip():
        return ''
    m = DIGIT_ONLY.search(cell)
    return m.group(0) if m else ''


def main() -> int:
    rows = []
    with pdfplumber.open(RAW) as pdf:
        for page in pdf.pages:
            for t in page.extract_tables() or []:
                for r in t:
                    if not r or not r[0]:
                        continue
                    if '送生学校' in r[0].replace(' ', ''):
                        continue  # 表头
                    rows.append({
                        'junior': clean_name(r[0]),
                        'senior': clean_name(r[1]),
                        'min_score': dig(r[2]),
                        'min_seq': dig(r[3]),
                        'last_score': dig(r[4]),
                        'last_vol_seq': dig(r[5]),
                        'last_seq': dig(r[6]),
                    })

    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('总行数:', len(rows))
    print('初中种类:', len(set(r['junior'] for r in rows)), '| 高中种类:', len(set(r['senior'] for r in rows)))
    print('空分对:', sum(1 for r in rows if not r.get('min_score')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
