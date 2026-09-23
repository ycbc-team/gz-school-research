#!/usr/bin/env python3
"""编译全国文明校园运行时索引：parsed 原文摘录 → 仅含 school_id 的 dist JSON。

官方名称明确校区/部别时，SchoolMatcher(strategy="all") 只返回该校区；未明确校区时，
SchoolMatcher 按法人关系展开所有可命中的校区。dist 刻意不携带校名、届次、来源或推断学段，
这些证据均留在 parsed。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BUSINESS = Path(__file__).resolve().parents[1]
ROOT = BUSINESS.parents[1]
PARSED = BUSINESS / "parsed" / "national_civilized_campuses.json"
BLACKLIST = BUSINESS / "src" / "national_civilized_campuses_blacklist.json"
DIST = BUSINESS / "dist" / "national_civilized_campus_school_ids.json"

sys.path.insert(0, str(ROOT / "data" / "registry" / "entity" / "scripts"))
from school_match import SchoolMatcher  # noqa: E402


def resolve_records() -> tuple[list[str], list[dict[str, object]]]:
    """返回运行时 ID 与供人工审阅的逐项匹配结果。

    不在此处预设城市范围：parsed 是官方原文转录，是否属于项目学校、是否需清洗名称，
    应由审阅输出决定，而不是由一份人工范围表反向筛选。
    """
    document = json.loads(PARSED.read_text(encoding="utf-8"))
    blacklist = json.loads(BLACKLIST.read_text(encoding="utf-8"))
    exact_names = set(blacklist["exact_names"])
    name_prefixes = tuple(blacklist["name_prefixes"])
    matcher = SchoolMatcher.load()
    school_ids: set[str] = set()
    review: list[dict[str, object]] = []

    for record in document["records"]:
        school = record["school"]
        if school in exact_names or school.startswith(name_prefixes):
            continue
        # 不传学段或行政区：名称有校区时精确命中该校区；无校区时由 matcher 展开同法人全部校区。
        hits = matcher.resolve(school, preferred_adcode=None, preferred_stage=None, strategy="all") or []
        # 一个官方名可展开至多个校区；按匹配到的实体名分行，避免把不同校区伪装成同一个实体。
        entities: dict[str, set[str]] = {}
        for hit in hits:
            entity_name = hit.get("matched_name")
            school_id = hit.get("school_id")
            if isinstance(entity_name, str) and isinstance(school_id, str):
                entities.setdefault(entity_name, set()).add(school_id)
                school_ids.add(school_id)
        if not entities:
            review.append({"src_name": school, "entity_name": None, "schoolid": []})
        else:
            for entity_name, ids in sorted(entities.items()):
                review.append({"src_name": school, "entity_name": entity_name, "schoolid": sorted(ids)})
    return sorted(school_ids), review


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只验证 parsed 可解析和匹配逻辑，不写 dist")
    parser.add_argument("--review", action="store_true", help="输出逐项原文名与实体匹配结果 JSON，不写 dist")
    parser.add_argument("--review-output", type=Path, help="将逐项审阅 JSON 写入指定文件，不写 dist")
    options = parser.parse_args()

    school_ids, review = resolve_records()
    if not school_ids:
        raise ValueError("没有解析出任何 school_id，拒绝生成空运行时索引")
    if options.review or options.review_output:
        if options.review_output:
            options.review_output.parent.mkdir(parents=True, exist_ok=True)
            options.review_output.write_text(
                json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            output_path = options.review_output.resolve()
            try:
                output_label = output_path.relative_to(ROOT)
            except ValueError:
                output_label = output_path
            print(f"[civilized] wrote review: {output_label}")
            return
        print(json.dumps(review, ensure_ascii=False, indent=2))
        return
    if options.check:
        unmatched = sum(1 for item in review if not item["schoolid"])
        print(f"[civilized] ok: {len(document_records())} 条正式原文，黑名单排除 {excluded_record_count()} 条 → "
              f"{len(school_ids)} 个 school_id；未匹配 {unmatched} 条")
        return

    DIST.parent.mkdir(exist_ok=True)
    DIST.write_text(json.dumps(school_ids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[civilized] wrote {DIST.relative_to(ROOT)}: {len(document_records())} 条正式原文，"
          f"黑名单排除 {excluded_record_count()} 条 → {len(school_ids)} 个 school_id")


def document_records() -> list[dict[str, object]]:
    return json.loads(PARSED.read_text(encoding="utf-8"))["records"]


def blacklist_names() -> tuple[set[str], tuple[str, ...]]:
    blacklist = json.loads(BLACKLIST.read_text(encoding="utf-8"))
    return set(blacklist["exact_names"]), tuple(blacklist["name_prefixes"])


def excluded_record_count() -> int:
    exact_names, name_prefixes = blacklist_names()
    return sum(
        record["school"] in exact_names or record["school"].startswith(name_prefixes)
        for record in document_records()
    )


if __name__ == "__main__":
    main()
