#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性迁移：把采集期的中间 CSV 迁移为 parsed/ 规范 JSON（唯一真源）。

三个源 CSV 字段完全一致：
    学校名称, 所在区, 类别, 级别, 批次, 认定年份, 认定项目全称, 发文单位, 官方来源URL, 备注

按类别拆分输出（每类一个规范 JSON）：
    parsed/gz_mental_health.json   心理健康教育（市级批次）
    parsed/gz_meiyu_pilot.json     美育/艺术教育（市级试点）
    parsed/science_tech.json       科技创新/科学教育（国家级/省级）
    parsed/gd_science_high.json    省科学特色高中试点（2026 高中多样化特色试点·科学类）
    parsed/sports.json             体育（冰雪体育/足球/传统特色等）

迁移完成后源 CSV 即中间产物，不再保留；后续新数据直接写 parsed/*.json。
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_FILES = ["municipal_mental_arts.csv", "science_tech.csv", "sports.csv"]

# 类别 → 输出文件名（parsed json）
CATEGORY_OUT = {
    "心理健康教育": "gz_mental_health.json",
    "美育/艺术教育": "gz_meiyu_pilot.json",
    "科技创新/科学教育": "science_tech.json",
    "科学高中": "gd_science_high.json",
}
SPORTS_PREFIX = "体育"  # 体育-冰雪体育 / 体育-校园足球 等子类统一进 sports.json

COL = {
    "school": "学校名称", "district": "所在区", "category": "类别", "level": "级别",
    "batch": "批次", "year": "认定年份", "project": "认定项目全称",
    "issuer": "发文单位", "url": "官方来源URL", "remark": "备注",
}


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    groups = defaultdict(list)
    sources = []
    for name in CSV_FILES:
        path = ROOT / name
        if not path.exists():
            print(f"[skip] {name} 不存在")
            continue
        for row in read_csv(path):
            rec = {k: (row.get(v) or "").strip() for k, v in COL.items()}
            if not rec["school"]:
                continue
            cat = rec["category"]
            if cat == SPORTS_PREFIX or cat.startswith(SPORTS_PREFIX + "-"):
                out = "sports.json"
            else:
                out = CATEGORY_OUT.get(cat)
                if not out:
                    print(f"[warn] 未知类别 {cat!r}（{rec['school']}），跳过")
                    continue
            groups[out].append(rec)
            sources.append(name)

    parsed_dir = ROOT / "parsed"
    parsed_dir.mkdir(exist_ok=True)
    for out_name, records in sorted(groups.items()):
        doc = {
            "business": "specialty_schools",
            "category": records[0]["category"] if len({r["category"] for r in records}) == 1 else "多类别",
            "generated_from": "采集期中间CSV（csv_to_parsed.py 迁移）",
            "generated_at": "2026-09-20",
            "record_count": len(records),
            "records": records,
        }
        out_path = parsed_dir / out_name
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ok] {out_name}: {len(records)} 条")

    print(f"\n共迁移 {sum(len(v) for v in groups.values())} 条记录，源 CSV：{sorted(set(sources))}")


if __name__ == "__main__":
    main()
