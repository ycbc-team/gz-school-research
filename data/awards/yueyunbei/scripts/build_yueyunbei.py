#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""粤韵杯湾区中小学生文学/艺术素养大赛获奖名单解析（raw → parsed → dist），覆盖 2024—2026。

输入：raw/ 下各年度 docx 附件（Word 表格）
  - 学生获奖名单：文件名含“获奖名单”且不含“指导老师/组织/人气”（2024：作文/美术；2025：作文/绘画/
    书法篆刻/非遗工艺/非遗艺术展演/阅读；2026：作文/阅读/绘画/书法篆刻/工艺美术/舞台创编/歌唱/舞蹈/语言艺术）
  - 教师（优秀指导老师）、组织（最佳组织单位/奖）、人气奖附件不采，跳过

列（各年小差异，按列名取值）：
  序号/学生姓名(姓名)/学校名称（全称）(学校名称/学校)/指导老师/参赛组别(组别)/奖项/类别(参赛类别)/证书编号

组别与学段映射：
  - 小学组三四年级 / 小学三四年级组 / 小学组五六年级 / 小学五六年级组 → primary
  - 初中组 → middle
  - 高中组 / 高中组（含高中、中专、职中）→ high

规则：
  - 湾区外市（佛山市/东莞市/深圳市/惠州市/珠海市/肇庆市/江门市/中山市/顺德区/香港/澳门 开头的学校）跳过；
    “中山大学”等广州市内校名不受影响
  - 奖项一等/二等/三等奖 → gold/silver/bronze；优胜奖记录保留但不进 dist 计数
  - 名单无区属列 → 靠 SchoolMatcher 名称 + 学段匹配，宁缺毋滥
  - 少年宫/青少年宫等非学校排除

输出：
  - parsed/yueyunbei_2024.json / 2025 / 2026  完整记录（含未命中与跳过）
  - dist/compiled.json  三年聚合（school_id → yueyunbei_awards）
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

sys.path.insert(0, str(ROOT / "data" / "registry" / "entity" / "scripts"))
from school_match import SchoolMatcher

XLSX_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
STAGE_NAMES = {"primary": "小学", "middle": "初中", "high": "高中"}
# 组别因年份/类别而异（作文分三四/五六年级组，绘画分低/高年级或一二三/四五六年级组，
# 阅读用“小学一至六年级组”+“中学组”），统一按学段关键词判定
def group_stage(group):
    g = (group or "").replace("（", "(").replace("）", ")")
    if "幼儿" in g:
        return None, "幼儿组（非中小学）"
    if "小学" in g:
        return "primary", None
    if "初中" in g:
        return "middle", None
    if "高中" in g:
        return "high", None
    if g == "中学组":
        return "middle", None
    return None, f"组别无法映射:{group}"
OUTSIDE_CITY = re.compile(
    r"^(佛山市|东莞市|深圳市|惠州市|珠海市|肇庆市|江门市|中山市|顺德区|香港|澳门)")
NON_SCHOOL = ["少年宫", "青少年宫"]
CATEGORY_KEYWORDS = [
    "非遗艺术展演", "非遗工艺", "书法篆刻", "语言艺术", "工艺美术", "舞台创编",
    "作文", "阅读", "绘画", "歌唱", "舞蹈", "美术",
]


def docx_tables(path):
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    tables = []
    for tbl in root.iter(f"{XLSX_NS}tbl"):
        rows = []
        for tr in tbl.findall(f"{XLSX_NS}tr"):
            rows.append(["".join(tc.itertext()).strip().replace("\n", " ")
                         for tc in tr.findall(f"{XLSX_NS}tc")])
        tables.append(rows)
    return tables


def category_of(filename):
    for keyword in CATEGORY_KEYWORDS:
        if keyword in filename:
            return keyword
    return "其他"


def parse_docx(path, year, matcher, compiled):
    rows = None
    for table in docx_tables(path):
        if table and any("学校" in cell for row in table[:3] for cell in row):
            rows = table
            break
    if rows is None:
        return [], 0
    headers = {name: index for index, name in enumerate(rows[0]) if name}

    def value(row, *names):
        for name in names:
            index = headers.get(name)
            if index is not None and index < len(row):
                return row[index]
        return ""

    records, skipped = [], []
    category = category_of(Path(path).name)
    for row in rows[1:]:
        school = value(row, "学校名称（全称）", "学校名称", "学校")
        if not school:
            continue
        group = value(row, "参赛组别", "组别")
        record = {
            "project": category, "category": category, "school": school,
            "group": group, "student": value(row, "学生姓名", "姓名"),
            "coach": value(row, "指导老师"), "award": value(row, "奖项"),
            "type": "personal",
        }
        if any(word in school for word in NON_SCHOOL):
            skipped.append({**record, "reason": "非学校"})
            continue
        if OUTSIDE_CITY.match(school):
            skipped.append({**record, "reason": "湾区外市"})
            continue
        stage, stage_reason = group_stage(group)
        if not stage:
            skipped.append({**record, "reason": stage_reason})
            continue
        sids = sorted({hit["school_id"] for hit in matcher.resolve(
            school, preferred_stage=STAGE_NAMES[stage], strategy="all") if hit.get("school_id")})
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
    return records, skipped


def main():
    matcher = SchoolMatcher.load()
    compiled = {}
    total_records = total_matched = 0
    for year in (2024, 2025, 2026):
        if year == 2024:
            # 2024 附件文件名不含年份（如“附件1：粤韵杯作文大赛获奖名单.docx”）
            sources = sorted(p for p in RAW.glob("附件*.docx")
                             if "获奖名单" in p.name and "指导" not in p.name
                             and "组织" not in p.name and "人气" not in p.name
                             and not re.search(r"202[56]", p.name))
        else:
            sources = sorted(RAW.glob(f"附件*：*{year}*获奖名单.docx"))
        records, skipped_all = [], []
        for source in sources:
            recs, skips = parse_docx(source, year, matcher, compiled)
            records.extend(recs)
            skipped_all.extend(skips)
            print(f"  [{year}] {source.name[:34]}… recs={len(recs)}")
        parsed = {
            "metric": "yueyunbei_awards", "competition": "粤韵杯湾区中小学生文学与艺术素养大赛",
            "year": year, "source_file": ", ".join(s.name for s in sources),
            "total_records": len(records), "skipped": skipped_all, "records": records,
            "compiled_schools": len({sid for r in records for sid in r["school_ids"]}),
        }
        PARSED.mkdir(exist_ok=True)
        (PARSED / f"yueyunbei_{year}.json").write_text(
            json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        matched = sum(bool(r["school_ids"]) for r in records)
        total_records += len(records)
        total_matched += matched
        print(f"[{year}] records={len(records)} matched={matched} skipped={len(skipped_all)}")

    DIST.mkdir(exist_ok=True)
    (DIST / "compiled.json").write_text(
        json.dumps({sid: {"yueyunbei_awards": data} for sid, data in compiled.items()},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[total] records={total_records} matched={total_matched} "
          f"compiled_schools={len(compiled)}")


if __name__ == "__main__":
    main()
