#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jyj 官网《广州市教育局直属事业单位列表》解析器：raw HTML → parsed JSON。

来源：https://jyj.gz.gov.cn/gk/zfxxgkml/zzjg/jgzn/content/post_10116380.html
  - 发布时间 2025-02-14 17:26:02，统计时间 2024-12-31，共 32 个单位
  - 字段：序号 / 单位名称 / 单位地址 / 联系电话

转录原则：忠实原文，不加工。地址中多个校区（<br> 分隔）保留为多行；
电话中的多个号码/分号原样保留。序号校验连续 1–32，缺失即失败。

用法：
  python3 data/registry/affiliation/scripts/parse_jyj_affiliation.py [--out-dir <dir>]
"""
import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data/registry/affiliation/raw/jyj_直属事业单位列表_2025-02-14.html"
OUT = ROOT / "data/registry/affiliation/parsed/jyj_直属事业单位列表_2025-02-14.json"

SOURCE_URL = "https://jyj.gz.gov.cn/gk/zfxxgkml/zzjg/jgzn/content/post_10116380.html"
TITLE = "广州市教育局直属事业单位列表"
PUBLISH_DATE = "2025-02-14"
STATS_DATE = "2024-12-31"
EXPECTED_COUNT = 32


def cell_text(td: str) -> str:
    """单元格 HTML → 纯文本。保留 <br> 为换行（多校区地址/多行内容），
    排版空白（&nbsp;/全角空格）压缩为单个空格并去行首尾空白。"""
    text = re.sub(r"<br\s*/?>", "\n", td, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    lines = [re.sub(r"[ \t\u3000\xa0]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(lines).strip()


def parse_rows(raw_html: str):
    """提取表格数据行（序号列为纯数字的行）。"""
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", raw_html, re.S):
        tds = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        cells = [cell_text(td) for td in tds]
        if cells and cells[0].isdigit():
            rows.append(cells)
    return rows


def build(raw_html: str) -> dict:
    rows = parse_rows(raw_html)
    if len(rows) != EXPECTED_COUNT:
        raise ValueError(f"数据行数 {len(rows)} ≠ 期望 {EXPECTED_COUNT}")
    units = []
    for i, r in enumerate(rows, start=1):
        seq = int(r[0])
        if seq != i:
            raise ValueError(f"序号不连续：第 {i} 行序号为 {seq}")
        if len(r) < 4:
            raise ValueError(f"第 {seq} 行字段不足：{r}")
        units.append({"seq": seq, "name": r[1], "address": r[2], "phone": r[3]})
    return {
        "title": TITLE,
        "source_url": SOURCE_URL,
        "publish_date": PUBLISH_DATE,
        "stats_date": STATS_DATE,
        "scraped_date": "2026-09-30",
        "unit_count": len(units),
        "units": units,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="输出目录（默认 parsed/，供重放/漂移检查用）")
    args = ap.parse_args()
    out = (args.out_dir or OUT).resolve()

    raw_html = RAW.read_text(encoding="utf-8")
    data = build(raw_html)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"转录完成：{out}")
    print(f"单位数：{data['unit_count']}（序号 1–{data['unit_count']} 连续）")
    print("单位名单：")
    for u in data["units"]:
        print(f"  {u['seq']:>2} {u['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
