#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""荔湾 2026 转录整改（A 层，可复现）：zone 树结构恢复 + a4 备注解析为 note。

背景（2026-09-22 用户指出）：
1. a4 地段表 zone 是「街道 → 社区 → 路段」树结构（跨行合并单元格），转录拍平成
   「街道·社区：路段」逐行（街道重复、无路段的社区也带「：」）。此处恢复层级：
   街道一行（无缩进），社区行两空格缩进；有路段 → 「社区：路段」，无路段 → 仅「社区」。
   特例「桥中街：」（街道级招生无社区列）→ 仅街道行，不带冒号。
2. a4 学校列单元格内学校名下方附「（注：…）」，转录未解析 → 提取为 note 字段
   （去「（注：」前缀与尾部「）」；法人行备注优先挂法人条目，无法人行挂首个校区条目）。

只改 zone 格式与 note 字段，不动 school/plan_classes（人工核对过的转录数据）。
用法：python3 data/primary/enrollment/scripts/fix_liwan_transcript.py
"""
import json
import os
import re
import sys

import docx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
TRANS = os.path.join(ROOT, "data/primary/enrollment/parsed/_transcripts/liwan_2026.json")
A4 = os.path.join(ROOT, "data/enrollment/raw/liwan_2026_primary_a4.docx")


def tree_zone(zone_str):
    """「街道·社区：路段」逐行 → 树结构（街道行 + 两空格缩进社区行；无路段不带冒号）。"""
    out, cur_street = [], None
    for line in (zone_str or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        if "·" in line:
            street, rest = line.split("·", 1)
            if street != cur_street:
                out.append(street)
                cur_street = street
            if "：" in rest:
                comm, route = rest.split("：", 1)
                out.append(f"  {comm}：{route.strip()}" if route.strip() else f"  {comm}")
            else:
                out.append(f"  {rest}")
        else:
            s = line.rstrip("：").strip()
            if s and s != cur_street:
                out.append(s)
                cur_street = s
    return "\n".join(out)


def norm(n):
    n = re.sub(r"\s+", "", n or "")
    n = n.replace("（", "(").replace("）", ")")
    n = n.replace("广州市", "").replace("荔湾区", "")
    n = re.sub(r"\(小学部\)$", "", n)
    return n


def extract_a4_notes():
    """a4 表格：学校列单元格「学校名\n\n（注：…）」→ {norm(学校名): note}。"""
    d = docx.Document(A4)
    notes, seen = {}, set()
    for row in d.tables[0].rows:
        sc = row.cells[0].text.strip()
        if not sc:
            continue
        first = sc.split("\n")[0].strip()
        if first in seen:
            continue
        seen.add(first)
        if "（注：" in sc:
            note = sc.split("（注：", 1)[1]
            if note.endswith("）"):
                note = note[:-1]
            notes[norm(first)] = note
    return notes


def main() -> int:
    tr = json.load(open(TRANS, encoding="utf-8"))
    notes = extract_a4_notes()

    # 1) zone 树化
    for s in tr["schools"]:
        if s.get("zone"):
            s["zone"] = tree_zone(s["zone"])

    # 2) note 归位：精确（norm 全等）→ 法人前缀（a4 法人名 ⊂ 转录校区名，挂首个匹配校区）
    assigned, leftovers = {}, {}
    for a4_norm, note in notes.items():
        # 精确
        hits = [s for s in tr["schools"] if norm(s["school"]) == a4_norm]
        if not hits:
            # 法人前缀：转录名以 a4 名开头（如「广东实验中学荔湾学校」→「…（第一小学部）」）
            hits = [s for s in tr["schools"]
                    if norm(s["school"]).startswith(a4_norm) and len(norm(s["school"])) > len(a4_norm)]
        if not hits:
            leftovers[a4_norm] = note
            continue
        if hits[0].get("note"):
            print(f"  [note已存在，跳过] {hits[0]['school']}")
        hits[0]["note"] = note
        assigned[a4_norm] = hits[0]["school"]
    for a4_norm, school in assigned.items():
        print(f"  note归位: {school}")
    if leftovers:
        print(f"  [未归位 {len(leftovers)}] {list(leftovers.keys())}")

    json.dump(tr, open(TRANS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"已写回 {TRANS}（schools {len(tr['schools'])}，note {sum(1 for s in tr['schools'] if s.get('note'))} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
