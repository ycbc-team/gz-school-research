#!/usr/bin/env python3
"""广州 parsed → 两类匹配审阅；运行时 dist 由 build_dist.py 统一融合。"""
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
    p=argparse.ArgumentParser(); p.add_argument("--formal-review-output", type=Path); p.add_argument("--advanced-review-output", type=Path); p.add_argument("--check", action="store_true"); a=p.parse_args()
    ids, review=resolve()
    for output, level in ((a.formal_review_output,"第二届广州市文明校园"),(a.advanced_review_output,"2021—2023年创建广州市文明校园先进学校")):
        if output:
            output.write_text(json.dumps([x for x in review if x["award"]==level],ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if a.formal_review_output or a.advanced_review_output: return
    if a.check: print(f"[civilized] city formal {len(ids['市级正式'])}; advanced {len(ids['创建储备'])}"); return
    print("请使用 build_dist.py 生成融合运行时产物")
if __name__ == "__main__": main()
