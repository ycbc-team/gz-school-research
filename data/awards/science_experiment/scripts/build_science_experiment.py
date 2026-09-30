#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广州市中小学科学实验大赛获奖名单解析（raw → parsed → dist），2025 首届。

输入：raw/附件1：2025年广州市中小学科学实验大赛公布名单.xls
列：序号/证书编号/学校/学生姓名/参赛组别/类别/学科/作品名称/指导老师/获奖等级

组别与学段映射：
  - 小学组 → primary
  - 初中组 → middle
  - 高中组 → high

规则：
  - 名单学段确定 → 只挂对应 stage 的 school_id
  - 带括号校区名 → 精确匹配该校区；整体名 → 一对多
  - 名单无区属列 → 无区码校验，靠 SchoolMatcher 名称匹配
  - 少年宫/青少年宫等非学校排除
  - 归属统一走 SchoolMatcher，宁缺毋滥（未命中 school_ids 留空，不进 dist）

输出：
  - parsed/science_experiment_2025.json  完整记录（含未命中记录）
  - dist/compiled.json                   聚合（school_id → science_experiment_awards）
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent.parent / "raw"
PARSED = Path(__file__).resolve().parent.parent / "parsed"
DIST = Path(__file__).resolve().parent.parent / "dist"

sys.path.insert(0, str(ROOT / "data" / "registry" / "entity" / "scripts"))
from school_match import SchoolMatcher

STAGE_NAMES = {"primary": "小学", "middle": "初中", "high": "高中"}
GROUP_STAGE = {"小学组": "primary", "初中组": "middle", "高中组": "high"}
NON_SCHOOL = ["少年宫", "青少年宫"]


def read_xls(path):
    import xlrd
    sh = xlrd.open_workbook(str(path)).sheet_by_index(0)
    rows = []
    for i in range(sh.nrows):
        rows.append([str(sh.cell_value(i, c)).strip() for c in range(sh.ncols)])
    return rows


def main():
    source = next(RAW.glob("附件1：2025年*.xls"), None)
    if source is None:
        raise FileNotFoundError(f"缺少 2025 公布名单（{RAW}）")
    matcher = SchoolMatcher.load()

    rows = read_xls(source)
    header_index = next(i for i, row in enumerate(rows)
                        if any("学校" in cell for cell in row) and any("序号" in cell for cell in row))
    headers = {name: index for index, name in enumerate(rows[header_index]) if name}

    def value(row, *names):
        for name in names:
            index = headers.get(name)
            if index is not None and index < len(row):
                return row[index]
        return ""

    records, skipped = [], []
    compiled = {}
    for row in rows[header_index + 1:]:
        school = value(row, "学校/单位名称", "学校")
        if not school:
            continue
        group = value(row, "参赛\n组别", "参赛组别")
        record = {
            "project": value(row, "作品名称"), "category": value(row, "类别"),
            "subject": value(row, "学科"), "school": school, "group": group,
            "student": value(row, "学生姓名"), "coach": value(row, "指导老师"),
            "award": value(row, "获奖等级"), "type": "personal",
        }
        if any(word in school for word in NON_SCHOOL):
            skipped.append({**record, "reason": "非学校"})
            continue
        stage = GROUP_STAGE.get(group)
        if not stage:
            skipped.append({**record, "reason": f"组别无法映射:{group}"})
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
                    "2025", {"gold": 0, "silver": 0, "bronze": 0}
                )[medal] += 1

    parsed = {
        "metric": "science_experiment_awards", "competition": "广州市中小学科学实验大赛",
        "year": 2025, "source_file": source.name,
        "total_records": len(records), "skipped": skipped, "records": records,
        "compiled_schools": len(compiled),
    }
    PARSED.mkdir(exist_ok=True)
    (PARSED / "science_experiment_2025.json").write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DIST.mkdir(exist_ok=True)
    (DIST / "compiled.json").write_text(
        json.dumps({sid: {"science_experiment_awards": data} for sid, data in compiled.items()},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    matched = sum(bool(r["school_ids"]) for r in records)
    print(f"[2025] records={len(records)} matched={matched} skipped={len(skipped)} "
          f"compiled_schools={len(compiled)}")


if __name__ == "__main__":
    main()
