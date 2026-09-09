#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 legacy/_generated 下 tier1.js 产物中的匹配别名/手工坐标回写进 tier1_schools_all.json。

背景：aliases（点位匹配别名）与 EXTRA_COORDS（手工坐标）原先只存在于生成的 tier1.js 产物中，
JSON 真源不完整。本脚本将这些字段回填到 JSON 真源（按学校名匹配，幂等，可重复运行），
此后 build_tier1_js.py / build_middle_tier1_js.py 优先使用 JSON 中已有的 aliases/coords。

用法: python3 scripts/sync_tier1_aliases.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STAGES = [
    {
        "stage": "primary",
        "json_path": ROOT / "data" / "primary" / "tier1_schools_all.json",
        "js_path": ROOT / "apps" / "web" / "legacy" / "_generated" / "primary" / "tier1.js",
        "var": "GZ_TIER1",
    },
    {
        "stage": "middle",
        "json_path": ROOT / "data" / "middle" / "tier1_schools_all.json",
        "js_path": ROOT / "apps" / "web" / "legacy" / "_generated" / "middle" / "tier1.js",
        "var": "GZ_MIDDLE_TIER1",
    },
]

ALIAS_FIELDS = ("aliases", "coords", "coord_addr", "coord_source")


def main() -> None:
    for cfg in STAGES:
        js = cfg["js_path"].read_text(encoding="utf-8")
        m = re.search(rf"window\.{cfg['var']}\s*=\s*(\{{.*?\}});?\s*$", js, re.S)
        if not m:
            raise SystemExit(f"无法解析 {cfg['js_path']} 中的 {cfg['var']}")
        prod = {s["name"]: s for s in json.loads(m.group(1))["schools"]}

        data = json.loads(cfg["json_path"].read_text(encoding="utf-8"))
        updated = 0
        skipped = 0
        for dist, meta in data["districts"].items():
            for s in meta["schools"]:
                p = prod.get(s["name"])
                if not p:
                    continue
                if "aliases" in s:
                    skipped += 1
                    continue
                for f in ALIAS_FIELDS:
                    if f in p:
                        s[f] = p[f]
                updated += 1
        cfg["json_path"].write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{cfg['stage']}: 回填 {updated} 所（已存在跳过 {skipped}） -> {cfg['json_path']}")


if __name__ == "__main__":
    main()
