#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广州市中小学生科技创客电视大赛获奖名单解析。

输入：raw/创客大赛_{个人,团体}项目获奖名单_YYYY.xls(x)
规则：
  - 参赛组别列：小学组→primary；中学组→secondary（初中+高中，不擅自拆分）
  - 带括号校区名 → 精确匹配
  - 整体名 → 一对多，该学校所有同学段校区
  - 品牌成员校排除
输出：
  - parsed/chuangke_YYYY.json
  - dist/compiled.json 聚合
"""
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent.parent / "raw"
PARSED = Path(__file__).resolve().parent.parent / "parsed"
DIST = Path(__file__).resolve().parent.parent / "dist"
ENTITIES = ROOT / "data/registry/entities.json"

sys.path.insert(0, str(ROOT / "scripts" / "registry"))
from school_match import SchoolMatcher

DISTRICT_ADCODE = {"荔湾": "440103", "越秀": "440104", "海珠": "440105", "天河": "440106",
                   "白云": "440111", "黄埔": "440112", "番禺": "440113", "花都": "440114",
                   "南沙": "440115", "从化": "440117", "增城": "440118"}
NON_SCHOOL = ["少年宫", "青少年宫"]
XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def workbook_rows(path):
    """返回首个工作表的稀疏补齐行；同时支持教育局常见的 xls / xlsx 附件。"""
    if path.suffix.lower() == ".xls":
        import xlrd
        sheet = xlrd.open_workbook(str(path)).sheet_by_index(0)
        return [[str(sheet.cell_value(row, col)).strip() for col in range(sheet.ncols)] for row in range(sheet.nrows)]

    with ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall(f"{XLSX_NS}si")]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows = []
    for row in sheet.findall(f".//{XLSX_NS}sheetData/{XLSX_NS}row"):
        values = []
        for cell in row.findall(f"{XLSX_NS}c"):
            match = re.match(r"([A-Z]+)", cell.get("r", ""))
            if not match:
                continue
            col = 0
            for char in match.group(1):
                col = col * 26 + ord(char) - ord("A") + 1
            values.extend([""] * (col - len(values) - 1))
            kind = cell.get("t")
            value = cell.findtext(f"{XLSX_NS}v", default="")
            if kind == "s" and value:
                value = shared[int(value)]
            elif kind == "inlineStr":
                value = "".join(cell.itertext())
            values.append(str(value).strip())
        rows.append(values)
    return rows


def raw_file(kind, year):
    for suffix in (".xls", ".xlsx"):
        path = RAW / f"创客大赛_{kind}项目获奖名单_{year}{suffix}"
        if path.exists():
            return path
    raise FileNotFoundError(f"缺少 {year} 年{kind}项目获奖名单")


def header_table(rows):
    """教育局附件的标题行数和列顺序会变，按列名读取而不依赖固定列号。"""
    header_index = next(i for i, row in enumerate(rows) if "参赛学校" in row or "学校/单位名称" in row)
    headers = {name: index for index, name in enumerate(rows[header_index]) if name}

    def value(row, *names):
        for name in names:
            index = headers.get(name)
            if index is not None and index < len(row):
                return row[index]
        return ""

    return rows[header_index + 1:], value


def match_school(school, stage, matcher):
    stage_names = ("小学",) if stage == "primary" else ("初中", "高中")
    adcode = None
    for dname, adcode in DISTRICT_ADCODE.items():
        if dname in school:
            break
    else:
        adcode = None
    hits = []
    for stage_name in stage_names:
        hits.extend(matcher.resolve(
            school, preferred_adcode=adcode, preferred_stage=stage_name, strategy="all"
        ))
    return sorted({hit["school_id"] for hit in hits if hit.get("school_id")})


def parse_personal(year, ents):
    rows, value = header_table(workbook_rows(raw_file("个人", year)))
    records = []
    for row in rows:
        school = value(row, "参赛学校", "学校/单位名称")
        if not school:
            continue
        records.append({
            "school": school, "student": value(row, "参赛选手", "学生姓名"), "project": value(row, "作品名称", "项目名称", "参赛项目"),
            "group": value(row, "组别", "参赛组别"), "coach": value(row, "指导教师", "指导老师"), "award": value(row, "获奖等级", "奖项"), "type": "personal",
        })
    return records


def parse_team(year, ents):
    rows, value = header_table(workbook_rows(raw_file("团体", year)))
    records = []
    for row in rows:
        school = value(row, "参赛学校", "学校/单位名称")
        if not school:
            continue
        records.append({
            "school": school, "student": value(row, "参赛选手", "学生姓名"), "project": value(row, "作品名称", "项目名称", "参赛项目") or "团体赛",
            "group": value(row, "组别", "参赛组别"), "coach": value(row, "指导教师", "指导老师"), "award": value(row, "获奖等级", "奖项"), "type": "team",
        })
    return records


def main():
    ents = json.load(open(ENTITIES))["entities"]
    matcher = SchoolMatcher.load(
        poi_paths=[
            (ROOT / "data/poi/dist/primary_poi.json", "小学"),
            (ROOT / "data/poi/dist/middle_poi.json", "初中"),
            (ROOT / "data/poi/dist/high_poi.json", "高中"),
        ],
        entities_path=ENTITIES,
    )
    years = sorted(set(
        re.search(r"(\d{4})", p.name).group(1)
        for p in RAW.glob("创客大赛_*获奖名单_*.*") if p.suffix.lower() in {".xls", ".xlsx"}
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
            stage = "primary" if rec["group"].startswith("小学组") else "secondary" if rec["group"].startswith("中学组") else None
            if not stage:
                skipped.append({**rec, "reason": f"未知组别:{rec['group']}"})
                continue
            sids = match_school(rec["school"], stage, matcher)
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
