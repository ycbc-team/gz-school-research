#!/usr/bin/env python3
import json, subprocess, sys, tempfile
from pathlib import Path
BUSINESS=Path(__file__).resolve().parents[1]; ROOT=BUSINESS.parents[1]
BUILD=BUSINESS/"scripts"/"build_guangzhou_dist.py"; PARSED=BUSINESS/"parsed"/"guangzhou_civilized_campuses.json"
REVIEW=BUSINESS/"test"/"guangzhou_civilized_campuses_match_review.json"
DIST=[BUSINESS/"dist"/"guangzhou_civilized_campus_school_ids.json", BUSINESS/"dist"/"guangzhou_civilized_campus_advanced_school_ids.json"]
def main():
    records=json.loads(PARSED.read_text(encoding="utf-8"))["records"]
    assert sum(x["level"]=="市级正式" for x in records)==49
    assert sum(x["level"]=="创建储备" for x in records)==63
    for path in DIST:
        values=json.loads(path.read_text(encoding="utf-8")); assert values==sorted(set(values)) and all(x.startswith("gz-") for x in values)
    with tempfile.TemporaryDirectory() as temp:
        generated=Path(temp)/REVIEW.name
        subprocess.run([sys.executable,str(BUILD),"--review-output",str(generated)],cwd=ROOT,check=True)
        assert json.loads(generated.read_text(encoding="utf-8"))==json.loads(REVIEW.read_text(encoding="utf-8")), "广州文明校园匹配变化：人工确认后更新 test/guangzhou_civilized_campuses_match_review.json"
    print("[civilized guangzhou] ok: 49 formal + 63 advanced")
if __name__=="__main__": main()
