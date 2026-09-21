#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""义务教育标准化学校名单解析（raw → parsed）。

输入：data/middle/details/raw/ 下政府原文
  - 穗教督〔2021/2022/2023/2024〕认定通知（HTML 名单表 / xls 附件）
  - 越教字〔2023〕26号 区级认定（PDF）
输出：data/middle/details/parsed/standardization.json
  - 全量名单（含小学），运行时按 stage 过滤初中段
  - 每条带 source_file / year / school_id（按 entities name+aliases 精确匹配，未命中标 null 进 src 人工校正）
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # gz_school_research/
RAW = Path(__file__).resolve().parent.parent / "raw"
PARSED = Path(__file__).resolve().parent.parent / "parsed"
ENTITIES = ROOT / "data/registry/entity/dist/entities.json"

# 初中学段（含九年制/完全中学/十二年制——都有初中段）
MIDDLE_TYPES = {"初中", "九年制", "九年一贯制", "完全中学", "十二年制", "十二年一贯制"}


class TableExtractor(HTMLParser):
    """从 HTML 抽所有表格为二维数组。"""
    def __init__(self):
        super().__init__()
        self.tables, self.rows, self.cur, self.in_cell = [], [], [], False
    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.cur = []
        elif tag in ("td", "th"): self.in_cell = True; self.buf = []
    def handle_endtag(self, tag):
        if tag == "tr":
            if self.cur: self.rows.append([c.strip() for c in self.cur])
            self.cur = []
        elif tag in ("td", "th"):
            self.cur.append("".join(self.buf)); self.in_cell = False
        elif tag == "table":
            if self.rows: self.tables.append(self.rows); self.rows = []
    def handle_data(self, data):
        if self.in_cell: self.buf.append(data)


def parse_html_list(path: Path, year: int, doc_label: str):
    h = path.read_text(encoding="utf-8", errors="ignore")
    p = TableExtractor(); p.feed(h)
    out = []
    for tb in p.tables:
        # 找含"学校名"或"学校"表头的表
        if not tb: continue
        head = "".join(tb[0])
        if not ("学校名" in head or "学校" in head): continue
        # 定位列
        cols = tb[0]
        def col(*keys):
            for i, c in enumerate(cols):
                if any(k in c for k in keys): return i
            return None
        i_region, i_name, i_type, i_own = col("区域", "区"), col("学校名", "学校"), col("学校类型", "类型"), col("公办", "办别")
        if i_name is None: continue
        for r in tb[1:]:
            if len(r) <= max(x for x in [i_region, i_name, i_type, i_own] if x is not None): continue
            name = r[i_name] if i_name is not None else ""
            if not name or name in ("学校名", "序号"): continue
            if not re.search(r"学校|中学|小学|实验", name): continue
            out.append({
                "name": name,
                "region": r[i_region] if i_region is not None and i_region < len(r) else "",
                "school_type": r[i_type] if i_type is not None and i_type < len(r) else "",
                "ownership": r[i_own] if i_own is not None and i_own < len(r) else "",
                "year": year, "doc": doc_label, "source_file": path.name,
            })
    return out


def parse_xls(path: Path, year: int, doc_label: str):
    import xlrd
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_index(0)
    rows = [[str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)] for r in range(sh.nrows)]
    out = []
    cols = rows[0]
    def col(*keys):
        for i, c in enumerate(cols):
            if any(k in c for k in keys): return i
        return None
    i_region, i_name, i_type, i_own = col("区域", "区"), col("学校名", "学校"), col("学校类型", "类型"), col("公办", "办别")
    if i_name is None: return out
    for r in rows[1:]:
        name = r[i_name] if i_name < len(r) else ""
        if not name or not re.search(r"学校|中学|小学", name): continue
        out.append({
            "name": name,
            "region": r[i_region] if i_region is not None and i_region < len(r) else "",
            "school_type": r[i_type] if i_type is not None and i_type < len(r) else "",
            "ownership": r[i_own] if i_own is not None and i_own < len(r) else "",
            "year": year, "doc": doc_label, "source_file": path.name,
        })
    return out


