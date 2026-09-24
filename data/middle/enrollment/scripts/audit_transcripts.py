#!/usr/bin/env python3
"""转录 ↔ OCR 原文交叉审计：量化「Read 多模态直读」转录在机器 OCR 原文中的可追溯命中率。

目的：A 层转录的可审计性量化——每个转录校名/小学名/组名须能在对应官方文件（OCR 原文）中
找到包含匹配；未命中的进入清单（多为 OCR 错字，人工对照原件判断转录是否正确）。

校验对象（对照 parsed/_ocr/<区>_juniors_ocr.json）:
  haizhu : groups 10 组全部中学 + prim_group 71 小学 + plan_classes 28 校名 + direct_feed 键值
  tianhe : gongban 24 校名 + 对口小学 + qiye 3 + minban 24
  huangpu: paiwei_groups 7 组中学/小学 + zhisheng_groups 22 组中学/小学

用法: python3 data/middle/enrollment/scripts/audit_transcripts.py
输出: 每区 命中/总数 + 命中率 + 未命中清单（含 OCR 原文上下文）
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
T = os.path.join(ROOT, "data", "middle", "enrollment", "parsed", "_transcripts")
OCR = os.path.join(ROOT, "data", "middle", "enrollment", "parsed", "_ocr")


def norm(s):
    return re.sub(r"\s+", "", s or "")


def audit(dk):
    tr = json.load(open(os.path.join(T, f"{dk}_2026_juniors.json"), encoding="utf-8"))
    ocr = json.load(open(os.path.join(OCR, f"{dk}_juniors_ocr.json"), encoding="utf-8"))
    hay = norm(ocr["text"])
    items = []  # (类别, 文本)
    if dk == "haizhu":
        for gid, members in tr["groups"].items():
            for m in members:
                items.append(("派位组中学", m))
        for pri, gid in tr["prim_group"].items():
            items.append(("对口小学", pri))
        for school in tr["plan_classes"]:
            items.append(("计划表学校", school))
        for k, v in tr["direct_feed"].items():
            items.append(("直升小学", k))
            items.append(("直升初中", v))
    elif dk == "tianhe":
        for r in tr["gongban"]:
            items.append(("公办初中", r["school"]))
            for p in r.get("primaries") or []:
                items.append(("对口小学", p))
        for r in tr["qiye"]:
            items.append(("企事业初中", r["school"]))
        for r in tr["minban"]:
            items.append(("民办初中", r["school"]))
    elif dk == "huangpu":
        for r in tr["paiwei_groups"].values():
            for m in r["juniors"]:
                items.append(("派位组中学", m))
            for p in r["primaries"]:
                items.append(("派位组小学", p))
        for r in tr["zhisheng_groups"]:
            items.append(("直升初中", r["junior"]))
            for p in r["primaries"]:
                items.append(("直升小学", p))
    hit, miss = [], []
    for cat, text in items:
        if norm(text) and norm(text) in hay:
            hit.append((cat, text))
        else:
            miss.append((cat, text))
    rate = len(hit) / len(items) * 100 if items else 100.0
    print(f"== {dk}: {len(hit)}/{len(items)} 命中（{rate:.1f}%）")
    for cat, text in miss:
        # 找 OCR 里最接近的片段（前后 20 字）供人工对照
        ctx = ""
        if norm(text):
            best = ""
            for seg in re.findall(r"[\u4e00-\u9fff]{2,}", hay):
                if text[0] in seg or seg[0] in text:
                    if len(seg) > len(best) and (seg[0] == text[0] or seg[-1] == text[-1]):
                        best = seg
            ctx = f"  OCR 邻近片段: {best[:40]}"
        print(f"  ✗ [{cat}] {text}{ctx}")
    return len(hit), len(items)


def main():
    total_hit = total = 0
    for dk in ("haizhu", "tianhe", "huangpu"):
        h, t = audit(dk)
        total_hit += h
        total += t
    print(f"\n合计: {total_hit}/{total} 命中（{total_hit/total*100:.1f}%）——未命中项见上，对照官方原件人工复核")
    return 0


if __name__ == "__main__":
    sys.exit(main())
