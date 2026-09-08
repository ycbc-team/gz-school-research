#!/usr/bin/env python3
"""解析番禺区 2026 年招生计划 xls → 离线招生数据库（data/enrollments/）。

数据源: 番禺区教育局《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》
官方通知: https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10794/mpost_10794083.html
附件: https://www.panyu.gov.cn/gzpyjy/attachment/8/8018/8018386/10794083.xls

用法: python3 scripts/build_panyu_enrollment.py [xls路径]
输出:
  data/enrollments/2026-panyu.json   可复核数据
  data/enrollments/2026-panyu.js     页面加载（window.GZ_ENROLL_PANYU）
"""
import json
import os
import re
import sys
import unicodedata
import xlrd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "enrollments")

def norm(s):
    return str(s).strip() if s is not None else ""

# ---- 名称归一化与匹配 ----
VARIANTS = {"穂": "穗", "敎": "教", "學": "学", "朮": "术", "甦": "苏"}
PREFIXES = ["市桥", "钟村", "石壁", "大石", "洛浦", "南村镇", "化龙镇", "新造镇",
            "小谷围街", "石楼镇", "石碁镇", "沙湾", "桥南", "东环", "沙头", "南村",
            "石碁"]
CAMPUS_WORDS = ["东校区", "西校区", "南校区", "北校区", "大龙校区", "首开校区",
                "新校区", "校区"]
# 泛称后缀：如「中心小学」「第二小学」「实验小学」，作为被包含短侧时容易误配，禁止参与包含匹配
GENERIC_TAILS = ("中心小学", "第二小学", "第一小学", "第三小学", "第四小学",
                 "第五小学", "实验小学", "实验学校")

def is_generic(s):
    return any(s == g or s.endswith(g) for g in GENERIC_TAILS)

def norm_school(n):
    n = unicodedata.normalize("NFKC", str(n))
    n = n.replace("广州市", "").replace("番禺区", "").replace("番禺", "")
    for a, b in VARIANTS.items():
        n = n.replace(a, b)
    n = re.sub(r"[（(].*?[)）]", "", n)
    n = n.replace("小学校", "小学")
    n = n.replace("镇", "")  # 化龙镇/石楼镇/石碁镇等，删「镇」统一（镇名去掉仍唯一）
    n = n.strip()
    return n

def strip_prefix(n):
    for p in PREFIXES:
        if n.startswith(p):
            return n[len(p):]
    return n

def is_campus(n):
    return any(w in n for w in CAMPUS_WORDS)

def rank_candidates(rec_school, poi_list):
    """为一条官方记录计算所有 POI 的匹配分，返回降序候选 [(score, prefer, poi)]

    规则（保守优先，避免「中心小学」等公共词误配）：
      1000 全名精确
       950 官方 strip 镇街前缀 == POI 全名（市桥东兴小学 → 东兴小学）
       900 POI strip 前缀 == 官方全名
       850 「学校/小学」词尾等价后精确（横江民生学校 ↔ 横江民生小学）
       600+ 全名互相包含
       500+ 单侧 strip 后包含
       450+ 词尾等价后包含
    严禁双侧 strip 后比较（会把所有「XX中心小学」归并为「中心小学」）。
    """
    nx = norm_school(rec_school)
    nxs = strip_prefix(nx)
    nx_eq = nxs.replace("学校", "小学")
    rec_campus = is_campus(rec_school)
    out = []
    for p in poi_list:
        pn = norm_school(p["name"])
        pns = strip_prefix(pn)
        pn_eq = pns.replace("学校", "小学")
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
        if score <= 0:
            continue
        # 偏好：官方记录含「校区」→ 校区 POI 优先；否则主校区（无校区字样）优先
        prefer = 0 if rec_campus == is_campus(p["name"]) else (-1 if is_campus(p["name"]) else 1)
        out.append((score, prefer, p))
    out.sort(key=lambda x: (-x[0], -x[1]))
    return out

