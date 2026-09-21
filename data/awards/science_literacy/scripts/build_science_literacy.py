#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广州市中小学生科学素养大赛获奖名单解析（xlsx → parsed → dist）。"""
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent.parent / "raw"
PARSED = Path(__file__).resolve().parent.parent / "parsed"
DIST = Path(__file__).resolve().parent.parent / "dist"
ENTITIES = ROOT / "data/registry/entities.json"
sys.path.insert(0, str(ROOT / "scripts" / "registry"))
from school_match import SchoolMatcher

XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DISTRICT_ADCODE = {"荔湾": "440103", "越秀": "440104", "海珠": "440105", "天河": "440106",
                   "白云": "440111", "黄埔": "440112", "番禺": "440113", "花都": "440114",
                   "南沙": "440115", "从化": "440117", "增城": "440118"}
STAGE_MAP = {"小学组": "primary", "初中组": "middle", "高中组": "high"}
MEDAL_MAP = {"一等奖": "gold", "二等奖": "silver", "三等奖": "bronze"}
NON_SCHOOL = ("少年宫", "青少年宫")


def workbook_rows(path):
    if path.suffix.lower() == ".xls":
        import xlrd
        sheet = xlrd.open_workbook(str(path)).sheet_by_index(0)
        return [[str(cell.value).strip() for cell in row] for row in sheet.get_rows()]
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
            value = cell.findtext(f"{XLSX_NS}v", default="")
            if cell.get("t") == "s" and value:
                value = shared[int(value)]
            elif cell.get("t") == "inlineStr":
                value = "".join(cell.itertext())
            values.append(str(value).strip())
        rows.append(values)
    return rows


def parse_year(year, sources, matcher):
    records, skipped, compiled = [], [], {}
    category_by_attachment = {"1": "科学探究", "2": "科学家精神", "3": "科技展演", "4": "科普讲解", "5": "信息科技素养"}

    for source in sources:
        rows = workbook_rows(source)
        normalized_rows = [[re.sub(r"\s+", "", str(value)) for value in row] for row in rows]
        header_index = next(i for i, row in enumerate(normalized_rows) if "学校/单位名称" in row)
        headers = {name: i for i, name in enumerate(normalized_rows[header_index]) if name}
        attachment = re.search(r"附件([1-5])", source.name)
        fallback_category = category_by_attachment.get(attachment.group(1)) if attachment else ""

        def value(row, *names):
            for name in names:
                i = headers.get(re.sub(r"\s+", "", name))
                if i is not None and i < len(row):
                    return row[i]
            return ""

        for row in normalized_rows[header_index + 1:]:
            school = value(row, "学校/单位名称")
            if not school:
                continue
            group = value(row, "参赛组别")
            stage = STAGE_MAP.get(group)
            record = {"category": value(row, "参赛项目") or fallback_category, "district": value(row, "属地"),
                      "school": school, "group": group, "student": value(row, "学生姓名"),
                      "coach": value(row, "指导老师"), "award": value(row, "获奖等级", "奖项")}
            if any(word in school for word in NON_SCHOOL):
                skipped.append({**record, "reason": "非学校"})
                continue
            if not stage:
                skipped.append({**record, "reason": f"未知组别:{group}"})
                continue
            adcode = DISTRICT_ADCODE.get(record["district"].replace("区", ""))
            names = [name.strip() for name in re.split(r"[、,，\n]+", school) if name.strip()]
            hits = []
            for name in names:
                hits.extend(matcher.resolve(name, preferred_adcode=adcode, preferred_stage=group[:2], strategy="all"))
            record["school_ids"] = sorted({hit["school_id"] for hit in hits if hit.get("school_id")})
            record["stage"] = stage
            records.append(record)
            medal = MEDAL_MAP.get(record["award"])
            if medal:
                for sid in record["school_ids"]:
                    compiled.setdefault(sid, {"stages": {}})
                    compiled[sid]["stages"].setdefault(stage, {}).setdefault(
                        str(year), {"gold": 0, "silver": 0, "bronze": 0}
                    )[medal] += 1
    return records, skipped, compiled


def main():
    matcher = SchoolMatcher.load(
        poi_paths=[
            (ROOT / "data/poi/dist/primary_poi.json", "小学"),
            (ROOT / "data/poi/dist/middle_poi.json", "初中"),
            (ROOT / "data/poi/dist/high_poi.json", "高中"),
        ], entities_path=ENTITIES,
    )
    sources_by_year = {
        2024: sorted(RAW.glob("2024_附件[1-5]*.xls")),
        2025: [next(RAW.glob("附件1 *科学素养大赛*获奖*名单.xlsx"), None)],
    }
    all_compiled = {}
    for year, sources in sources_by_year.items():
        sources = [source for source in sources if source is not None]
        if not sources:
            raise FileNotFoundError(f"缺少 {year} 年科学素养大赛学生获奖名单")
        records, skipped, compiled = parse_year(year, sources, matcher)
        parsed = {"metric": "science_literacy_awards", "competition": "广州市中小学生科学素养大赛",
                  "year": year, "source_file": [source.name for source in sources],
                  "total_records": len(records), "skipped": skipped, "records": records,
                  "compiled_schools": len(compiled)}
        PARSED.mkdir(exist_ok=True)
        (PARSED / f"science_literacy_{year}.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for sid, data in compiled.items():
            target = all_compiled.setdefault(sid, {"stages": {}})
            for stage, years in data["stages"].items():
                target["stages"].setdefault(stage, {}).update(years)
        print(f"[{year}] records={len(records)} matched={sum(bool(r['school_ids']) for r in records)} skipped={len(skipped)} schools={len(compiled)}")

    DIST.mkdir(exist_ok=True)
    (DIST / "compiled.json").write_text(json.dumps({sid: {"science_literacy_awards": data} for sid, data in all_compiled.items()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
