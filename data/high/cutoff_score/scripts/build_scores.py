#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析广州市招考办官方中考录取分数（HTML 表格）→ data/high/cutoff_score/dist/scores_{year}.json 真源。

与 fetch_scores.py 分拆（2026-09-20）：
- fetch_scores.py：下载官方 HTML 到 raw/，仅每年录取批次公布时手动跑一次，不进入 check。
- build_scores.py：解析 raw/ HTML → 匹配实体 → dist/scores_{year}.json。
  每次 `npm run check` 由 check_groups_drift 重跑本脚本并与入库产物比对，
  分数清单（by_school_id 匹配）有任何变化都会失败——防手改产物/解析漂移/实体表变化静默漏更。

覆盖批次：
- 第一批次（外语、艺术类）：广州外国语学校（统一计划）、广州市艺术中学等
- 第三批次（公办：户籍生/非户籍生/外区生；民办+中外合作：最低分数）
- 第四批次（公办：户籍生/非户籍生；民办+中外合作：最低分数）

事实表按 school_id 引用学校实体（data/registry/entity/dist/entities.json，dimension 表）：
  官方招生单位名 → 实体 name/aliases 全等匹配（norm 后）→ school_id。
  未命中（远郊 7 区外、中外合作办学项目、项目未收录学校/校区）落在 unmapped，
  保留官方原文，供后续扩展。

用法: python3 data/high/cutoff_score/scripts/build_scores.py [--out-dir DIR]
  --out-dir  产物输出目录（默认 dist/；check_groups_drift 重跑比对用）

输出:
  data/high/cutoff_score/dist/scores_2025.json  2025 年官方录取分数（真源）
  data/high/cutoff_score/dist/scores_2026.json  2026 年官方录取分数（真源）

