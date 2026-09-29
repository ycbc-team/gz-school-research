#!/usr/bin/env python3
"""汇总已解析的白名单竞赛明细，供 Web 获奖详情页使用。

字段口径（2026-09-29 体积治理）：
- leader/members 归一为单字段 person（前端只渲染"参赛学生"一行，members 96.5% 为空、仅作
  members||leader 回退；合并后语义不变：person = members 名单，缺失时回退 leader）
- coach 移除（Web 前端两页均未消费该字段，26586 条全量冗余）
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/awards/dist/detailed_records.json"
INNOVATION = ROOT / "data/awards/innovation/parsed"
CHUANGKE = ROOT / "data/awards/chuangke/parsed/chuangke.json"
SCIENCE_LITERACY = ROOT / "data/awards/science_literacy/parsed"
TECH_SPORTS = ROOT / "data/awards/tech_sports/parsed"
SCIENCE_EXPERIMENT = ROOT / "data/awards/science_experiment/parsed"
YUEYUNBEI = ROOT / "data/awards/yueyunbei/parsed"


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
                "person": record.get("members") or record.get("leader") or "",
                "award": record.get("award", ""),
                "school_ids": record["school_ids"],
            })

    for year_group in json.loads(CHUANGKE.read_text("utf-8")).get("records", []):
        for record in year_group.get("records", []):
            if not record.get("school_ids"):
                continue
            details.append({
                "competition": "chuangke", "stage": record["stage"], "year": int(year_group["year"]),
                "school": record["school"], "project": record.get("project", "团体赛"),
                "person": record.get("student", ""),
                "award": record.get("award", ""),
                "school_ids": record["school_ids"],
            })

    for science_path in sorted(SCIENCE_LITERACY.glob("science_literacy_*.json")):
        doc = json.loads(science_path.read_text("utf-8"))
        for record in doc.get("records", []):
            if not record.get("school_ids"):
                continue
            details.append({
                "competition": "science_literacy", "stage": record["stage"],
                "year": int(doc["year"]), "school": record["school"],
                "project": record.get("category", ""), "person": record.get("student", ""),
                "award": record.get("award", ""), "school_ids": record["school_ids"],
            })

    for tech_path in sorted(TECH_SPORTS.glob("tech_sports_*.json")):
        doc = json.loads(tech_path.read_text("utf-8"))
        for record in doc.get("records", []):
            if not record.get("school_ids"):
                continue
            details.append({
                "competition": "tech_sports", "stage": record["stage"],
                "year": int(doc["year"]), "school": record["school"],
                "project": record.get("project", ""),
                "person": record.get("student", ""),
                "award": record.get("award", ""),
                "school_ids": record["school_ids"],
            })

    for science_path in sorted(SCIENCE_EXPERIMENT.glob("science_experiment_*.json")):
        doc = json.loads(science_path.read_text("utf-8"))
        for record in doc.get("records", []):
            if not record.get("school_ids"):
                continue
            details.append({
                "competition": "science_experiment", "stage": record["stage"],
                "year": int(doc["year"]), "school": record["school"],
                "project": record.get("project", ""), "person": record.get("student", ""),
                "award": record.get("award", ""), "school_ids": record["school_ids"],
            })

    for yue_path in sorted(YUEYUNBEI.glob("yueyunbei_*.json")):
        doc = json.loads(yue_path.read_text("utf-8"))
        for record in doc.get("records", []):
            if not record.get("school_ids"):
                continue
            details.append({
                "competition": "yueyunbei", "stage": record["stage"],
                "year": int(doc["year"]), "school": record["school"],
                "project": record.get("project", ""), "person": record.get("student", ""),
                "award": record.get("award", ""), "school_ids": record["school_ids"],
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"[detailed-records] {len(details)} 条")


if __name__ == "__main__":
    main()
