#!/usr/bin/env python3
"""
高德 POI 批量查询工具：入参为待查询地点列表（校名+区+学段，JSON），
批量调高德 text 搜索（按区限 citylimit），输出候选 POI，
再与实体表/POI 数据比对给出"可补/疑似/无结果"分类。

用法:
  python3 data/poi/scripts/amap_batch_query.py <input.json> [--output output.json]

输入 JSON 格式:
{
  "queries": [
    {"name": "广州市荔湾区博雅实验学校", "district": "荔湾", "adcode": "440103", "stage": "primary"},
    ...
  ]
}

输出 JSON 格式:
{
  "results": [
    {
      "query": {...},
      "classification": "可补"|"疑似"|"无结果"|"已存在POI",
      "candidates": [{"name","address","location","type","distance_to_existing"}],
      "matched_existing": {...} or null
    },
    ...
  ]
}
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

ROOT = "/Users/bytedance/Developer/gz_school_research"
ADCODE_MAP = {
    "荔湾": "440103", "越秀": "440104", "海珠": "440105",
    "天河": "440106", "白云": "440111", "黄埔": "440112", "番禺": "440113",
}

def load_key():
    env_path = os.path.join(ROOT, ".env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("AMAP_WEB_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("no AMAP_WEB_KEY in .env")

def api_call(url, retries=3, timeout=20):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))

def search_amap(key, keywords, adcode, offset=10):
    """text 搜索，返回候选 POI 列表。"""
    params = {
        "key": key,
        "keywords": keywords,
        "city": adcode,
        "citylimit": "true",
        "offset": str(offset),
        "page": "1",
        "extensions": "all",
    }
    url = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params)
    data = api_call(url)
    results = []
    if data.get("status") != "1":
        return [{"name": "API_ERROR", "address": data.get("info", ""), "location": "", "type": ""}]
    for poi in (data.get("pois") or []):
        results.append({
            "name": poi.get("name") or "",
            "address": (poi.get("address") or "").replace("\n", " "),
            "location": poi.get("location") or "",
            "type": poi.get("type") or "",
            "tel": poi.get("tel") or "",
        })
    return results

# 统一匹配库：norm 收敛至 school_match.matchNorm（含前导区名剥/去广州市/保留校区括号，泛词保护）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "scripts", "registry"))
from school_match import matchNorm as norm

def load_existing_poi():
    """加载所有学段现有 POI。"""
    all_poi = []
    for stage in ["primary", "middle", "high"]:
        path = os.path.join(ROOT, f"data/poi/dist/{stage}_poi.json")
        with open(path) as f:
            data = json.load(f)
        for s in data.get("schools", []):
            all_poi.append({
                "name": s["name"],
                "norm": norm(s["name"]),
                "lng": s.get("lng"),
                "lat": s.get("lat"),
                "adcode": s.get("adcode", ""),
                "stage": stage,
                "school_id": s.get("school_id", ""),
            })
    return all_poi

def dist_km(loc1, loc2):
    """近似距离（度→km）。"""
    try:
        x1, y1 = map(float, loc1.split(","))
        x2, y2 = map(float, loc2.split(","))
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5 * 97
    except Exception:
        return None

def classify_query(query_name, query_adcode, query_stage, candidates, existing_poi):
    """
    对查询结果分类：
    - 已存在POI：同名同区同学段已有 POI
    - 可补：找到高置信候选（名称匹配度高、类型含学校、同区），且该学段无同名 POI
    - 疑似：找到候选但匹配度一般，或与现有 POI 距离近可能重复
    - 无结果：无候选或候选均不相关
    """
    norm_query = norm(query_name)
    base_query = re.sub(r"[（(]?(小学部|初中部|高中部|校区)[）)]?.*$", "", norm_query)

    # 检查同学段是否已有同名 POI
    same_stage_exists = False
    for p in existing_poi:
        if p["adcode"] == query_adcode and p["stage"] == query_stage:
            if norm_query and (norm_query == p["norm"] or base_query and base_query in p["norm"]):
                same_stage_exists = True
                break

    if same_stage_exists:
        return "已存在POI", None

    if not candidates:
        return "无结果", []

    # 过滤有效候选（类型含教育/学校，或名称含学校/小学/中学/实验）
    valid_candidates = []
    for c in candidates:
        if c["name"] == "API_ERROR":
            continue
        ctype = c.get("type", "")
        cname = c.get("name", "")
        is_edu = any(kw in ctype for kw in ["科教文化", "教育", "学校", "小学", "中学", "幼儿园"])
        is_school_name = any(kw in cname for kw in ["学校", "小学", "中学", "实验", "外国语", "中英文", "学院"])
        if is_edu or is_school_name:
            valid_candidates.append(c)

    if not valid_candidates:
        return "无结果", candidates

    # 评估候选匹配度
    scored = []
    for c in valid_candidates:
        cname_norm = norm(c["name"])
        score = 0
        # 名称精确匹配
        if norm_query == cname_norm:
            score = 100
        # 基础名包含
        elif base_query and base_query in cname_norm:
            score = 80
        elif cname_norm and cname_norm in norm_query:
            score = 70
        # 关键词重叠
        else:
            common = set(base_query) & set(cname_norm) if base_query else set()
            score = len(common) * 5 if common else 0

        # 检查与现有 POI 的距离（防止重复补点）
        nearest_existing = None
        min_dist = float("inf")
        if c["location"]:
            for p in existing_poi:
                if p["adcode"] == query_adcode and p["lng"] and p["lat"]:
                    loc_p = f"{p['lng']},{p['lat']}"
                    d = dist_km(c["location"], loc_p)
                    if d is not None and d < min_dist:
                        min_dist = d
                        nearest_existing = p

        c["_score"] = score
        c["_nearest_existing"] = nearest_existing["name"] if nearest_existing else None
        c["_nearest_dist_km"] = round(min_dist, 2) if min_dist != float("inf") else None
        scored.append(c)

    scored.sort(key=lambda x: -x["_score"])
    top = scored[0]

    if top["_score"] >= 70:
        # 检查是否与现有 POI 过近（可能是同一所学校不同学段，坐标可复用而非新补）
        if top["_nearest_dist_km"] is not None and top["_nearest_dist_km"] < 0.1:
            return "疑似(与现有POI极近)", scored[:5]
        return "可补", scored[:5]
    elif top["_score"] >= 30:
        return "疑似", scored[:5]
    else:
        return "无结果", scored[:5]

def main():
    if len(sys.argv) < 2:
        print("用法: python3 amap_batch_query.py <input.json> [--output output.json]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output_path = sys.argv[idx + 1]

    with open(input_path) as f:
        inp = json.load(f)

    queries = inp.get("queries", inp.get("schools", []))
    if not queries:
        print("输入无 queries", file=sys.stderr)
        sys.exit(1)

    key = load_key()
    existing_poi = load_existing_poi()

    results = []
    for i, q in enumerate(queries):
        name = q.get("name", q.get("校名", ""))
        district = q.get("district", q.get("区", ""))
        adcode = q.get("adcode", ADCODE_MAP.get(district, ""))
        stage = q.get("stage", q.get("学段", ""))

        if not adcode and district in ADCODE_MAP:
            adcode = ADCODE_MAP[district]

        print(f"[{i+1}/{len(queries)}] 查询: {name} ({district} {adcode} {stage})", file=sys.stderr)

        candidates = search_amap(key, name, adcode)
        classification, scored = classify_query(name, adcode, stage, candidates, existing_poi)

        print(f"  → 分类: {classification}, 候选: {len(candidates)}", file=sys.stderr)

        results.append({
            "query": {"name": name, "district": district, "adcode": adcode, "stage": stage},
            "classification": classification,
            "candidates": scored if scored else candidates[:5],
        })

        # 限流
        time.sleep(0.3)

    output = {"results": results, "total": len(results)}

    # 统计
    from collections import Counter
    cls_count = Counter(r["classification"] for r in results)
    print(f"\n=== 统计 ===", file=sys.stderr)
    for cls, cnt in cls_count.most_common():
        print(f"  {cls}: {cnt}", file=sys.stderr)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n已写入 {output_path}", file=sys.stderr)
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