def parse_pdf(path: Path, year: int, doc_label: str):
    import pdfplumber
    out = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            for tb in (page.extract_tables() or []):
                rows = [[(c or "").replace("\n", "").strip() for c in row] for row in tb]
                for r in rows:
                    if not r: continue
                    # 找含学校名的单元
                    cells = [c for c in r if c]
                    name = next((c for c in cells if re.search(r"学校|中学", c) and "区" not in c[:3]), "")
                    if not name or name in ("学校", "学校名"): continue
                    out.append({
                        "name": name, "region": "越秀区",
                        "school_type": "", "ownership": "",
                        "year": year, "doc": doc_label, "source_file": path.name,
                    })
    return out


def main():
    items = []
    items += parse_html_list(RAW / "2024_穗教督3号_标准化34所.html", 2024, "穗教督〔2024〕3号")
    items += parse_html_list(RAW / "2023_穗教督2号_标准化29所.html", 2023, "穗教督〔2023〕2号")
    items += parse_html_list(RAW / "2022_穗教督_标准化14所.html", 2022, "穗教督〔2022〕号")
    items += parse_xls(RAW / "2021_穗教督4号_标准化92所.xls", 2021, "穗教督〔2021〕4号")
    items += parse_pdf(RAW / "越秀_越教字2023-26号_标准化74所.pdf", 2023, "越教字〔2023〕26号")

    # 匹配 school_id：entities name + aliases，规范化去行政区前缀 + 区码校验
    ents = json.load(open(ENTITIES))["entities"]
    DISTRICT_ADCODE = {"荔湾":"440103","越秀":"440104","海珠":"440105","天河":"440106",
                       "白云":"440111","黄埔":"440112","番禺":"440113","花都":"440114",
                       "南沙":"440115","从化":"440117","增城":"440118"}
    def norm_key(s):
        s = s.replace("（", "(").replace("）", ")").replace(" ", "").strip()
        s = re.sub(r"[（(].*?[)）]", "", s)
        s = re.sub(r"^广州市", "", s)
        s = re.sub(r"^广州", "", s)
        for d in DISTRICT_ADCODE:
            s = re.sub(r"^" + d + r"区?", "", s)
        return s
    idx = {}
    for e in ents:
        idx.setdefault(norm_key(e["name"]), e["school_id"])
        for a in e.get("aliases", []):
            idx.setdefault(norm_key(a), e["school_id"])

    matched, unmatched = 0, []
    for it in items:
        sid = idx.get(norm_key(it["name"]))
        # 区码校验：官方 region → adcode；school_id 前 6 位 = gz-XXXXXX-
        expect_adcode = DISTRICT_ADCODE.get(it["region"].replace("区", ""))
        if sid and expect_adcode:
            sid_adcode = sid.split("-")[1] if sid.count("-") >= 2 else ""
            if sid_adcode != expect_adcode:
                sid = None  # 同名跨区，不采纳 → 进人工校正
        it["school_id"] = sid
        if sid: matched += 1
        else: unmatched.append(it["name"])

    # 初中段标记
    for it in items:
        t = it["school_type"]
        it["is_middle_stage"] = any(k in t for k in ["初中", "九年", "完全", "十二年"])

    out = {
        "metric": "standardization_school",
        "description": "义务教育标准化学校认定（市/区分批名单）",
        "sources": [p.name for p in sorted(RAW.glob("*"))],
        "total": len(items),
        "matched": matched,
        "unmatched_count": len(unmatched),
        "unmatched": unmatched,
        "items": items,
    }
    PARSED.mkdir(exist_ok=True)
    (PARSED / "standardization.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 生成 dist/compiled.json：school_id → {指标: 认定信息}（运行时只读）
    compiled = {}
    for it in items:
        if not it["school_id"] or not it["is_middle_stage"]: continue
        compiled[it["school_id"]] = {
            "standardization": True,
            "year": it["year"], "doc": it["doc"], "source_file": it["source_file"],
        }
    DIST = Path(__file__).resolve().parent.parent / "dist"
    DIST.mkdir(exist_ok=True)
    (DIST / "compiled.json").write_text(json.dumps(compiled, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"compiled school_ids={len(compiled)}")
    print(f"total={len(items)} matched={matched} unmatched={len(unmatched)}")


if __name__ == "__main__":
    main()
