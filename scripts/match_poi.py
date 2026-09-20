#!/usr/bin/env python3
"""
POI 匹配 CLI（薄封装）。

匹配实现已收敛至 scripts/registry/school_match.py（项目唯一校名匹配库：
normName/looseNorm/matchNorm 三档 + SchoolMatcher 统一服务，含行政区/学段收敛）。
本文件只保留命令行入口，逻辑不在本地重复定义。

用法：python3 match_poi.py <json_file_with_names>
输入 JSON: {"schools": ["校名1", "校名2", ...]}
输出 JSON: {"results": [{"name": "...", "poi_match": "...", "matched_name": "...", "stage": "...", "district": "..."}]}
"""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "registry"))
from school_match import SchoolMatcher

BASE = "/Users/bytedance/Developer/gz_school_research"


def main():
    if len(sys.argv) < 2:
        print("usage: match_poi.py <input.json>", file=sys.stderr)
        sys.exit(1)
    inp = json.load(open(sys.argv[1]))
    names = inp.get("schools", inp.get("names", []))
    matcher = SchoolMatcher.load(
        poi_paths=[(os.path.join(BASE, "data/poi/dist/primary_poi.json"), "小学"),
                   (os.path.join(BASE, "data/poi/dist/middle_poi.json"), "初中"),
                   (os.path.join(BASE, "data/poi/dist/high_poi.json"), "高中")],
        entities_path=os.path.join(BASE, "data/registry/entities.json"))
    results = []
    for name in names:
        r = matcher.resolve(name)
        r["name"] = name
        results.append(r)
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
