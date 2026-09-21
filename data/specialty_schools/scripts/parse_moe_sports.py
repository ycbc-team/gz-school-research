#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""体育特色校结构化源解析（raw/moe → 广州学校清单 + 与现有 sports.json 对比）。

覆盖批次（全部官方原始附件，路径见 raw/moe/）：
  - 足球 2015 第一批    moe_2015_football_schools.xls   （xls，无市列，区名识别）
  - 足球 2023          moe_2023_football.xlsx          （xlsx，省/市/县区/学校）
  - 足球 2024          moe_2024_football.txt + .pdf    （txt 为官方文本提取）
  - 足球 2025          moe_2025_football.txt + .pdf
  - 篮球 2017 第一批   moe_2017_basketball_batch1.docx （docx 表格，省/序号/学校/类别）

输出：
  - scripts/out/moe_sports_parsed.json   解析结果（每批广州学校 + 源行号 + 原文名）
  - 控制台对比报告：与 parsed/sports.json 中对应批次的学校集合差异
用法：python3 data/specialty_schools/scripts/parse_moe_sports.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPECIALTY = Path(__file__).resolve().parent.parent
RAW_MOE = SPECIALTY / "raw" / "moe"
OUT_DIR = Path(__file__).resolve().parent / "out"

GZ_DISTRICTS = ["越秀", "海珠", "荔湾", "天河", "白云", "黄埔", "番禺", "花都", "南沙", "从化", "增城"]
GZ_RE = re.compile(r"^(广州市|" + "|".join(GZ_DISTRICTS) + r")")
# 2015/2017 无市列：广东省段内用区名识别广州市学校（"增城市/从化市"为撤市设区前旧名，
# 区名不带"区/市"字以覆盖新旧叫法；广州区名为全国独有，search 不会误伤外市学校）
GZ_NAME_RE = re.compile(r"广州市|" + "|".join(GZ_DISTRICTS))
# 广东省内其他市/深圳各区名（search）：识别"待核对"与排除项
OTHER_CITY_RE = re.compile(r"东莞|佛山|中山|珠海|惠州|江门|肇庆|汕头|汕尾|湛江|茂名|揭阳|潮州|韶关|河源|梅州|清远|云浮|阳江|深圳|龙岗|宝安|南山|福田|罗湖|盐田|坪山|龙华|光明")

ISSUER_MOE = "教育部"
PROJECT_FOOTBALL = "全国青少年校园足球特色学校"
PROJECT_BASKETBALL = "全国青少年校园篮球特色学校"


def norm_school(name):
    return re.sub(r"\s+", "", name or "").strip()


def is_gz_school(name):
    """无市列名单中的广州学校识别：区名/广州市前缀/裸名"广州XX"（如广州中学）。"""
    return bool(GZ_NAME_RE.search(name)) or name.startswith("广州")


def load_gz_entity_names():
    """项目实体注册表（entities.json）中广州（adcode 4401xx）学校名集合，用于二次确认省属/裸名学校。"""
    try:
        ents = json.loads((ROOT / "data/registry/entity/dist/entities.json").read_text("utf-8"))["entities"]
    except Exception:
        return set()
    gz = set()
    for e in ents:
        sid = e.get("school_id", "")
        if sid.startswith("gz-4401"):
            gz.add(norm_school(e.get("name", "")))
            for a in e.get("aliases", []):
                gz.add(norm_school(a))
    return gz


def parse_xls_2015(path):
    """moe_2015_football_schools.xls：省/序号/学校名称/学校类别，省列前向填充，无市列。
    广东省段内：区名/广州市识别为广州学校；含其他市前缀 → 排除；无法确定 → 待核对。"""
    import xlrd
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_index(0)
    prov, rows, unclear = "", [], []
    for r in range(3, sh.nrows):
        p = str(sh.cell_value(r, 0)).strip()
        if p:
            prov = p
        name = norm_school(str(sh.cell_value(r, 2)))
        if not name or prov != "广东省":
            continue
        if is_gz_school(name):
            rows.append({"raw_name": name, "line": r + 1, "category": str(sh.cell_value(r, 3)).strip()})
        elif OTHER_CITY_RE.search(name):
            continue
        else:
            unclear.append({"raw_name": name, "line": r + 1})
    return rows, unclear


