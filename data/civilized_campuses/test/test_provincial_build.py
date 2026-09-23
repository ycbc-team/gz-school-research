#!/usr/bin/env python3
import json, subprocess, sys, tempfile
from pathlib import Path
B=Path(__file__).resolve().parents[1]; R=B.parents[1]; BUILD=B/"scripts"/"build_provincial_dist.py"; SNAP=B/"test"/"provincial_civilized_campuses_match_review.json"
def main():
 assert len(json.loads((B/"parsed"/"provincial_civilized_campuses.json").read_text(encoding="utf-8"))["records"])==61
 with tempfile.TemporaryDirectory() as temp:
  output=Path(temp)/SNAP.name; subprocess.run([sys.executable,str(BUILD),"--review-output",str(output)],cwd=R,check=True)
  assert json.loads(output.read_text(encoding="utf-8"))==json.loads(SNAP.read_text(encoding="utf-8")), "省级文明校园匹配变化：人工确认后更新 test/provincial_civilized_campuses_match_review.json"
 print("[civilized provincial] ok: first term 61 records")
if __name__=="__main__":main()
