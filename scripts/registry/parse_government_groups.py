#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""政府文件底表解析器：官方文件 → 集团/成员清单 → 对照 partial 数据源。

原则（用户口径）：以政府文件为底表（不逐个找），脚本解析官方文件形成数据源，
diff 出缺失集团/缺失成员，宁缺不兜底。产物落 data/registry/_raw/government/。

当前支持：
  - yuexiu：越秀区「669」学区化集团化办学新格局一览表（2026-06-26 官方发布）
    成员表格特征：成员挤在同一单元格，以「学校名（学段）」连续拼接，学校名前缀
    为 广州市越秀区/广州市增城区/英德市/广州市。

用法：
  python3 scripts/registry/parse_government_groups.py yuexiu [--update-partial]
    --update-partial：把官方成员中缺失的写回 partial（带 school_id 反查，缺实体则跳过并列入报告）
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/registry/_raw/government"
PARTIAL = ROOT / "data/registry/_partial_{}_groups.json"
ENTITIES = ROOT / "data/registry/entities.json"

SOURCES = {
    "yuexiu": {
        "file": "yuexiu_669_2026-06.html",
        "url": "http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/xqhjthbx/content/post_10874811.html",
        "table_index": 2,  # 表3-1：集团成员校一览表
        "member_re": r"(?:广州市越秀区|广州市增城区|英德市|广州市)[^（]*（[^）]*）",
        "brand_aliases": {"广州市育才教育集团": ["广州育才教育集团"]},
    },
}


def parse_html_table(html: str, index: int):
    """提取第 index 个 <table> 并解析为行列表。"""
    tables = re.findall(r"<table.*?</table>", html, re.S)
    if index >= len(tables):
        raise ValueError(f"表格索引 {index} 越界（共 {len(tables)} 个）")
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", tables[index], re.S):
        cells = re.findall(r"<t[dh].*?</t[dh]>", tr, re.S)
        rows.append([re.sub(r"<[^>]+>", "", c).strip() for c in cells])
    return rows


def nrm(s: str) -> str:
    """名称归一：去括号及内容、去空格、去 广州市/广州 前缀。"""
    s = re.sub(r"[（(][^）)]*[）)]", "", s)
    s = s.replace(" ", "").replace("\u3000", "")
    return s.replace("广州市", "").replace("广州", "")


def parse_yuexiu(html: str):
    cfg = SOURCES["yuexiu"]
    rows = parse_html_table(html, cfg["table_index"])
    pat = re.compile(cfg["member_re"])
    groups = []
    for brand, core, members in rows[1:]:  # 跳过表头
        mems = pat.findall(members or "")
        groups.append({"brand": brand, "core": core, "members": mems})
    return groups


def load_entities():
    return json.load(open(ENTITIES))["entities"]


def find_entity(ents, name):
    n = nrm(name)
    hits = []
    for e in ents:
        en = nrm(e["name"])
        if en == n or n in (nrm(a) for a in (e.get("aliases") or [])):
            hits.append(e)
    return hits


def diff_partial(groups, partial_groups):
    """官方 vs partial：返回缺失成员（含 school_id 反查）。"""
    cur_map = {}
    for g in partial_groups:
        key = nrm(g["brand"])
        cur_map[key] = set()
        for m in g["members"]:
            cur_map[key].add(nrm(m["name"]))
            for c in m.get("campuses", []):
                cur_map[key].add(nrm(c["poi_name"]))
    missing = []
    for g in groups:
        have = cur_map.get(nrm(g["brand"]), set())
        for m in g["members"]:
            if nrm(m) not in have:
                missing.append({"brand": g["brand"], "member": m})
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("district", choices=sorted(SOURCES))
    ap.add_argument("--update-partial", action="store_true")
    ap.add_argument("--exit-on-gap", action="store_true",
                    help="有缺失成员时以非零码退出（供 check 回归用）")
    args = ap.parse_args()

    cfg = SOURCES[args.district]
    html_path = RAW / cfg["file"]
    if not html_path.exists():
        print(f"❌ 官方快照缺失：{html_path}\n请先抓取官方文件放入该路径。")
        sys.exit(1)
    html = html_path.read_text(encoding="utf-8", errors="ignore")

    if args.district == "yuexiu":
        groups = parse_yuexiu(html)
    else:
        raise NotImplementedError(args.district)

    ents = load_entities()
    partial_path = ROOT / f"data/registry/_partial_{args.district}_groups.json"
    partial = json.load(open(partial_path))

    # 覆盖报告
    cur_map = {}
    for g in partial["groups"]:
        key = nrm(g["brand"])
        cur_map[key] = set()
        for m in g["members"]:
            cur_map[key].add(nrm(m["name"]))
            for c in m.get("campuses", []):
                cur_map[key].add(nrm(c["poi_name"]))

    print(f"==== {args.district}：官方底表覆盖报告 ====")
    total_members = 0
    gaps = []
    for g in groups:
        total_members += len(g["members"])
        have = cur_map.get(nrm(g["brand"]), set())
        miss = [m for m in g["members"] if nrm(m) not in have]
        status = "✓" if not miss else "❌"
        print(f"  {status} {g['brand']}（core={g['core']}）| 官方 {len(g['members'])} 成员"
              + (f" | 缺 {len(miss)}" if miss else ""))
        for m in miss:
            hits = find_entity(ents, m.split("（")[0])
            ids = ", ".join(f"{h['school_id']}({h['name']})" for h in hits) if hits else "entities 无"
            print(f"      - {m} → {ids}")
            gaps.append({"brand": g["brand"], "member": m, "school_ids": [h["school_id"] for h in hits]})
    print(f"\n官方成员总数 {total_members}，缺失 {len(gaps)}")

    if args.exit_on_gap and gaps:
        print("\n❌ 官方底表有缺失成员，请先 --update-partial 或补实体后再提交。")
        sys.exit(1)

    if args.update_partial:
        if not gaps:
            print("\n无缺失，partial 已对齐官方底表。")
            return
        print("\n--update-partial：写回缺失成员……")
        for gap in gaps:
            if not gap["school_ids"]:
                print(f"  ⚠️ 跳过（entities 无实体，宁缺不兜底）：{gap['member']}")
                continue
            name = gap["member"].split("（")[0]
            stage_map = {"小学": "小学", "初中": "初中", "高中": "高中", "完中": "完中",
                         "九年一贯制": "九年一贯"}
            stage = stage_map.get(re.search(r"（([^）]*)）", gap["member"]).group(1), "")
            g = next(g for g in partial["groups"] if nrm(g["brand"]) == nrm(gap["brand"]))
            g["members"].append({
                "name": name,
                "stage": stage,
                "source_url": cfg["url"],
                "verified": "2026-09-18",
                "poi_match": "已锚定",
                "poi_name": name,
                "school_id": gap["school_ids"][0],
            })
            print(f"  ✓ 已加：{name} → {gap['school_ids'][0]}")
        json.dump(partial, open(partial_path, "w"), ensure_ascii=False, indent=2)
        open(partial_path, "a").write("\n")
        print(f"\n已写回 {partial_path}")


if __name__ == "__main__":
    main()