def parse_xlsx_2023(path):
    """moe_2023_football.xlsx：序号/所属省/所属市/所属县（区）/学校名称。"""
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True)
    ws = wb.active
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        vals = [str(c).strip() if c else "" for c in row]
        if len(vals) < 5 or vals[0] == "序号":
            continue
        if vals[1] == "广东省" and vals[2] == "广州市":
            rows.append({"raw_name": norm_school(vals[4]), "line": i, "district": vals[3]})
    return rows


def parse_txt_football(path):
    """moe_2024/2025_football.txt：序号 所属省 所属市 所属县（区） 学校名称（空格分列）。"""
    rows = []
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            int(parts[0])
        except ValueError:
            continue
        prov, city = parts[1], parts[2]
        if prov == "广东省" and city == "广州市":
            rows.append({"raw_name": norm_school("".join(parts[4:])), "line": i, "district": parts[3]})
    return rows


def parse_docx_2017(path):
    """moe_2017_basketball_batch1.docx：省份/序号/学校名称/学校类别。
    表格省份列可能跨行合并（空单元格继承上一省）；广东省段内按区名识别广州学校，
    "广州中学"等不带"广州市"前缀的裸名同样识别；外市（深圳龙岗等）排除。"""
    import docx
    d = docx.Document(str(path))
    rows, prov = [], ""
    for row in d.tables[0].rows:
        cells = [c.text.strip() for c in row.cells]
        if len(cells) < 3:
            continue
        if cells[0]:
            prov = cells[0]
        name = norm_school(cells[2])
        if prov != "广东省" or not name or name.startswith("序号"):
            continue
        if is_gz_school(name) and not OTHER_CITY_RE.search(name):
            rows.append({"raw_name": name, "line": 0, "category": cells[3]})
    return rows


BATCHES = [
    {
        "key": "football_2015", "category": "体育-校园足球", "level": "国家级",
        "batch": "第一批", "year": 2015, "project": PROJECT_FOOTBALL,
        "source": "moe_2015_football_schools.xls",
        "url": "http://www.moe.gov.cn/srcsite/A17/moe_938/s3273/201509/t20150907_206023.html",
        "parse": lambda p: parse_xls_2015(p),
    },
    {
        "key": "football_2023", "category": "体育-校园足球", "level": "国家级",
        "batch": "2023年", "year": 2023, "project": PROJECT_FOOTBALL,
        "source": "moe_2023_football.xlsx",
        "url": "http://www.moe.gov.cn/srcsite/A17/moe_938/s3276/202406/t20240628_1138312.html",
        "parse": lambda p: parse_xlsx_2023(p),
    },
    {
        "key": "football_2024", "category": "体育-校园足球", "level": "国家级",
        "batch": "2024年度", "year": 2024, "project": PROJECT_FOOTBALL,
        "source": "moe_2024_football.txt",
        "url": "http://www.moe.gov.cn/srcsite/A17/moe_938/s3276/202506/t20250612_1193900.html",
        "parse": lambda p: parse_txt_football(p),
    },
    {
        "key": "football_2025", "category": "体育-校园足球", "level": "国家级",
        "batch": "2025年", "year": 2025, "project": PROJECT_FOOTBALL,
        "source": "moe_2025_football.txt",
        "url": "http://www.moe.gov.cn/srcsite/A17/moe_938/s3273/202604/t20260402_1432741.html",
        "parse": lambda p: parse_txt_football(p),
    },
    {
        "key": "basketball_2017", "category": "体育-篮球", "level": "国家级",
        "batch": "第一批", "year": 2017, "project": PROJECT_BASKETBALL,
        "source": "moe_2017_basketball_batch1.docx",
        "url": "http://www.moe.gov.cn/srcsite/A17/moe_938/s3273/201711/t20171120_319504.html",
        "parse": lambda p: parse_docx_2017(p),
    },
]