解析约定：
- 民办/中外合作官方只发布「最低分数」（无户籍/非户籍之分），公费班为独立条目（名称含「（公费班）」）。
- 分数为 "--" 表示该类别无考生被录取，落 null。
- 综合高中、特长生、自主招生条目不纳入（综合高中非普通高中，特长生/自招为合成成绩非分数）。
"""
import json
import re
import sys
from pathlib import Path

# 官方页面清单（文件名/批次/标题/URL）由 fetch_scores.py 权威定义，本脚本只消费文件名
from fetch_scores import PAGES

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
RAW = ROOT / "data" / "high" / "cutoff_score" / "raw"
OUT = ROOT / "data" / "high" / "cutoff_score" / "dist"

# 统一匹配库：norm 本体收敛至 school_match.normName（原 norm_name 定义已删，规则与 build_entities/support 一致）
sys.path.insert(0, str(ROOT / "data" / "registry" / "entity" / "scripts"))
from school_match import normName as norm_name

def clean_html(h: str) -> str:
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
    return h


def cell_text(td: str) -> str:
    t = re.sub(r"<[^>]+>", "", td)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", "", t).strip()


def tables_of(h: str):
    return re.findall(r"<table[^>]*>(.*?)</table>", clean_html(h), re.S)


def parse_int(v):
    if v in ("", "--", "—", "None"):
        return None
    return int(v)


def classify(rows):
    """按表头关键字识别表格类型。rows: list[list[str]]（每个单元格文本）。"""
    for r in rows[:4]:
        joined = " ".join(r)
        if "学校名称" not in joined:
            continue
        if "英语最低分数要求" in joined or "户籍生末位考生分数" in joined:
            return "lang_art"
        if "外区生" in joined and "户籍生" in joined:
            return "public19"
        if "户籍生" in joined:
            return "public14"
        if "最低分数" in joined:
            return "private"
    return None


def data_rows(rows):
    """取数据行：跳过表头（首列非数字的行）。"""
    out = []
    for r in rows:
        cells = [cell_text(c) for c in r]
        if not cells or not cells[0]:
            continue
        if not re.fullmatch(r"\d+", cells[0]):
            continue
        out.append(cells)
    return out


def parse_public(cells, ncols):
    """公办表：序号 学校 性质 范围 [户籍生5] [非户籍生5] [外区生5]。"""
    if len(cells) < ncols:
        return None
    rec = {"nature": cells[2], "scope": cells[3]}
    rec["huji"] = parse_int(cells[4])
    rec["feihuji"] = parse_int(cells[9])
    if ncols >= 19:
        rec["waiqu"] = parse_int(cells[14])
    else:
        rec["waiqu"] = None
    return rec


def parse_private(cells):
    """民办/中外合作表：序号 学校 性质 范围 最低分 同分 末位志愿 末位分 末位同分。"""
    if len(cells) < 9:
        return None
    rec = {"nature": cells[2], "scope": cells[3]}
    rec["min_score"] = parse_int(cells[4])
    return rec


def parse_lang_art(cells):
    """外语艺术类：序号 学校 性质 范围 户籍生末位分 户籍生末位同分 非户籍生末位分 非户籍生末位同分 [英语要求] [专业要求]。"""
    if len(cells) < 8:
        return None
    rec = {"nature": cells[2], "scope": cells[3]}
    rec["huji_last"] = parse_int(cells[4])
    rec["feihuji_last"] = parse_int(cells[6])
    return rec


def clean_school_name(name: str) -> str:
    """去掉公费班/普通高中/统一计划等后缀，还原本体校名（校区/班型保留）。
    中外合作办学项目、港澳子弟班为独立招生计划，保留原名不聚合。"""
    n = name
    n = re.sub(r"（公费班）$", "", n)
    n = re.sub(r"（普通高中）$", "", n)
    n = re.sub(r"（统一计划）$", "", n)
    return n


def parse_file(fname: str, batch: int):
    h = (RAW / fname).read_text(encoding="utf-8", errors="replace")
    rows_out = []
    for tbl in tables_of(h):
        trs = re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S)
        row_cells = [re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S) for tr in trs]
        kind = classify(row_cells)
        if kind is None:
            continue
        # 第一批次只取「外语、艺术类」表；特长生/自主招生/中职三二分段等不纳入
        if batch == 1 and kind != "lang_art":
            continue
        for cells in data_rows(row_cells):
            raw_name = cells[1] if len(cells) > 1 else ""
            # 综合高中（职校试点）不属普通高中，跳过
            if "综合高中" in raw_name:
                continue
            if kind == "public19":
                rec = parse_public(cells, 19)
                if rec is None:
                    continue
                rec.update({"batch": batch, "kind": "public"})
            elif kind == "public14":
                rec = parse_public(cells, 14)
                if rec is None:
                    continue
                rec.update({"batch": batch, "kind": "public"})
            elif kind == "private":
                rec = parse_private(cells)
                if rec is None:
                    continue
                rec.update({"batch": batch, "kind": "private"})
            elif kind == "lang_art":
                rec = parse_lang_art(cells)
                if rec is None:
                    continue
                rec.update({"batch": batch, "kind": "lang_art"})
            else:
                continue
            gongfei = "（公费班）" in raw_name
            rec["name"] = clean_school_name(raw_name)
            rec["gongfei"] = gongfei
            rec["raw_name"] = raw_name
            rows_out.append(rec)
    return rows_out


def load_entity_index():
    """实体表（dimension）name/aliases → school_id（norm 全等，与 build_entities.py 同规则）。"""
    ents = json.loads((ROOT / "data" / "registry" / "entity" / "dist" / "entities.json").read_text(encoding="utf-8"))["entities"]
    idx = {}
    for e in ents:
        if e.get("stage") != "high":
            continue
        for k in [e["name"]] + e.get("aliases", []):
            idx.setdefault(norm_name(k), set()).add(e["school_id"])
    return idx


def build(year: int):
    records = []
    for batch, fname, _title, _url in PAGES[year]:
        recs = parse_file(fname, batch)
        records.extend(recs)
        print(f"  {year} batch{batch}: {len(recs)} 条")
    return records


def main():
    out_dir = OUT
    if "--out-dir" in sys.argv:
        out_dir = Path(sys.argv[sys.argv.index("--out-dir") + 1])
    idx = load_entity_index()
    for year in (2025, 2026):
        records = build(year)
        by_sid, unmapped = {}, []
        for r in records:
            ids = idx.get(norm_name(r["name"]), set())
            rec = {k: v for k, v in r.items() if k not in ("name", "raw_name")}
            if not ids:
                unmapped.append({"official_name": r["name"], "raw_name": r["raw_name"], **rec})
                continue
            for sid in sorted(ids):
                by_sid.setdefault(sid, []).append(
                    {"official_name": r["name"], **rec})
        payload = {
            "year": year,
            "title": f"{year}年广州市普通高中学校录取分数（官方发布）",
            "updated": "2026-09-11",
            "scope": ("广州市招考办发布的普通高中录取分数，覆盖第一批次（外语艺术类）/第三批次/第四批次；"
                      "民办与中外合作项目为最低分数口径；by_school_id 按学校实体（registry/entities.json）引用，"
                      "unmapped 为未收录实体（远郊/中外合作/新校）的官方原文"),
            "source": [
                {"batch": b, "title": t, "url": u}
                for b, _f, t, u in PAGES[year]
            ],
            "by_school_id": dict(sorted(by_sid.items())),
            "unmapped": unmapped,
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"scores_{year}.json"
        # 入库格式 = 1 空格缩进（与既有产物一致，保证重跑 == 入库的格式确定性）
        out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8")
        print(f"→ {out.name}: {len(by_sid)} 个实体校区, {len(unmapped)} 条未映射")


if __name__ == "__main__":
    main()
