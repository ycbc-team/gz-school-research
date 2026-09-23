#!/usr/bin/env python3
"""复现解析：荔湾公办初中电脑派位分组（liwan_2026_groups.json）

输入: raw/liwan_2026_a3.docx（《2026年荔湾区公办初中一年级招生工作方案》附件3：2026年荔湾区小学毕业生电脑派位分组）
输出: parsed/_transcripts/liwan_2026_groups.json
      [{"table": <表序号>, "cells": [[列1段落...], [列2段落...], [列3段落...]]}, ...]
      按行解析：docx 表格每行一条，cells 为每列单元格按换行拆分后的段落数组。

用途: 复现 2026-09-10 人工转录，保证可审计可重跑。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
RAW = os.path.join(ROOT, "data", "enrollment", "raw")
OUT = os.path.join(ROOT, "data", "middle", "enrollment", "parsed", "_transcripts", "liwan_2026_groups.json")

from docx import Document


def clean(v):
    return re.sub(r"\s+", " ", v).strip()


def split_cell(text):
    """单元格按换行拆段，去空段。"""
    return [s.strip() for s in re.split(r"[\n\r]+", text) if s.strip()]


def main():
    doc = Document(os.path.join(RAW, "liwan_2026_a3.docx"))
    out = []
    for ti, table in enumerate(doc.tables):
        for row in table.rows:
            cells = [split_cell(c.text) for c in row.cells]
            if not any(cells):
                continue
            out.append({"table": ti, "cells": cells})
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✓ {OUT}  {len(out)} 行")
    old = json.load(open(OUT, encoding="utf-8"))
    # 与 git 旧版对比（先读旧内容再覆盖的问题：这里直接读 git show 由外部做）
    print("条数:", len(old))


if __name__ == "__main__":
    main()
