#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广州市中小学生科技体育教育竞赛获奖名单解析（raw → parsed → dist），覆盖 2024—2026。

输入（raw/）：
  - 2024 科技体育模型系列教育竞赛决赛获奖名单（附件1-5.xlsx，航海/建筑/车辆/智能交通/航空模型）
    列：序号/姓名/参赛学校/区属/指导老师/组别/奖项/项目
    注：表尾混入“优秀指导老师”“优秀裁判员（工作人员）”行（组别列为“/”），需过滤
  - 2025 科技体育教育竞赛市级总决赛参赛队员获奖公示名单（附件1.xlsx）
    列：序号/参赛者/参赛单位/所属区/指导老师/参赛组别/等次/参赛项目
  - 2026 科技体育教育竞赛市级总决赛参赛学生获奖公示名单（科技体育_学生获奖名单.xlsx）
    列：序号/参赛者/参赛单位/所属区/指导老师/参赛组别/获奖/参赛项目

组别与学段映射：
  - 小学组 / 小学组团队 / 小学男子组 / 小学女子组 / M10 / W10 / M12 / W12 → primary
  - 中学组 / 中学组团队 / 中学男子组 / 中学女子组 / M15 / W15 → secondary（初中+高中，不擅自拆分）
  - M18 / W18 → high（测向 18 岁组）
  - 综合组 / 综合组团队 → 展演/挑战赛项目，学段混合无法判定 → 跳过匹配（记录留 parsed 的 skipped）

规则：
  - 名单学段确定 → 只挂对应 stage 的 school_id
  - 带括号校区名 → 精确匹配该校区
  - 整体名 → 一对多，该学校所有同学段校区
  - 区码校验：名单有“所属区/区属”列，school_id adcode 与官方区属一致（市属/省属无区码，靠名称匹配）
  - 少年宫/青少年宫等非学校排除
  - 归属统一走 SchoolMatcher，宁缺毋滥（未命中 school_ids 留空，不进 dist）

输出：
  - parsed/tech_sports_2024.json / tech_sports_2025.json / tech_sports_2026.json  完整记录（含未命中记录）
  - dist/compiled.json  三年聚合（school_id → tech_sports_awards，stages[stage][year] 计数）
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
ENTITIES = ROOT / "data/registry/entity/dist/entities.json"

sys.path.insert(0, str(ROOT / "data" / "registry" / "entity" / "scripts"))
from school_match import SchoolMatcher

DISTRICT_ADCODE = {"荔湾": "440103", "越秀": "440104", "海珠": "440105", "天河": "440106",
                   "白云": "440111", "黄埔": "440112", "番禺": "440113", "花都": "440114",
                   "南沙": "440115", "从化": "440117", "增城": "440118"}
GROUP_STAGE = {
    "小学组": "primary", "小学组团队": "primary",
    "小学男子组": "primary", "小学女子组": "primary",
    "中学组": "secondary", "中学组团队": "secondary",
    "中学男子组": "secondary", "中学女子组": "secondary",
    "M10": "primary", "W10": "primary", "M12": "primary", "W12": "primary",
    "M15": "secondary", "W15": "secondary",
    "M18": "high", "W18": "high",
}
NON_SCHOOL = ["少年宫", "青少年宫"]
XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

YEARS = {
    2024: {
        "competition": "广州市中小学生科技体育模型系列教育竞赛",
        "pattern": "附件*：2024年*.xlsx",
        "columns": {
            "school": ("参赛学校",), "district": ("区属",), "group": ("组别",),
            "award": ("奖项",), "student": ("姓名",), "coach": ("指导老师",), "project": ("项目",),
        },
    },
    2025: {
        "competition": "广州市中小学生科技体育教育竞赛",
        "pattern": "附件1：2025年*.xlsx",
        "columns": {
            "school": ("参赛单位",), "district": ("所属区",), "group": ("参赛组别",),
            "award": ("等次",), "student": ("参赛者",), "coach": ("指导老师",), "project": ("参赛项目",),
        },
    },
    2026: {
        "competition": "广州市中小学生科技体育教育竞赛",
        "pattern": "科技体育_学生获奖名单.*",
        "columns": {
            "school": ("参赛单位",), "district": ("所属区",), "group": ("参赛组别",),
            "award": ("获奖",), "student": ("参赛者",), "coach": ("指导老师",), "project": ("参赛项目",),
        },
    },
}


