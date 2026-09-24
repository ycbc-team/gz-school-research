#!/usr/bin/env python3
"""广州文明校园两类已完整公开名单：raw → parsed。"""
import html
import json
import re
from pathlib import Path

BUSINESS = Path(__file__).resolve().parents[1]
RAW = BUSINESS / "raw"
OUT = BUSINESS / "parsed" / "guangzhou_civilized_campuses.json"
SOURCES = (
    ("guangzhou_civilized_campuses_2_2021.html", "第二届广州市文明校园", "市级正式", 49,
     "https://m.sohu.com/a/463529378_120152148"),
    ("guangzhou_civilized_campuses_advanced_2021_2023.html", "2021—2023年创建广州市文明校园先进学校", "创建储备", 63,
     "https://gdgz.wenming.cn/2020index/xxgg/202201/t20220121_7478272.html"),
)

def paragraphs(path):
    text = path.read_text(encoding="utf-8")
    return [re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", value))).strip()
            for value in re.findall(r"<p[^>]*>(.*?)</p>", text, re.S | re.I)]

def extract(values, title, count):
    start = next(i for i, value in enumerate(values) if title in value)
    names = []
    for value in values[start + 1:]:
        if value and not value.startswith("（") and not value.startswith("广州市精神文明") and not value.startswith("责任编辑"):
            names.append(value)
        if len(names) == count:
            break
    assert len(names) == count, (title, len(names), names[-3:])
    return names

def main():
    records = []
    for filename, award, level, count, url in SOURCES:
        names = extract(paragraphs(RAW / filename), award + "名单", count)
        records.extend({"school": name, "award": award, "level": level, "source_url": url} for name in names)
    OUT.write_text(json.dumps({"dataset": "广州市文明校园名单原文摘录", "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[civilized] wrote {OUT.relative_to(BUSINESS.parents[1])}: {len(records)} records")

if __name__ == "__main__": main()
