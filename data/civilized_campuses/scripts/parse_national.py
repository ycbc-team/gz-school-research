#!/usr/bin/env python3
"""从中国文明网全国文明校园正式名单页提取广东省原文名单。

此脚本有意只产出来源可直接证明的字段：届次、认定年份、原文学校名、原文省份、原文顺序和
来源 URL。市区、学段、school_id、是否属于广州等均留待后续按实体表核验，不在本阶段猜测。
"""

from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "parsed" / "national_civilized_campuses.json"

SOURCES = (
    {
        "term": 1,
        "year": 2017,
        "file": "national_civilized_campuses_1_2021.html",
        "url": "https://www.wenming.cn/wmsjk/cjdx_53740/qgwmxymd/202112/t20211227_6276854.shtml",
        "expected_guangdong_records": 30,
    },
    {
        "term": 2,
        "year": 2020,
        "file": "national_civilized_campuses_2_2021.html",
        "url": "https://www.wenming.cn/wmsjk/cjdx_53740/qgwmxymd/202112/t20211227_6276858.shtml",
        "expected_guangdong_records": 37,
    },
    {
        "term": 3,
        "year": 2025,
        "file": "national_civilized_campuses_3_2025.html",
        "url": "https://www.wenming.cn/wmzthc/20250522/49dda5aa663948a9830ba2e7b9890e0b/c.html",
        "expected_guangdong_records": 48,
    },
)


class ParagraphText(HTMLParser):
    """仅收集 p 标签文本；足以覆盖三个官方名单页，避免引入解析依赖。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._parts: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "p":
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._depth:
            self._depth -= 1
            if self._depth == 0:
                value = "".join(self._parts).replace("\xa0", " ").strip()
                if value:
                    self.paragraphs.append(value)
                self._parts = []

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._parts.append(data)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", html.unescape(text))


def split_entries(text: str) -> list[str]:
    """按顿号拆学校名，但保留括号内的校区/部别枚举。"""
    entries: list[str] = []
    buffer: list[str] = []
    depth = 0
    for char in text:
        if char in "（(":
            depth += 1
        elif char in "）)" and depth:
            depth -= 1
        if char == "、" and depth == 0:
            value = "".join(buffer).strip()
            if value:
                entries.append(value)
            buffer = []
        else:
            buffer.append(char)
    value = "".join(buffer).strip()
    if value:
        entries.append(value)
    return entries


def find_guangdong_list(page: Path) -> list[str]:
    parser = ParagraphText()
    parser.feed(page.read_text(encoding="utf-8"))
    for paragraph in parser.paragraphs:
        text = normalize(paragraph)
        match = re.search(r"广东省：[\s]*(.+?)[；;]?$", text)
        if match:
            return split_entries(match.group(1))
    raise ValueError(f"未在 {page.name} 找到广东省名单段")


def build() -> dict[str, object]:
    records: list[dict[str, object]] = []
    sources: list[dict[str, object]] = []
    for source in SOURCES:
        page = RAW / str(source["file"])
        schools = find_guangdong_list(page)
        expected = source["expected_guangdong_records"]
        if len(schools) != expected:
            raise ValueError(
                f"{page.name} 提取到 {len(schools)} 所，预期 {expected} 所；请先检查页面结构或名单。"
            )
        sources.append(
            {
                "term": source["term"],
                "year": source["year"],
                "file": source["file"],
                "url": source["url"],
                "province": "广东省",
                "record_count": len(schools),
            }
        )
        for position, school in enumerate(schools, start=1):
            records.append(
                {
                    "school": school,
                    "term": source["term"],
                    "year": source["year"],
                    "province": "广东省",
                    "source_position": position,
                    "source_url": source["url"],
                }
            )
    return {
        "dataset": "全国文明校园（广东省名单原文摘录）",
        "status": "draft_raw_extraction",
        "note": "仅含全国正式名单中广东省段的原文学校名；未推断市区、学段、实体或现行有效状态。",
        "sources": sources,
        "records": records,
    }


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--check", action="store_true", help="只执行解析及数量断言，不写文件")
    options = args.parse_args()
    payload = build()
    if options.check:
        print(f"ok: {len(payload['records'])} records from {len(SOURCES)} official national lists")
        return
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT.parent.parent)}: {len(payload['records'])} records")


if __name__ == "__main__":
    main()