def main():
    xls_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/bytedance/Downloads/panyu_2026.xls"
    wb = xlrd.open_workbook(xls_path)

    records = []  # 小学招生记录

    # ---- Sheet1 公办小学 ----
    sh = wb.sheet_by_name("公办小学招生地段、计划")
    district = ""
    for r in range(3, sh.nrows):
        d = norm(sh.cell_value(r, 0))
        if d:
            district = d.replace("\n", "")
        school = norm(sh.cell_value(r, 1))
        if not school:
            continue
        plan = sh.cell_value(r, 2)
        zone = norm(sh.cell_value(r, 3))
        note = norm(sh.cell_value(r, 4))
        records.append({
            "school": school,
            "district": district,
            "nature": "公办",
            "plan_classes": int(plan) if isinstance(plan, float) and plan == int(plan) else (plan if isinstance(plan, (int, float)) else None),
            "zone": zone,
            "note": note,
            "source": "番禺区教育局2026",
        })

    # ---- Sheet3 民办小学 ----
    sh2 = wb.sheet_by_name("民办招生计划")
    district2 = ""
    for r in range(5, sh2.nrows):
        d = norm(sh2.cell_value(r, 0))
        if d:
            district2 = d.replace("\n", "")
        school = norm(sh2.cell_value(r, 1))
        if not school:
            continue
        classes = sh2.cell_value(r, 2)  # 小学班数
        persons = sh2.cell_value(r, 3)  # 小学人数
        note = norm(sh2.cell_value(r, 6))
        records.append({
            "school": school,
            "district": district2,
            "nature": "民办",
            "plan_classes": int(classes) if isinstance(classes, float) and classes == int(classes) else (classes if isinstance(classes, (int, float)) else None),
            "plan_count": int(persons) if isinstance(persons, float) and persons == int(persons) else (persons if isinstance(persons, (int, float)) else None),
            "zone": "民办：无地段，报名人数超计划电脑派位（摇号）",
            "note": note,
            "source": "番禺区教育局2026",
        })

    # ---- 与已有番禺学校点位匹配 ----
    with open(os.path.join(ROOT, "data", "schools.js"), encoding="utf-8") as f:
        js = f.read()
    m = re.search(r"window\.GZ_SCHOOLS\s*=\s*(\{.*?\});?\s*$", js, re.S)
    data = json.loads(m.group(1))
    panyu = [s for s in data.get("schools", []) if s.get("adcode") == "440113"]

    # 全局按匹配分从高到低分配 POI；同一 POI 被多条官方记录竞争时，高分者得，其余记歧义
    bindings = []  # (score, rec_idx, poi)
    for idx, rec in enumerate(records):
        cands = rank_candidates(rec["school"], panyu)
        if cands:
            bindings.append((cands[0][0], idx, cands[0][2]))
    bindings.sort(key=lambda x: -x[0])

    matched_records, ambiguous = [], []
    used_poi = {}
    has_poi = set()
    for score, idx, poi in bindings:
        if poi["name"] in used_poi:
            ambiguous.append({"school": records[idx]["school"], "poi": poi["name"],
                              "compete_with": used_poi[poi["name"]]})
            continue
        used_poi[poi["name"]] = records[idx]["school"]
        has_poi.add(poi["name"])
        rec = dict(records[idx])
        rec["school_id"] = poi["name"]
        rec["lng"], rec["lat"] = poi["lng"], poi["lat"]
        matched_records.append(rec)

    # 未被任何官方记录绑定的 POI（高德有、官方无）
    poi_leftover = [s["name"] for s in panyu if s["name"] not in has_poi]
    matched_names = {r["school"] for r in matched_records}
    unmatched = [r["school"] for r in records if r["school"] not in matched_names]

    result = {
        "year": 2026,
        "district": "番禺区",
        "source": "番禺区教育局《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》",
        "source_url": "https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10794/mpost_10794083.html",
        "records": matched_records,
        "unmatched": sorted(set(unmatched)),
        "ambiguous": ambiguous,
        "poi_leftover": sorted(set(poi_leftover)),
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "2026-panyu.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "2026-panyu.js"), "w", encoding="utf-8") as f:
        f.write("window.GZ_ENROLL_PANYU = ")
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print(f"记录总数: {len(records)}（公办{sum(1 for r in records if r['nature']=='公办')} / 民办{sum(1 for r in records if r['nature']=='民办')}）")
    print(f"番禺 POI: {len(panyu)} | 匹配到点位: {len(matched_records)} / 未匹配: {len(unmatched)} / 歧义: {len(ambiguous)} / POI无官方记录: {len(poi_leftover)}")
    if unmatched:
        print("官方有高德无（未匹配）:", sorted(set(unmatched))[:50])
    if poi_leftover:
        print("高德有官方无（POI 无记录）:", sorted(poi_leftover))
    if ambiguous:
        print("歧义绑定:", ambiguous[:20])

if __name__ == "__main__":
    main()
