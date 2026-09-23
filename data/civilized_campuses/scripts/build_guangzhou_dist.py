#!/usr/bin/env python3
"""广州 parsed → 两类纯 school_id dist，并输出审阅 JSON。"""
import argparse, json, sys
from pathlib import Path
BUSINESS = Path(__file__).resolve().parents[1]; ROOT = BUSINESS.parents[1]
PARSED = BUSINESS / "parsed" / "guangzhou_civilized_campuses.json"
sys.path.insert(0, str(ROOT / "data" / "registry" / "entity" / "scripts"))
from school_match import SchoolMatcher

def resolve():
    matcher = SchoolMatcher.load(); rows = json.loads(PARSED.read_text(encoding="utf-8"))["records"]
    result, ids = [], {"市级正式": set(), "创建储备": set()}
    for row in rows:
        hits = matcher.resolve(row["school"], strategy="all") or []
        grouped = {}
        for hit in hits:
            if hit.get("school_id"): grouped.setdefault(hit["matched_name"], set()).add(hit["school_id"])
        if not grouped: result.append({"src_name": row["school"], "entity_name": None, "schoolid": [], "award": row["award"]})
        for name, schoolids in sorted(grouped.items()):
            values = sorted(schoolids); ids[row["level"]].update(values)
            result.append({"src_name": row["school"], "entity_name": name, "schoolid": values, "award": row["award"]})
    return ids, result

def main():
    p=argparse.ArgumentParser(); p.add_argument("--review-output", type=Path); p.add_argument("--check", action="store_true"); a=p.parse_args()
    ids, review=resolve()
    if a.review_output:
        a.review_output.write_text(json.dumps(review,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return
    if a.check: print(f"[civilized] city formal {len(ids['市级正式'])}; advanced {len(ids['创建储备'])}"); return
    (BUSINESS/"dist"/"guangzhou_civilized_campus_school_ids.json").write_text(json.dumps(sorted(ids["市级正式"]),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (BUSINESS/"dist"/"guangzhou_civilized_campus_advanced_school_ids.json").write_text(json.dumps(sorted(ids["创建储备"]),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__ == "__main__": main()
