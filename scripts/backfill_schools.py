#!/usr/bin/env python3
"""补位搜索：对官方名单中有、但高德 POI 未收录的学校逐校检索，尽量补点。

用法: python3 scripts/backfill_schools.py
依赖: 项目根 .env 的 AMAP_WEB_KEY
数据流:
  1. 读取 data/primary/enrollments/2026-panyu.json 的 unmatched（官方有、高德无）
  2. 逐校调高德 place/text 检索（city=440113，不限分类）
  3. 高置信命中 → 合并进 data/primary/schools-gz.json（唯一真源，追加，src=backfill 标记）
     + apps/web/legacy/_generated/primary/schools.js（旧页面兼容产物）
     并存 data/primary/schools-backfill.json 留痕
  4. 之后重跑 scripts/build_district_enrollment.py panyu 完成绑定
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "primary")

VARIANTS = {"穂": "穗", "敎": "教", "學": "学", "朮": "术", "甦": "苏"}
PREFIXES = ["市桥", "钟村", "石壁", "大石", "洛浦", "南村镇", "化龙镇", "新造镇",
            "小谷围街", "石楼镇", "石碁镇", "沙湾", "桥南", "东环", "沙头", "南村", "石碁"]
GENERIC_TAILS = ("中心小学", "第二小学", "第一小学", "第三小学", "第四小学",
                 "第五小学", "实验小学", "实验学校")

def norm(n):
    n = unicodedata.normalize("NFKC", str(n))
    n = n.replace("广州市", "").replace("番禺区", "").replace("番禺", "")
    for a, b in VARIANTS.items():
        n = n.replace(a, b)
    n = re.sub(r"[（(].*?[)）]", "", n)
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

def main():
    key = load_key()
    with open(os.path.join(DATA, "enrollments", "2026-panyu.json"), encoding="utf-8") as f:
        enr = json.load(f)
    missing = sorted(set(enr["unmatched"]))

    # 加载现有 POI 避免重复（数据真源为 JSON；js 产物同步写 legacy/_generated）
    with open(os.path.join(DATA, "schools-gz.json"), encoding="utf-8") as f:
        data = json.load(f)
    existing = {(s["name"], round(s["lng"], 5), round(s["lat"], 5)) for s in data["schools"]}

    found, uncertain, notfound = [], [], []
    for school in missing:
        cands = search_school(key, school)
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
    added = 0
    for f_ in found:
        if f_.get("note") == "POI 已存在":
            continue
        poi = f_["poi"]
        key_t = (poi["name"], round(poi["lng"], 5), round(poi["lat"], 5))
        if key_t in existing:
            continue
        rec = {"name": poi["name"], "lng": poi["lng"], "lat": poi["lat"],
               "adcode": "440113", "src": "backfill",
               "matched_to": f_["school"], "match_score": f_["score"]}
        data["schools"].append(rec)
        existing.add(key_t)
        added += 1

    if added:
        data["note"] = data.get("note", "") + "；含 backfill 补充点位"
        with open(os.path.join(DATA, "schools-gz.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        legacy_dir = os.path.join(BASE, "apps", "web", "legacy", "_generated", "primary")
        os.makedirs(legacy_dir, exist_ok=True)
        with open(os.path.join(legacy_dir, "schools.js"), "w", encoding="utf-8") as f:
            f.write("window.GZ_SCHOOLS = ")
            json.dump(data, f, ensure_ascii=False)
            f.write(";\n")
        with open(os.path.join(DATA, "schools-backfill.json"), "w", encoding="utf-8") as f:
            json.dump({"updated": time.strftime("%Y-%m-%d"), "added": added, "items": found},
                      f, ensure_ascii=False, indent=1)
        print(f"\n已追加 {added} 个补充点位 → data/primary/schools-gz.json（js 产物已同步 legacy/_generated）")

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
