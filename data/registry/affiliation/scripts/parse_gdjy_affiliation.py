#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广东省教育厅部门预算下属单位清单解析器：PDF → parsed JSON（省属口径）。

来源：https://edu.gd.gov.cn/attachment/0/573/573199/4670841.pdf
  《2025年广东省教育厅部门预算》第三部分「部门预算构成」：下属单位具体包括 1–64 号。

转录原则：忠实原文（单位名称、序号原样），分类（category）为转录时按名称
特征推断，非原文字段，见 README 口径说明。省属学校 = 其中「省属中小学 3 所」
+「省属中职/专门学校 6 所」；在穗省属高中校区口径另见招考办名额分配表
（data/linkage/，不在此重复转录）。

用法：
  python3 data/registry/affiliation/scripts/parse_gdjy_affiliation.py [--out-dir <dir>]
依赖：系统 pdftotext（macOS/Linux 常见，或 poppler-utils）。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/registry/affiliation/raw/gdjy_2025年部门预算_下属单位.pdf"
OUT = ROOT / "data/registry/affiliation/parsed/gdjy_2025年部门预算_下属单位.json"

SOURCE_URL = "https://edu.gd.gov.cn/attachment/0/573/573199/4670841.pdf"
TITLE = "2025年广东省教育厅部门预算——下属单位清单"
PUBLISH_DATE = "2025-01"
EXPECTED_TOTAL = 64

# 分类规则：按名称特征归类（转录推断，非原文字段）
CATE_OFFICE = ("广东省教育厅（本级）", "广东省教育考试院", "广东省教育研究院",
               "广东省教育装备中心", "广东省教育厅事务中心（省电化教育馆）")
CATE_ADULT = ("广东开放大学（广东理工职业学院）", "广东社会科学大学")


def categorize(name: str) -> str:
    if name in CATE_OFFICE or name.endswith("事务中心"):
        return "厅属事业单位"
    if name.endswith("中学") or name.endswith("小学"):
        return "省属中小学"
    if ("职业技术学校" in name or name.endswith("附属中等音乐学校")
            or name.endswith("附属中等美术学校") or name.endswith("潜水学校")):
        return "省属中职/专门学校"
    if name in CATE_ADULT:
        return "成人高校"
    if ("职业技术学院" in name or name.endswith("职业学院")
            or name.endswith("职业技术大学")):
        return "省属高职院校"
    return "省属本科高校"


def extract_units(text: str):
    """从“下属单位具体包括：”到“第二部分”之间提取 序号.单位名称 列表。"""
    m = re.search(r"下属单位具体包括：(.*?)第二部分\s*2025年部门预算表", text, re.S)
    if not m:
        raise ValueError("PDF 文本中未定位到下属单位清单段落")
    seg = m.group(1)
    seg = re.sub(r"-\d+-", "", seg)  # 去页码
    units = []
    for item in re.findall(r"(\d+)\s*[\.．、]\s*([^\d\n][^\n]*)", seg):
        seq = int(item[0])
        name = item[1].strip().rstrip("；;。 ")
        name = re.sub(r"\s+", "", name)
        if name:
            units.append((seq, name))
    return units


def build(text: str) -> dict:
    units = extract_units(text)
    seqs = [u[0] for u in units]
    if seqs != list(range(1, EXPECTED_TOTAL + 1)):
        raise ValueError(
            f"单位序号不连续/缺漏：期望 1–{EXPECTED_TOTAL}，实得 {seqs[0]}–{seqs[-1]} 共 {len(seqs)}")
    records = [{"seq": s, "name": n, "category": categorize(n)} for s, n in units]
    counts = {}
    for r in records:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    return {
        "title": TITLE,
        "source_url": SOURCE_URL,
        "publish_date": PUBLISH_DATE,
        "scraped_date": "2026-09-30",
        "total": len(records),
        "category_counts": counts,
        "units": records,
        "note": "category 为转录时按名称特征推断，非原文字段；省属学校口径见 README。",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="输出目录（默认 parsed/，供重放/漂移检查用）")
    args = ap.parse_args()
    out = (args.out_dir or OUT).resolve()

    pdf = subprocess.run(
        ["pdftotext", "-layout", str(RAW), "-"],
        capture_output=True, text=True, check=True,
    )
    data = build(pdf.stdout)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"转录完成：{out}")
    print(f"下属单位总数：{data['total']}（序号 1–{data['total']} 连续）")
    for c, n in data["category_counts"].items():
        print(f"  {c}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
