#!/usr/bin/env python3
import html, json, re
from pathlib import Path
BUSINESS=Path(__file__).resolve().parents[1]; RAW=BUSINESS/"raw"; OUT=BUSINESS/"parsed"/"provincial_civilized_campuses.json"
def main():
    text=(RAW/"provincial_civilized_campuses_1_2017.html").read_text(encoding="utf-8")
    values=[re.sub(r"\s+","",html.unescape(re.sub(r"<[^>]+>","",x))).strip() for x in re.findall(r"<p[^>]*>(.*?)</p>",text,re.S|re.I)]
    start=next(i for i,x in enumerate(values) if "第一届广东省文明校园名单" in x); names=[]
    for x in values[start+1:]:
        if x: names.append(x)
        if len(names)==61: break
    assert len(names)==61
    OUT.write_text(json.dumps({"dataset":"广东省文明校园名单原文摘录","records":[{"school":x,"award":"第一届广东省文明校园","source_url":"https://ld.southcn.com/node_5102313f8b/0bd3619345.shtml"} for x in names]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__": main()
