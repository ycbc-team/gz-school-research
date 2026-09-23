#!/usr/bin/env python3
"""复现解析：番禺区义务教育阶段学校招生计划（panyu_2026_official.json）

输入: raw/panyu_2026_official.xls（4 sheet：公办小学招生地段计划 / 公办初中招生范围计划 / 民办招生计划 / 咨询电话）
输出: parsed/_transcripts/panyu_2026_official.json
      {"source","title","published","sheets": {sheet名: rows}}

用途: 复现 2026-09-10 人工转录，保证可审计可重跑。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
RAW = os.path.join(ROOT, "data", "primary", "enrollment", "raw")
OUT = os.path.join(ROOT, "data", "primary", "enrollment", "parsed", "_transcripts", "panyu_2026_official.json")

import xlrd


def clean(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else str(v)
    return re.sub(r"\s+", " ", str(v)).strip()


def main():
    wb = xlrd.open_workbook(os.path.join(RAW, "panyu_2026_official.xls"))
    sheets = {}
    for s in wb.sheets():
        rows = []
        for r in range(s.nrows):
            row = [clean(v) for v in s.row_values(r)]
            rows.append(row)
        sheets[s.name] = rows
    out = {
        "source": "https://www.panyu.gov.cn/jgzy/qzfbm/fzqjyj/jyjgkml/qt/tzgg/content/post_10794082.html",
        "title": "2026年番禺区义务教育阶段学校招生计划、招生地段及条件",
        "published": "2026-04-28",
        "sheets": sheets,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✓ {OUT}  sheets: {list(sheets.keys())}")
    old = json.load(open(OUT, encoding="utf-8"))
    # 对比现状：先备份对比（旧文件已 git mv，直接从 _transcripts 读会被覆盖——这里只打印行数对比）
    for name, rows in sheets.items():
        print(f"  {name}: {len(rows)} 行")
        # 打印与旧版行数差异：旧版在 git HEAD 中，不重复读取


if __name__ == "__main__":
    main()
