#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""特色校认定聚合编译：parsed/*.json → dist/specialty_schools.json（运行时产物）。

规则（与 data/awards 一致）：
  - 学校名统一走项目 SchoolMatcher（scripts/registry/school_match.py）
  - 名单带区属 → preferred_adcode 收窄（school_id adcode 与官方区属一致）
  - 特色校名单不分学段 → 不传 preferred_stage，全学段匹配，多校区/多学段 school_id 全挂
  - 非学校（少年宫/青少年宫等）在 parsed 阶段已排除
输出：按学校聚合该学校全部特色认定（recognitions），school_id 供运行时挂学校画像。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # gz_school_research
SPECIALTY = Path(__file__).resolve().parent.parent
ENTITIES = ROOT / "data/registry/entities.json"

sys.path.insert(0, str(ROOT / "scripts" / "registry"))
from school_match import SchoolMatcher

DISTRICT_ADCODE = {"荔湾": "440103", "越秀": "440104", "海珠": "440105", "天河": "440106",
                   "白云": "440111", "黄埔": "440112", "番禺": "440113", "花都": "440114",
                   "南沙": "440115", "从化": "440117", "增城": "440118"}


def main():
    matcher = SchoolMatcher.load(
        poi_paths=[
            (ROOT / "data/poi/dist/primary_poi.json", "小学"),
            (ROOT / "data/poi/dist/middle_poi.json", "初中"),
            (ROOT / "data/poi/dist/high_poi.json", "高中"),
        ],
        entities_path=ENTITIES,
    )

    schools = {}   # school 名 → {school_ids, match_type, recognitions: []}
    unmatched = []
    total = 0
    for p in sorted((SPECIALTY / "parsed").glob("*.json")):
        doc = json.loads(p.read_text("utf-8"))
        for rec in doc.get("records", []):
            total += 1
            school = rec["school"]
            adcode = DISTRICT_ADCODE.get(rec.get("district", "").replace("区", ""))
            hits = matcher.resolve(school, preferred_adcode=adcode, preferred_stage=None, strategy="all") or []
            sids = sorted({h.get("school_id") for h in hits if h.get("school_id")})
            entry = schools.setdefault(school, {"school": school, "school_ids": [], "recognitions": []})
            if sids:
                entry["school_ids"] = sorted(set(entry["school_ids"]) | set(sids))
            entry["match_type"] = "single" if len(entry["school_ids"]) == 1 else (
                "multi" if len(entry["school_ids"]) > 1 else "none")
            entry["recognitions"].append({
                "category": rec.get("category", ""),
                "level": rec.get("level", ""),
                "batch": rec.get("batch", ""),
                "year": int(rec.get("year")) if str(rec.get("year", "")).isdigit() else rec.get("year", ""),
                "project": rec.get("project", ""),
                "issuer": rec.get("issuer", ""),
                "url": rec.get("url", ""),
                "remark": rec.get("remark", ""),
            })
            if not sids:
                unmatched.append({"school": school, "district": rec.get("district", ""), "category": rec.get("category", "")})

    out = {
        "updated": "2026-09-20",
        "metric": "specialty_schools",
        "summary": {
            "total_records": total,
            "total_schools": len(schools),
            "matched_schools": sum(1 for s in schools.values() if s["school_ids"]),
            "unmatched_schools": len(unmatched),
        },
        "schools": list(schools.values()),
        "unmatched": unmatched,
    }
    dist_dir = SPECIALTY / "dist"
    dist_dir.mkdir(exist_ok=True)
    (dist_dir / "specialty_schools.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[specialty] 记录 {total} 条 → 学校 {len(schools)} 所，匹配 {out['summary']['matched_schools']} 所，"
          f"未匹配 {len(unmatched)} 所")
    for u in unmatched:
        print(f"  [unmatched] {u['school']} ({u['district']} / {u['category']})")


if __name__ == "__main__":
    main()
