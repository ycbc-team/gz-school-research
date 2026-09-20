#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广州市中小学生创新大赛初中金种子组获奖名单解析（raw → parsed → dist）。

输入：raw/创新大赛_初中金种子组获奖名单_YYYY.xls（每年一个文件）
规则：
  - 名单本身即初中段，所有获奖学生均为初中生
  - 带括号校区名 → 精确匹配该校区 middle school_id
  - 整体名 → 一对多，该学校所有 middle 校区 school_id 都挂
  - 排除少年宫/青少年宫（非学校）
  - 区码收窄：school_id adcode 与官方区属一致
  - 品牌成员校（独立法人）排除
输出：
  - parsed/innovation_YYYY.json  每年完整记录
  - dist/compiled.json           聚合所有年份（school_id → 历年奖牌）
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # gz_school_research/
RAW = Path(__file__).resolve().parent.parent / "raw"
PARSED = Path(__file__).resolve().parent.parent / "parsed"
DIST = Path(__file__).resolve().parent.parent / "dist"
ENTITIES = ROOT / "data/registry/entities.json"

DISTRICT_ADCODE = {"荔湾": "440103", "越秀": "440104", "海珠": "440105", "天河": "440106",
                   "白云": "440111", "黄埔": "440112", "番禺": "440113", "花都": "440114",
                   "南沙": "440115", "从化": "440117", "增城": "440118"}
NON_SCHOOL = ["少年宫", "青少年宫"]
BRAND_SUFFIX = ["附属学校", "附属实验", "实验学校", "附属小学", "附属中学", "外国语学校"]


def core_name(s):
    s = s.replace("（", "(").replace("）", ")").replace(" ", "").strip()
    paren = re.search(r"[（(](.+?)[)）]", s)
    campus = paren.group(1) if paren else ""
    s = re.sub(r"[（(].*?[)）]", "", s)
    s = re.sub(r"^广州市", "", s)
    for d in DISTRICT_ADCODE:
        s = re.sub(r"^" + d + r"区?", "", s)
    return s, campus


def parse_year(year, ents):
    year = int(year)
    import xlrd
    xls = RAW / f"创新大赛_初中金种子组获奖名单_{year}.xls"
    wb = xlrd.open_workbook(str(xls))
    sh = wb.sheet_by_index(0)

    # 三年列结构不同，按年份映射列索引
    if year == 2026:
        # col2=项目, col3=学校, col4=负责人, col5=成员, col6=指导老师, col7=奖项, col8=区属
        COLS = {"project": 2, "school": 3, "leader": 4, "members": 5, "coach": 6, "award": 7, "district": 8}
        header_row = 3
    elif year == 2025:
        # col2=项目, col3=负责人, col4=成员, col5=学校, col6=指导老师, col7=区属, col8=奖项
        COLS = {"project": 2, "school": 5, "leader": 3, "members": 4, "coach": 6, "award": 8, "district": 7}
        header_row = 3
    elif year == 2024:
        # col1=成员, col2=负责人, col3=学校, col4=指导老师, col5=奖次, col6=项目, col7=区属
        COLS = {"project": 6, "school": 3, "leader": 2, "members": 1, "coach": 4, "award": 5, "district": 7}
        header_row = 4

    rows = []
    for r in range(header_row, sh.nrows):
        row = [str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
        if not row[COLS["school"]]: continue
        rows.append({"school": row[COLS["school"]], "award": row[COLS["award"]], "district": row[COLS["district"]],
                     "project": row[COLS["project"]], "leader": row[COLS["leader"]],
                     "members": row[COLS["members"]], "coach": row[COLS["coach"]]})

    matched_records = []
    skipped = []
    for rec in rows:
        school = rec["school"]
        if any(kw in school for kw in NON_SCHOOL):
            skipped.append({"school": school, "reason": "非学校"})
            continue
        for sname in re.split(r"[\n\r]+", school):
            sname = sname.strip()
            if not sname: continue
            core, campus = core_name(sname)
            expect_adcode = DISTRICT_ADCODE.get(rec["district"].replace("区", ""))
            cands = [e for e in ents if e["stage"] == "middle" and (core in e["name"] or e["name"] in core)]
            if expect_adcode:
                cands = [e for e in cands if e["school_id"].split("-")[1] == expect_adcode]
            cands = [e for e in cands if not any(suf in e["name"] and suf not in core for suf in BRAND_SUFFIX)]
            if campus:
                cands = [e for e in cands if campus in e["name"]] or cands
            sids = sorted(set(e["school_id"] for e in cands))
            rec["school_ids"] = sids
            rec["match_type"] = "single" if len(sids) == 1 else ("multi" if len(sids) > 1 else "none")
            matched_records.append(rec)

    by_school = {}
    for rec in matched_records:
        if not rec["school_ids"]: continue
        medal = {"金": "gold", "银": "silver", "铜": "bronze"}[rec["award"][0]]
        for sid in rec["school_ids"]:
            by_school.setdefault(sid, {"gold": 0, "silver": 0, "bronze": 0})
            by_school[sid][medal] += 1

    out = {
        "metric": "innovation_awards",
        "competition": "广州市中小学生创新大赛·初中金种子组",
        "year": year,
        "source_file": xls.name,
        "total_records": len(rows),
        "skipped": skipped,
        "records": matched_records,
        "compiled_schools": len(by_school),
    }
    PARSED.mkdir(exist_ok=True)
    (PARSED / f"innovation_{year}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{year}] records={len(rows)} schools={len(by_school)} skipped={len(skipped)}")
    return by_school


def main():
    ents = json.load(open(ENTITIES))["entities"]
    years = sorted([p.stem.split("_")[-1] for p in RAW.glob("创新大赛_初中金种子组获奖名单_*.xls")])
    all_schools = {}
    for y in years:
        by_school = parse_year(y, ents)
        for sid, medals in by_school.items():
            all_schools.setdefault(sid, {"years": {}})
            all_schools[sid]["years"][y] = medals

    compiled = {}
    for sid, data in all_schools.items():
        compiled[sid] = {"innovation_awards": data}

    DIST.mkdir(exist_ok=True)
    (DIST / "compiled.json").write_text(json.dumps(compiled, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n聚合完成: {len(compiled)} 个 school_id, 年份={years}")


if __name__ == "__main__":
    main()
