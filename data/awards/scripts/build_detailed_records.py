#!/usr/bin/env python3
"""汇总已解析的白名单竞赛明细，供 Web 获奖详情页使用。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/awards/detailed_records.json"
INNOVATION = ROOT / "data/awards/innovation/parsed"
CHUANGKE = ROOT / "data/awards/chuangke/parsed/chuangke.json"


def main():
    details = []
    for path in sorted(INNOVATION.glob("innovation_*.json")):
        match = re.fullmatch(r"innovation_(primary|middle|high)_(\d{4})\.json", path.name)
        if not match:
            continue
        stage, year = match.groups()
        for record in json.loads(path.read_text("utf-8")).get("records", []):
            if not record.get("school_ids"):
                continue
            details.append({
                "competition": "innovation", "stage": stage, "year": int(year),
                "school": record["school"], "project": record.get("project", ""),
                "leader": record.get("leader", ""), "members": record.get("members", ""),
                "coach": record.get("coach", ""), "award": record.get("award", ""),
                "school_ids": record["school_ids"],
            })

    for year_group in json.loads(CHUANGKE.read_text("utf-8")).get("records", []):
        for record in year_group.get("records", []):
            if not record.get("school_ids"):
                continue
            details.append({
                "competition": "chuangke", "stage": record["stage"], "year": int(year_group["year"]),
                "school": record["school"], "project": record.get("project", "团体赛"),
                "leader": record.get("student", "") if record.get("type") == "personal" else "",
                "members": record.get("student", "") if record.get("type") == "team" else "",
                "coach": record.get("coach", ""), "award": record.get("award", ""),
                "school_ids": record["school_ids"],
            })

    OUT.write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"[detailed-records] {len(details)} 条")


if __name__ == "__main__":
    main()
