#!/usr/bin/env python3
"""构建未入教育集团的多校区法人索引（运行时纯 school_id 查询）。

这是实体注册表派生的校区规模数据，不是官方教育集团名录：
同一物理区 + legalKey 相同 + 至少两个 distinct school_id，且所有校区均未进入
education_groups.json，才会输出。名称推导只发生在构建期，运行时不做名称匹配。
"""
import argparse
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(ROOT, "data", "registry", "entity", "scripts"))
from school_match import legalKey  # noqa: E402

ENTITIES = os.path.join(ROOT, "data", "registry", "entity", "dist", "entities.json")
EDUCATION_GROUPS = os.path.join(ROOT, "data", "registry", "group", "dist", "education_groups.json")
DEFAULT_OUT = os.path.join(ROOT, "data", "registry", "group", "dist", "non_group_multi_campuses.json")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build():
    entities = load(ENTITIES)["entities"]
    grouped_ids = {
        member["school_id"]
        for group in load(EDUCATION_GROUPS)["groups"]
        for member in group.get("members") or []
        if member.get("school_id")
    }
    buckets = defaultdict(dict)
    for entity in entities:
        school_id = entity["school_id"]
        adcode = school_id.split("-")[1]
        bucket = buckets[(adcode, legalKey(entity["name"]))]
        item = bucket.setdefault(school_id, {"school_id": school_id, "names": [], "stages": []})
        if entity["name"] not in item["names"]:
            item["names"].append(entity["name"])
        if entity["stage"] not in item["stages"]:
            item["stages"].append(entity["stage"])

    families = {}
    for (adcode, key), by_id in sorted(buckets.items()):
        members = [by_id[sid] for sid in sorted(by_id)]
        if len(members) < 2 or any(member["school_id"] in grouped_ids for member in members):
            continue
        family_key = f"{adcode}:{key}"
        # 运行时只需家族键和实体外键；名称、学段、推导细节留在实体表/测试快照。
        families[family_key] = [member["school_id"] for member in members]
    return families


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=DEFAULT_OUT)
    args = parser.parse_args()
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(build(), f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[产物] {args.output}")


if __name__ == "__main__":
    main()
