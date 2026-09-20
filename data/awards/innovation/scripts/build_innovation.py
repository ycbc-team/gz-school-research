#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广州市中小学生创新大赛获奖名单解析（raw → parsed → dist）。

三学段：小学金点子组 / 初中金种子组 / 高中金苗子组，每年一个文件。
规则：
  - 名单学段确定 → 只挂对应 stage 的 school_id
  - 带括号校区名 → 精确匹配该校区
  - 整体名 → 一对多，该学校所有同学段校区
  - 排除少年宫/青少年宫（非学校）
  - 区码收窄：school_id adcode 与官方区属一致（2026 小学/高中无区属列，跳过）
  - 品牌成员校（独立法人）排除
输出：
  - parsed/innovation_{stage}_{year}.json  每年每学段完整记录
  - dist/compiled.json                     聚合所有学段所有年份
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

STAGE_MAP = {"小学": "primary", "初中": "middle", "高中": "high"}
GROUP_MAP = {"小学": "金点子组", "初中": "金种子组", "高中": "金苗子组"}


def core_name(s):
    s = s.replace("（", "(").replace("）", ")").replace(" ", "").strip()
    paren = re.search(r"[（(](.+?)[)）]", s)
    campus = paren.group(1) if paren else ""
    s = re.sub(r"[（(].*?[)）]", "", s)
    s = re.sub(r"^广州市", "", s)
    for d in DISTRICT_ADCODE:
        s = re.sub(r"^" + d + r"区?", "", s)
    return s, campus


def get_cols(stage, year, sh):
    """按年份+学段返回列映射和表头行号。"""
    if year == 2024:
        # col1=成员, col2=负责人, col3=单位, col4=指导老师, col5=奖次, col6=项目, col7=区属
        return {"project": 6, "school": 3, "leader": 2, "members": 1, "coach": 4, "award": 5, "district": 7}, 3
    if year == 2025:
        # col2=项目, col3=负责人, col4=成员, col5=单位, col6=指导老师, col7=区属, col8=奖项
        return {"project": 2, "school": 5, "leader": 3, "members": 4, "coach": 6, "award": 8, "district": 7}, 2
    if year == 2026:
        if stage == "初中":
            # col2=项目, col3=学校, col4=负责人, col5=成员, col6=指导老师, col7=奖项, col8=区属
            return {"project": 2, "school": 3, "leader": 4, "members": 5, "coach": 6, "award": 7, "district": 8}, 3
        else:
            # 小学/高中：col2=学校, col3=项目, col4=指导老师, col5=获奖等级, col7=负责人, col8=成员，无区属
            return {"project": 3, "school": 2, "leader": 7, "members": 8, "coach": 4, "award": 5, "district": -1}, 2


def parse_file(xls_path, stage_cn, ents):
    year = int(xls_path.stem.split("_")[-1])
    stage = STAGE_MAP[stage_cn]
    import xlrd
    wb = xlrd.open_workbook(str(xls_path))
    sh = wb.sheet_by_index(0)
    COLS, header_row = get_cols(stage_cn, year, sh)

    rows = []
    for r in range(header_row, sh.nrows):
        row = [str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
        if not row[COLS["school"]]: continue
        district = row[COLS["district"]] if COLS["district"] >= 0 else ""
        rows.append({"school": row[COLS["school"]], "award": row[COLS["award"]], "district": district,
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
            expect_adcode = DISTRICT_ADCODE.get(rec["district"].replace("区", "")) if rec["district"] else None
            cands = [e for e in ents if e["stage"] == stage and (core in e["name"] or e["name"] in core)]
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
        "competition": f"广州市中小学生创新大赛·{stage_cn}{GROUP_MAP[stage_cn]}",
        "stage": stage,
        "year": year,
        "source_file": xls_path.name,
        "total_records": len(rows),
        "skipped": skipped,
        "records": matched_records,
        "compiled_schools": len(by_school),
    }
    PARSED.mkdir(exist_ok=True)
    (PARSED / f"innovation_{stage}_{year}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{stage_cn} {year}] records={len(rows)} schools={len(by_school)} skipped={len(skipped)}")
    return by_school, year, stage


def main():
    ents = json.load(open(ENTITIES))["entities"]
    all_schools = {}
    for xls in sorted(RAW.glob("创新大赛_*组获奖名单_*.xls")):
        m = re.match(r"创新大赛_(小学|初中|高中)(金点子|金种子|金苗子)组获奖名单_(\d{4})", xls.name)
        stage_cn, _, year = m.group(1), m.group(2), m.group(3)
        by_school, yr, stage = parse_file(xls, stage_cn, ents)
        for sid, medals in by_school.items():
            all_schools.setdefault(sid, {"stages": {}})
            all_schools[sid]["stages"].setdefault(stage, {})[yr] = medals

    compiled = {}
    for sid, data in all_schools.items():
        compiled[sid] = {"innovation_awards": data}

    DIST.mkdir(exist_ok=True)
    (DIST / "compiled.json").write_text(json.dumps(compiled, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n聚合完成: {len(compiled)} 个 school_id")


if __name__ == "__main__":
    main()
