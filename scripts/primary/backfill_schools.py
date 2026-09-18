#!/usr/bin/env python3
"""补位搜索：对官方名单中有、但高德 POI 未收录的学校逐校检索，尽量补点。

用法: python3 scripts/primary/backfill_schools.py
依赖: 项目根 .env 的 AMAP_WEB_KEY
数据流:
  1. 读取 data/primary/enrollments/2026-panyu.json 的 unmatched（官方有、高德无）
  2. 逐校调高德 place/text 检索（city=440113，不限分类）
  3. 高置信命中 → 合并进 data/primary/schools-gz.json（唯一真源，追加，src=backfill 标记）
     并存 data/primary/schools-backfill.json 留痕
  4. 之后重跑 scripts/primary/build_district_enrollment.py panyu 完成绑定
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 项目根（scripts/primary/ 的上三层）
DATA = os.path.join(ROOT, "data", "primary")

# 统一匹配库：norm 本体（NFKC/繁简/去广州市/删括号/去空白）收敛至 school_match.normName；
# 番禺采集特有的输入清洗（去区名/镇）保留在本地，不再重复定义 norm 逻辑
sys.path.insert(0, os.path.join(ROOT, "scripts/registry"))
from school_match import normName as _normName, fold_unicode as _fold

PREFIXES = ["市桥", "钟村", "石壁", "大石", "洛浦", "南村镇", "化龙镇", "新造镇",
            "小谷围街", "石楼镇", "石碁镇", "沙湾", "桥南", "东环", "沙头", "南村", "石碁"]
GENERIC_TAILS = ("中心小学", "第二小学", "第一小学", "第三小学", "第四小学",
                 "第五小学", "实验小学", "实验学校")

def norm(n):
    n = _normName(_fold(n))  # fold=NFKC+繁简（采集输入清洗），norm 本体统一
    n = n.replace("番禺区", "").replace("番禺", "")
    n = n.replace("小学校", "小学").replace("镇", "").strip()
    return n

def strip_prefix(n):
    for p in PREFIXES:
        if n.startswith(p):
            return n[len(p):]
    return n

def is_generic(s):
    return any(s == g or s.endswith(g) for g in GENERIC_TAILS)

def is_campus(n):
    return any(w in n for w in ("东校区", "西校区", "南校区", "北校区", "大龙校区", "首开校区", "新校区", "校区"))

def load_key():
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            line = line.strip()
            if line.startswith("AMAP_WEB_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("未找到 .env 的 AMAP_WEB_KEY")

def api(key, params):
    params["key"] = key
    url = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params)
    for a in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            if a == 2:
                return {"error": str(e)}
            time.sleep(1.5)

def search_school(key, school):
    """按官方名检索番禺区 POI，返回排序后的候选 [(score, poi)]"""
    kws = [school, re.sub(r"学校$", "", school), re.sub(r"小学$", "", school)]
    cands = {}
    for kw in kws[:2]:
        d = api(key, {"keywords": kw, "city": "440113", "citylimit": "true",
                      "offset": "10", "page": "1", "extensions": "all"})
        pois = d.get("pois") or []
        for p in pois:
            cands.setdefault(p["id"], p)
        time.sleep(0.35)

    nx = norm(school)
    nxs = strip_prefix(nx)
    nx_eq = nxs.replace("学校", "小学")
    out = []
    for p in cands.values():
        pn = norm(p.get("name") or "")
        pns = strip_prefix(pn)
        pn_eq = pns.replace("学校", "小学")
        t = (p.get("type") or "")
        # 非学校类 POI 直接排除（培训机构/地产等）
        if not any(w in t or w in pn for w in ("学校", "小学", "附小", "教育")):
            continue
        if any(b in pn for b in ("培训", "托辅", "托管", "辅导", "自习", "成长中心",
                                 "学习中心", "文具", "书店", "幼儿园", "工地", "智云书房")):
            continue
        score = 0
        if nx == pn:
            score = 1000
        elif nxs == pn:
            score = 950
        elif nx == pns:
            score = 900
        elif nx_eq == pn:
            score = 850
        elif nx in pn or pn in nx:
            short = nx if len(nx) <= len(pn) else pn
            score = 600 + min(len(nx), len(pn)) if not is_generic(short) else 0
        elif (len(nxs) >= 3 and nxs in pn and not is_generic(nxs)) or \
             (len(pns) >= 3 and nx in pns and not is_generic(pns)):
            score = 500 + min(len(nx), len(pn))
        elif (len(nx_eq) >= 3 and nx_eq in pn_eq and not is_generic(nx_eq)) or \
             (len(pn_eq) >= 3 and pn_eq in nx_eq and not is_generic(pn_eq)):
            score = 450 + min(len(nx_eq), len(pn_eq))
        if score > 0:
            out.append((score, p))
    out.sort(key=lambda x: -x[0])
    return out

# 官方名 → 指定高德查询词（官方名单名与高德 POI 名不一致的补录，2026-09-18 高德核实）：
#   化龙镇中心小学：2026 秋整体搬迁至复甦安置区配建学校，高德 POI「复苏小学」（复苏路38号）
#   新桥小学：大龙街新桥村市莲路桥东大街2号，高德 POI「新桥学校」（市莲路153旁）
#   石碁镇永善小学：石碁镇永善村义里上街4号，高德 POI「永善学校」（义里上街4号）
PATCH_QUERIES = {
    "化龙镇中心小学": "复苏小学",
    "新桥小学": "新桥学校",
    "石碁镇永善小学": "永善学校",
}

def main():
    key = load_key()
    with open(os.path.join(DATA, "enrollments", "2026-panyu.json"), encoding="utf-8") as f:
        enr = json.load(f)
    # 支持 --only 白名单（如「python3 backfill_schools.py 化龙镇中心小学」只补该所，避免全量不可控）
    import sys as _sys
    only = set(_sys.argv[1:]) if len(_sys.argv) > 1 else set()
    missing = sorted(set(enr["unmatched"]))
    if only:
        missing = [s for s in missing if s in only]

    # 加载现有 POI 避免重复（数据真源为 JSON）
    with open(os.path.join(DATA, "schools-gz.json"), encoding="utf-8") as f:
        data = json.load(f)
    existing = {(s["name"], round(s["lng"], 5), round(s["lat"], 5)) for s in data["schools"]}
    by_name = {s["name"]: s for s in data["schools"]}

    found, uncertain, notfound = [], [], []
    for school in missing:
        query = PATCH_QUERIES.get(school, school)  # 官方名与 POI 名不一致时用指定查询词
        cands = search_school(key, query)
        if not cands:
            notfound.append(school)
            continue
        score, p = cands[0]
        loc = (p.get("location") or "").split(",")
        if len(loc) != 2:
            uncertain.append({"school": school, "reason": "无坐标", "poi": p.get("name")})
            continue
        poi = {"name": p.get("name"), "lng": float(loc[0]), "lat": float(loc[1]),
               "adcode": "440113", "src": "backfill", "match_score": score,
               "match_rule": "exact" if score >= 850 else "fuzzy"}
        if (poi["name"], round(poi["lng"], 5), round(poi["lat"], 5)) in existing:
            found.append({"school": school, "poi": poi, "score": score, "note": "POI 已存在"})
        elif score >= 600:
            found.append({"school": school, "poi": poi, "score": score, "note": ""})
        else:
            uncertain.append({"school": school, "reason": f"分数低({score})", "poi": p.get("name")})
        time.sleep(0.35)

    # 应用：把高置信命中追加进 schools.js / schools-gz.json（避免覆盖已有）
    added, updated = 0, 0
    for f_ in found:
        if f_.get("note") == "POI 已存在":
            continue
        poi = f_["poi"]
        key_t = (poi["name"], round(poi["lng"], 5), round(poi["lat"], 5))
        if key_t in existing:
            continue
        # 同名 POI 已存在但无坐标（历史采集缺 loc）→ 补坐标，不追加重复
        if poi["name"] in by_name and by_name[poi["name"]].get("lng") is None:
            by_name[poi["name"]].update({"lng": poi["lng"], "lat": poi["lat"], "src": "backfill"})
            existing.add(key_t)
            updated += 1
            continue
        rec = {"name": poi["name"], "lng": poi["lng"], "lat": poi["lat"],
               "adcode": "440113", "src": "backfill",
               "matched_to": f_["school"], "match_score": f_["score"]}
        data["schools"].append(rec)
        existing.add(key_t)
        added += 1

    if added or updated:
        data["note"] = data.get("note", "") + "；含 backfill 补充点位"
        with open(os.path.join(DATA, "schools-gz.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(DATA, "schools-backfill.json"), "w", encoding="utf-8") as f:
            json.dump({"updated": time.strftime("%Y-%m-%d"), "added": added, "items": found},
                      f, ensure_ascii=False, indent=1)
        print(f"\n已追加 {added} 个补充点位 → data/primary/schools-gz.json")

    print(f"命中: {len(found)} / 存疑: {len(uncertain)} / 未找到: {len(notfound)}")
    print("\n== 命中 ==")
    for f_ in found:
        print(" ", f_["school"], "→", f_["poi"]["name"], f"({f_['score']})", f_["note"])
    print("\n== 存疑 ==")
    for u in uncertain:
        print(" ", u)
    print("\n== 未找到 ==")
    for n in notfound:
        print(" ", n)

if __name__ == "__main__":
    main()