def workbook_rows(path):
    """返回首个工作表的稀疏补齐行；与其它竞赛脚本共用同一套 xlsx 解析。"""
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


def header_table(rows, columns):
    """按列名读取，不依赖固定列号（前两行为标题行）。"""
    header_index = next(i for i, row in enumerate(rows) if any(c in row for c in columns["school"]))
    headers = {name: index for index, name in enumerate(rows[header_index]) if name}

    def value(row, names):
        for name in names:
            index = headers.get(name)
            if index is not None and index < len(row):
                return row[index]
        return ""

    return rows[header_index + 1:], value


def match_school(school, stage, adcode, matcher):
    """stage: primary → 小学；secondary → 初中+高中；high → 高中。"""
    stage_names = {"primary": ("小学",), "secondary": ("初中", "高中"), "high": ("高中",)}[stage]
    hits = []
    for stage_name in stage_names:
        hits.extend(matcher.resolve(
            school, preferred_adcode=adcode, preferred_stage=stage_name, strategy="all"
        ))
    return sorted({hit["school_id"] for hit in hits if hit.get("school_id")})


def parse_year(year, matcher, compiled):
    spec = YEARS[year]
    sources = sorted(RAW.glob(spec["pattern"]))
    if not sources:
        raise FileNotFoundError(f"[{year}] 缺少获奖名单文件（{RAW}）")
    columns = spec["columns"]
    records, skipped = [], []

    def value_of(row, name):
        return value(row, columns[name])

    for source in sources:
        rows, value = header_table(workbook_rows(source), columns)
        for row in rows:
            school = value_of(row, "school")
            if not school:
                continue
            group = value_of(row, "group")
            district = value_of(row, "district")
            record = {
                "project": value_of(row, "project"), "district": district, "school": school,
                "group": group, "student": value_of(row, "student"),
                "coach": value_of(row, "coach"), "award": value_of(row, "award"),
                "type": "team" if "团队" in (group or "") else "personal",
            }
            if any(word in school for word in NON_SCHOOL):
                skipped.append({**record, "reason": "非学校"})
                continue
            stage = GROUP_STAGE.get(group)
            if not stage:
                if group in ("/", ""):
                    skipped.append({**record, "reason": "非学生（教师/裁判行）"})
                else:
                    skipped.append({**record, "reason": f"组别学段混合无法判定:{group}"})
                continue
            adcode = DISTRICT_ADCODE.get((district or "").replace("区", ""))
            sids = match_school(school, stage, adcode, matcher)
            record["school_ids"] = sids
            record["stage"] = stage
            records.append(record)
            medal = {"一等": "gold", "二等": "silver", "三等": "bronze"}.get((record["award"] or "")[:2])
            if medal:
                for sid in sids:
                    compiled.setdefault(sid, {"stages": {}})
                    compiled[sid]["stages"].setdefault(stage, {}).setdefault(
                        str(year), {"gold": 0, "silver": 0, "bronze": 0}
                    )[medal] += 1

    parsed = {
        "metric": "tech_sports_awards", "competition": spec["competition"],
        "year": year, "source_file": ", ".join(s.name for s in sources),
        "total_records": len(records), "skipped": skipped, "records": records,
        "compiled_schools": len({sid for r in records for sid in r["school_ids"]}),
    }
    PARSED.mkdir(exist_ok=True)
    (PARSED / f"tech_sports_{year}.json").write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    matched = sum(bool(r["school_ids"]) for r in records)
    print(f"[{year}] records={len(records)} matched={matched} skipped={len(skipped)}")
    return records


def main():
    matcher = SchoolMatcher.load()
    compiled = {}
    total_records = total_matched = 0
    for year in sorted(YEARS):
        records = parse_year(year, matcher, compiled)
        total_records += len(records)
        total_matched += sum(bool(r["school_ids"]) for r in records)

    DIST.mkdir(exist_ok=True)
    (DIST / "compiled.json").write_text(
        json.dumps({sid: {"tech_sports_awards": data} for sid, data in compiled.items()},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[total] records={total_records} matched={total_matched} "
          f"compiled_schools={len(compiled)}")


if __name__ == "__main__":
    main()
