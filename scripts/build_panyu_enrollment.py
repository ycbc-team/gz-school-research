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
import sys
import xlrd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "enrollments")

def norm(s):
    return str(s).strip() if s is not None else ""

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

    # ---- 与已有番禺学校点位匹配（双向包含 + 长度差异去歧义） ----
    with open(os.path.join(ROOT, "data", "schools.js"), encoding="utf-8") as f:
        js = f.read()
    import re
    m = re.search(r"window\.GZ_SCHOOLS\s*=\s*(\{.*?\});?\s*$", js, re.S)
    data = json.loads(m.group(1))
    panyu = [s for s in data.get("schools", []) if s.get("adcode") == "440113"]

    def norm_school(n):
        n = str(n).replace("广州市", "").replace("番禺区", "").replace("番禺", "")
        n = re.sub(r"[（(].*?[)）]", "", n)
        n = n.replace("小学校", "小学").strip()
        return n

    def sim(a, b):
        if not a or not b:
            return 0
        if a == b:
            return len(a) * 2
        if a in b or b in a:
            return min(len(a), len(b))
        return 0

    poi_by_school = {}
    for s in panyu:
        poi_by_school.setdefault(s["name"], s)

    matched, unmatched, ambiguous = [], [], []
    used_poi = {}
    for rec in records:
        nx = norm_school(rec["school"])
        best = None
        best_score = 0
        for s in panyu:
            np_ = norm_school(s["name"])
            sc = sim(nx, np_)
            if sc > best_score or (sc == best_score and sc > 0 and best is not None and abs(len(nx) - len(norm_school(best["name"]))) > abs(len(nx) - len(np_))):
                best, best_score = s, sc
        if best and best_score > 0:
            hit = best
            if hit["name"] in used_poi and used_poi[hit["name"]] != rec["school"]:
                ambiguous.append({"school": rec["school"], "poi": hit["name"]})
            used_poi[hit["name"]] = rec["school"]
            rec["school_id"] = hit["name"]
            rec["lng"], rec["lat"] = hit["lng"], hit["lat"]
            matched.append(rec)
        else:
            unmatched.append(rec["school"])

    result = {
        "year": 2026,
        "district": "番禺区",
        "source": "番禺区教育局《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》",
        "source_url": "https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10794/mpost_10794083.html",
        "records": matched,
        "unmatched": sorted(set(unmatched)),
        "ambiguous": ambiguous,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "2026-panyu.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "2026-panyu.js"), "w", encoding="utf-8") as f:
        f.write("window.GZ_ENROLL_PANYU = ")
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print(f"记录总数: {len(records)}（公办{sum(1 for r in records if r['nature']=='公办')} / 民办{sum(1 for r in records if r['nature']=='民办')}）")
    print(f"匹配到点位: {len(matched)} / 未匹配: {len(unmatched)} / 歧义: {len(ambiguous)}")
    if unmatched:
        print("未匹配学校名:", sorted(set(unmatched))[:40])
    if ambiguous:
        print("歧义绑定:", ambiguous[:20])

if __name__ == "__main__":
    main()
