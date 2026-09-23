#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
BUSINESS=Path(__file__).resolve().parents[1]; ROOT=BUSINESS.parents[1]; PARSED=BUSINESS/"parsed"/"provincial_civilized_campuses.json"; BLACKLIST=BUSINESS/"src"/"provincial_civilized_campuses_blacklist.json"
sys.path.insert(0,str(ROOT/"data"/"registry"/"entity"/"scripts")); from school_match import SchoolMatcher
def resolve():
 m=SchoolMatcher.load(); ids=set(); review=[]; blocked=json.loads(BLACKLIST.read_text(encoding="utf-8")); exact=set(blocked["exact_names"]); prefixes=tuple(blocked["name_prefixes"])
 for row in json.loads(PARSED.read_text(encoding="utf-8"))["records"]:
  if row["school"] in exact or row["school"].startswith(prefixes): continue
  grouped={}
  for hit in m.resolve(row["school"],strategy="all") or []:
   if hit.get("school_id"): grouped.setdefault(hit["matched_name"],set()).add(hit["school_id"]); ids.add(hit["school_id"])
  if not grouped: review.append({"src_name":row["school"],"entity_name":None,"schoolid":[]})
  for name, values in sorted(grouped.items()): review.append({"src_name":row["school"],"entity_name":name,"schoolid":sorted(values)})
 return sorted(ids),review
def main():
 p=argparse.ArgumentParser();p.add_argument("--review-output",type=Path);a=p.parse_args();ids,review=resolve()
 if a.review_output:a.review_output.write_text(json.dumps(review,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 else: print(len(ids))
if __name__=="__main__":main()
