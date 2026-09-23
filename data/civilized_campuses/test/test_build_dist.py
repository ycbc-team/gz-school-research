#!/usr/bin/env python3
"""全国文明校园 dist 的一致性测试，并输出供人工审阅的逐项匹配。"""

import json
import subprocess
import sys
from pathlib import Path


BUSINESS = Path(__file__).resolve().parents[1]
ROOT = BUSINESS.parents[1]
BUILD = BUSINESS / "scripts" / "build_dist.py"
DIST = BUSINESS / "dist" / "national_civilized_campus_school_ids.json"
REVIEW = BUSINESS / "test" / "national_civilized_campus_match_review.json"
BLACKLIST = BUSINESS / "src" / "national_civilized_campuses_blacklist.json"


def main() -> None:
    result = subprocess.run([sys.executable, str(BUILD), "--check"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(result.stdout + result.stderr)
    school_ids = json.loads(DIST.read_text(encoding="utf-8"))
    assert isinstance(school_ids, list) and school_ids, "dist 必须是非空 school_id 列表"
    assert school_ids == sorted(set(school_ids)), "dist school_id 必须去重且排序"
    assert all(isinstance(school_id, str) and school_id.startswith("gz-") for school_id in school_ids), "dist 不得含非广州 school_id"
    review_result = subprocess.run(
        [sys.executable, str(BUILD), "--review-output", str(REVIEW)], cwd=ROOT, text=True, capture_output=True
    )
    if review_result.returncode:
        raise SystemExit(review_result.stdout + review_result.stderr)
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    assert isinstance(review, list) and review, "审阅输出必须是非空列表"
    assert all(set(item) == {"src_name", "entity_name", "schoolid"} for item in review), "审阅字段不符合约定"
    assert all(isinstance(item["src_name"], str) for item in review), "src_name 必须保留官方原文名"
    assert all(item["entity_name"] is None or isinstance(item["entity_name"], str) for item in review), "entity_name 类型错误"
    assert all(isinstance(item["schoolid"], list) for item in review), "schoolid 必须为列表"
    blacklist = json.loads(BLACKLIST.read_text(encoding="utf-8"))
    exact_names = set(blacklist["exact_names"])
    name_prefixes = tuple(blacklist["name_prefixes"])
    assert all(
        item["src_name"] not in exact_names and not item["src_name"].startswith(name_prefixes)
        for item in review
    ), "黑名单学校不得出现在审阅产物或 dist 候选中"
    print(f"[civilized test] ok: {len(school_ids)} school_id; review: {REVIEW.relative_to(ROOT)} ({len(review)} rows)")


if __name__ == "__main__":
    main()
