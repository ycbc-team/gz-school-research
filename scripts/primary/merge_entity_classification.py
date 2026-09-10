#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 entity_classification.json 的法人分类字段合并到 tier1_schools_all.json。
仅新增字段，不删改现有字段。
用法：python3 scripts/primary/merge_entity_classification.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NEW_FIELDS = ["entity_relation", "tier1_eligible", "legal_entity",
              "exclude_reason", "evidence", "opened_year"]


def merge(src_json: Path, cls_json: Path, out_json: Path) -> None:
    data = json.loads(src_json.read_text(encoding="utf-8"))
    cls = json.loads(cls_json.read_text(encoding="utf-8"))
    cls_map = {s["name"]: s for s in cls["schools"]}

    total = 0
    for dist, meta in data["districts"].items():
        for s in meta["schools"]:
            name = s["name"]
            if name not in cls_map:
                print(f"  [WARN] not found in classification: {name}")
                continue
            c = cls_map[name]
            for field in NEW_FIELDS:
                s[field] = c[field]
            total += 1

    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"merged {total} schools -> {out_json}")


def main() -> None:
    # 小学
    merge(
        ROOT / "data" / "primary" / "tier1_schools_all.json",
        ROOT / "data" / "primary" / "entity_classification.json",
        ROOT / "data" / "primary" / "tier1_schools_all.json",
    )
    # 初中
    merge(
        ROOT / "data" / "middle" / "tier1_schools_all.json",
        ROOT / "data" / "middle" / "entity_classification.json",
        ROOT / "data" / "middle" / "tier1_schools_all.json",
    )


if __name__ == "__main__":
    main()
