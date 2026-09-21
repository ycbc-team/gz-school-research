#!/usr/bin/env python3
"""复现解析：白云公办初中招生计划（baiyun_2026_juniors.json）

输入: raw/baiyun_2026_official.xlsx（附表2：公办初中含小区配套学校）
输出: parsed/_transcripts/baiyun_2026_juniors.json
      [{"seq","pian","jiedao","school","kind","feed","plan","note"}, ...]

用途: 复现 2026-09-10 人工转录，替代无过程 OCR/手工录入，保证可审计可重跑。
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
RAW = os.path.join(ROOT, "data", "primary", "transition", "raw")
OUT = os.path.join(ROOT, "data", "primary", "transition", "parsed", "_transcripts", "baiyun_2026_juniors.json")

import openpyxl


def clean(v):
    """压缩空格/制表，保留换行（对口小学多校区说明按行分隔）。"""
    if v is None:
        return ""
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else str(v)
    return re.sub(r"[ \t]+", " ", str(v)).strip()


def clean_nl(v):
    """去除全部空白（学校名等单行字段，合并跨行单元格）。"""
    if v is None:
        return ""
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else str(v)
    return re.sub(r"\s+", "", str(v))


def main():
    wb = openpyxl.load_workbook(os.path.join(RAW, "baiyun_2026_official.xlsx"), data_only=True)
    ws = wb["公办初中"]
    rows = list(ws.iter_rows(values_only=True))
    # 找表头行
    header_i = None
    for i, r in enumerate(rows):
        if r and r[0] == "序号":
            header_i = i
            break
    if header_i is None:
        raise SystemExit("未找到 公办初中 表头")
    # 表头: 序号 片 街（镇） 学校名称 学校类别 招生对口小学 咨询电话 2026计划招生班数 特殊情况说明
    out = []
    for r in rows[header_i + 1:]:
        if not r or not clean(r[0]):
            continue
        rec = {
            "seq": clean_nl(r[0]),
            "pian": clean_nl(r[1]),
            "jiedao": clean_nl(r[2]),
            "school": clean_nl(r[3]),
            "kind": clean_nl(r[4]),
            "feed": clean(r[5]),
            "plan": clean_nl(r[7]) if len(r) > 7 else "",
            "note": clean(r[8]) if len(r) > 8 else "",
        }
        out.append(rec)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✓ {OUT}  {len(out)} 条")
    # 与现状对比
    cur = os.path.join(ROOT, "data", "primary", "transition", "parsed", "_transcripts", "baiyun_2026_juniors.json")
    j = json.load(open(cur, encoding="utf-8"))
    print(f"现状 {len(j)} 条，新生成 {len(out)} 条")
    if len(j) != len(out):
        print("条数不一致！")
    for a, b in zip(j, out):
        for k in ("seq", "pian", "jiedao", "school", "kind", "feed", "plan", "note"):
            if clean(a.get(k)) != b[k]:
                print(f"  DIFF {k}: 现={a.get(k)!r} 新={b[k]!r}")
                break


if __name__ == "__main__":
    main()
