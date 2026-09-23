#!/usr/bin/env python3
import json, subprocess, sys, tempfile
from pathlib import Path
BUSINESS=Path(__file__).resolve().parents[1]; ROOT=BUSINESS.parents[1]
BUILD=BUSINESS/"scripts"/"build_guangzhou_dist.py"; PARSED=BUSINESS/"parsed"/"guangzhou_civilized_campuses.json"
REVIEWS={"formal": BUSINESS/"test"/"guangzhou_civilized_campuses_formal_match_review.json", "advanced": BUSINESS/"test"/"guangzhou_civilized_campuses_advanced_match_review.json"}
def main():
    records=json.loads(PARSED.read_text(encoding="utf-8"))["records"]
    assert sum(x["level"]=="市级正式" for x in records)==49
    assert sum(x["level"]=="创建储备" for x in records)==63
    with tempfile.TemporaryDirectory() as temp:
        generated={key: Path(temp)/value.name for key,value in REVIEWS.items()}
        subprocess.run([sys.executable,str(BUILD),"--formal-review-output",str(generated["formal"]),"--advanced-review-output",str(generated["advanced"])],cwd=ROOT,check=True)
        for key, path in REVIEWS.items(): assert json.loads(generated[key].read_text(encoding="utf-8"))==json.loads(path.read_text(encoding="utf-8")), f"广州{key}文明校园匹配变化：请人工确认后更新快照"
    print("[civilized guangzhou] ok: 49 formal + 63 advanced")
if __name__=="__main__": main()