def load_existing_sports():
    """现有 parsed/sports.json 按 (category, batch) 归组学校名。"""
    p = SPECIALTY / "parsed" / "sports.json"
    if not p.exists():
        return {}
    doc = json.loads(p.read_text("utf-8"))
    groups = {}
    for r in doc.get("records", []):
        key = (r.get("category", ""), r.get("batch", ""))
        groups.setdefault(key, []).append(norm_school(r["school"]))
    return groups


def main():
    OUT_DIR.mkdir(exist_ok=True)
    existing = load_existing_sports()
    results = []
    print(f"{'批次':<18}{'解析广州':<10}{'现有':<8}{'解析独有':<8}{'现有独有'}")
    gz_entities = load_gz_entity_names()
    for b in BATCHES:
        res = b["parse"](RAW_MOE / b["source"])
        rows, unclear = (res if isinstance(res, tuple) else (res, []))
        # 待核对 → 项目实体注册表二次确认（命中广州 school_id 的省属/裸名学校归入广州）
        confirmed, rest = [], []
        for u in unclear:
            if norm_school(u["raw_name"]) in gz_entities:
                confirmed.append(u)
            else:
                rest.append(u)
        rows += confirmed
        parsed_names = [r["raw_name"] for r in rows]
        results.append({
            "key": b["key"], "category": b["category"], "level": b["level"],
            "batch": b["batch"], "year": b["year"], "project": b["project"],
            "issuer": ISSUER_MOE, "source_file": b["source"], "url": b["url"],
            "records": rows,
            "unclear_city": rest, "confirmed_by_registry": [u["raw_name"] for u in confirmed],
        })
        exist = existing.get((b["category"], b["batch"]), [])
        ps, es = set(parsed_names), set(exist)
        print(f"{b['key']:<18}{len(ps):<10}{len(es):<8}{len(ps-es):<8}{len(es-ps)}")
        for name in sorted(ps - es)[:5]:
            print(f"    [解析独有] {name}")
        for name in sorted(es - ps)[:5]:
            print(f"    [现有独有] {name}")
        if unclear:
            print(f"    [待核对·无法确定市] {len(unclear)} 所: " + "、".join(u['raw_name'] for u in unclear[:8]))
        if confirmed:
            print(f"    [实体表确认归穗] {len(confirmed)} 所: " + "、".join(u['raw_name'] for u in confirmed))

    (OUT_DIR / "moe_sports_parsed.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n解析结果已写入 {OUT_DIR / 'moe_sports_parsed.json'}")

    if "--apply" in sys.argv:
        apply_to_parsed(results)


def apply_to_parsed(results):
    """把解析结果替换进 parsed/sports.json 中对应 (category, batch) 批次（保留冰雪等未覆盖批次）。"""
    path = SPECIALTY / "parsed" / "sports.json"
    doc = json.loads(path.read_text("utf-8"))
    target = {(b["category"], b["batch"]) for b in BATCHES}
    keep = [r for r in doc.get("records", []) if (r.get("category"), r.get("batch")) not in target]
    added = 0
    for batch in results:
        for rec in batch["records"]:
            line = f"行{rec['line']}" if rec.get("line") else "官方附件"
            keep.append({
                "school": rec["raw_name"],
                "district": rec.get("district", ""),
                "category": batch["category"],
                "level": batch["level"],
                "batch": batch["batch"],
                "year": str(batch["year"]),
                "project": batch["project"],
                "issuer": batch["issuer"],
                "url": batch["url"],
                "remark": f"由官方附件脚本解析（{batch['source_file']} {line}）",
            })
            added += 1
    doc["records"] = keep
    doc["generated_from"] = "scripts/parse_moe_sports.py --apply（脚本化解析，替换硬编码批次）"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[apply] sports.json 已更新：目标批次替换为脚本解析结果 {added} 条，保留其他批次 {len(keep) - added} 条，"
          f"总计 {len(keep)} 条")


if __name__ == "__main__":
    main()
