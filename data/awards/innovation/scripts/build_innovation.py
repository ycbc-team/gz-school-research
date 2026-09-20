#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广州市中小学生创新大赛初中金种子组获奖名单解析（raw → parsed → dist）。

输入：data/awards/raw/创新大赛_初中金种子组获奖名单.xls
规则：
  - 名单本身即初中段，所有获奖学生均为初中生
  - 带括号校区名 → 精确匹配该校区 middle school_id
  - 整体名 → 一对多，该学校所有 middle 校区 school_id 都挂
  - 排除少年宫/青少年宫（非学校）
  - 区码校验：school_id adcode 必须与官方区属一致
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
# 品牌成员校后缀（独立法人，不是本校校区，收窄排除）
BRAND_SUFFIX = ["附属学校", "附属实验", "实验学校", "附属小学", "附属中学", "外国语学校"]


def core_name(s):
    """提取学校核心名：去市/区前缀、去括号、去空白。"""
    s = s.replace("（", "(").replace("）", ")").replace(" ", "").strip()
    paren = re.search(r"[（(](.+?)[)）]", s)
    campus = paren.group(1) if paren else ""
    s = re.sub(r"[（(].*?[)）]", "", s)
    s = re.sub(r"^广州市", "", s)
    for d in DISTRICT_ADCODE:
        s = re.sub(r"^" + d + r"区?", "", s)
    return s, campus


def main():
    import xlrd
    wb = xlrd.open_workbook(str(RAW / "创新大赛_初中金种子组获奖名单.xls"))
    sh = wb.sheet_by_index(0)
    rows = []
    for r in range(3, sh.nrows):
        row = [str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
        if not row[3]: continue
        rows.append({"school": row[3], "award": row[7], "district": row[8],
                     "project": row[2], "leader": row[4], "members": row[5], "coach": row[6]})

    ents = json.load(open(ENTITIES))["entities"]

    matched_records = []
    skipped = []
    for rec in rows:
        school = rec["school"]
        if any(kw in school for kw in NON_SCHOOL):
            skipped.append({"school": school, "reason": "非学校（少年宫/青少年宫）"})
            continue
        for sname in re.split(r"[\n\r]+", school):
            sname = sname.strip()
            if not sname: continue
            core, campus = core_name(sname)
            expect_adcode = DISTRICT_ADCODE.get(rec["district"].replace("区", ""))

            # 候选：stage=middle，name 含 core 或反向
            cands = [e for e in ents if e["stage"] == "middle" and (core in e["name"] or e["name"] in core)]
            # 区码收窄：官方 district → adcode 必须一致
            if expect_adcode:
                cands = [e for e in cands if e["school_id"].split("-")[1] == expect_adcode]
            # 品牌成员校收窄：排除含后缀的独立法人，但 core 本身含后缀时不排除（本校名）
            cands = [e for e in cands if not any(suf in e["name"] and suf not in core for suf in BRAND_SUFFIX)]
            # 带括号校区名优先
            if campus:
                cands = [e for e in cands if campus in e["name"]] or cands
            sids = sorted(set(e["school_id"] for e in cands))
            rec["school_ids"] = sids
            rec["match_type"] = "single" if len(sids) == 1 else ("multi" if len(sids) > 1 else "none")
            matched_records.append(rec)

    # 聚合到 school_id
    by_school = {}
    for rec in matched_records:
        if not rec["school_ids"]: continue
        medal = {"金": "gold", "银": "silver", "铜": "bronze"}[rec["award"][0]]
        for sid in rec["school_ids"]:
            by_school.setdefault(sid, {"gold": 0, "silver": 0, "bronze": 0})
            by_school[sid][medal] += 1

    compiled = {}
    for sid, c in by_school.items():
        compiled[sid] = {"innovation_awards": {
            "gold": c["gold"], "silver": c["silver"], "bronze": c["bronze"], "year": 2026
        }}

    out = {
        "metric": "innovation_awards",
        "competition": "广州市中小学生创新大赛·初中金种子组",
        "year": 2026,
        "source_file": "创新大赛_初中金种子组获奖名单.xls",
        "total_records": len(rows),
        "skipped": skipped,
        "records": matched_records,
        "compiled_schools": len(compiled),
    }
    PARSED.mkdir(exist_ok=True)
    (PARSED / "innovation_2026.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    DIST.mkdir(exist_ok=True)
    (DIST / "compiled_2026.json").write_text(json.dumps(compiled, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"records={len(rows)} compiled_schools={len(compiled)} skipped={len(skipped)}")
    no_match = [r["school"] for r in matched_records if not r["school_ids"]]
    print("未匹配:", no_match)
    multi = [(r["school"], len(r["school_ids"])) for r in matched_records if len(r["school_ids"]) > 1]
    print("一对多:", multi)


if __name__ == "__main__":
    main()
