#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广州市中小学生科技创客电视大赛获奖名单解析。

输入：raw/创客大赛_{个人,团体}项目获奖名单_YYYY.xls
规则：
  - 参赛组别列：小学组→primary，中学组→middle/high（中学组混初+高，暂只挂 middle）
  - 带括号校区名 → 精确匹配
  - 整体名 → 一对多，该学校所有同学段校区
  - 品牌成员校排除
输出：
  - parsed/chuangke_YYYY.json
  - dist/compiled.json 聚合
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent.parent / "raw"
PARSED = Path(__file__).resolve().parent.parent / "parsed"
DIST = Path(__file__).resolve().parent.parent / "dist"
ENTITIES = ROOT / "data/registry/entities.json"

DISTRICT_ADCODE = {"荔湾": "440103", "越秀": "440104", "海珠": "440105", "天河": "440106",
                   "白云": "440111", "黄埔": "440112", "番禺": "440113", "花都": "440114",
                   "南沙": "440115", "从化": "440117", "增城": "440118"}
NON_SCHOOL = ["少年宫", "青少年宫"]
BRAND_SUFFIX = ["附属学校", "附属实验", "实验学校", "附属小学", "附属中学", "外国语学校"]
GROUP_STAGE = {"小学组": "primary", "中学组": "middle"}


def core_name(s):
    s = s.replace("（", "(").replace("）", ")").replace(" ", "").strip()
    paren = re.search(r"[（(](.+?)[)）]", s)
    campus = paren.group(1) if paren else ""
    s = re.sub(r"[（(].*?[)）]", "", s)
    s = re.sub(r"^广州市", "", s)
    for d in DISTRICT_ADCODE:
        s = re.sub(r"^" + d + r"区?", "", s)
    return s, campus


def match_school(school, stage, ents):
    core, campus = core_name(school)
    cands = [e for e in ents if e["stage"] == stage and (core in e["name"] or e["name"] in core)]
    cands = [e for e in cands if not any(suf in e["name"] and suf not in core for suf in BRAND_SUFFIX)]
    # 区码收窄：从原始校名提取区码
    for dname, adcode in DISTRICT_ADCODE.items():
        if dname in school:
            cands_in_dist = [e for e in cands if adcode in e["school_id"]]
            if cands_in_dist:
                cands = cands_in_dist
            break
    if campus:
        cands = [e for e in cands if campus in e["name"]] or cands
    return sorted(set(e["school_id"] for e in cands))


def parse_personal(year, ents):
    import xlrd
    wb = xlrd.open_workbook(str(RAW / f"创客大赛_个人项目获奖名单_{year}.xls"))
    sh = wb.sheet_by_index(0)
    records = []
    for r in range(4, sh.nrows):
        row = [str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
        if not row[1]: continue
        records.append({
            "school": row[1], "student": row[2], "project": row[3],
            "group": row[4], "coach": row[5], "award": row[6], "type": "personal",
        })
    return records


def parse_team(year, ents):
    import xlrd
    wb = xlrd.open_workbook(str(RAW / f"创客大赛_团体项目获奖名单_{year}.xls"))
    sh = wb.sheet_by_index(0)
    records = []
    for r in range(4, sh.nrows):
        row = [str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
        if not row[1]: continue
        records.append({
            "school": row[1], "student": row[2], "group": row[3],
            "coach": row[4], "award": row[5], "type": "team",
        })
    return records


def main():
    ents = json.load(open(ENTITIES))["entities"]
    years = sorted(set(
        re.search(r"(\d{4})", p.name).group(1)
        for p in RAW.glob("创客大赛_*获奖名单_*.xls")
    ))
    all_schools = {}
    all_records = []

    for y in years:
        records = parse_personal(y, ents) + parse_team(y, ents)
        matched = []
        skipped = []
        for rec in records:
            if any(kw in rec["school"] for kw in NON_SCHOOL):
                skipped.append({**rec, "reason": "非学校"})
                continue
            stage = GROUP_STAGE.get(rec["group"])
            if not stage:
                skipped.append({**rec, "reason": f"未知组别:{rec['group']}"})
                continue
            sids = match_school(rec["school"], stage, ents)
            rec["school_ids"] = sids
            rec["stage"] = stage
            matched.append(rec)
            for sid in sids:
                all_schools.setdefault(sid, {"stages": {}})
                all_schools[sid]["stages"].setdefault(stage, {}).setdefault(y, {"gold": 0, "silver": 0, "bronze": 0})
                medal = {"一等": "gold", "二等": "silver", "三等": "bronze"}.get(rec["award"][:2])
                if medal:
                    all_schools[sid]["stages"][stage][y][medal] += 1
        all_records.append({"year": y, "records": matched, "skipped": skipped})
        print(f"[{y}] records={len(records)} matched={len(matched)} skipped={len(skipped)}")

    compiled = {sid: {"chuangke_awards": data} for sid, data in all_schools.items()}
    PARSED.mkdir(exist_ok=True)
    (PARSED / "chuangke.json").write_text(json.dumps({"records": all_records}, ensure_ascii=False, indent=2), encoding="utf-8")
    DIST.mkdir(exist_ok=True)
    (DIST / "compiled.json").write_text(json.dumps(compiled, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n聚合: {len(compiled)} school_id")


if __name__ == "__main__":
    main()
