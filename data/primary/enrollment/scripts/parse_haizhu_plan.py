#!/usr/bin/env python3
"""复现解析：2026年海珠区公办小学招生计划表（班数，haizhu_2026_gongban_plan.png）

输入: raw/haizhu_2026_gongban_plan.png（官网「2026年海珠区公办小学招生计划表」，2026-04-28 挂网）
流程: Vision OCR → 双列重建（左列 | 右列，每列 学校（校区）+招生计划（班））
输出: parsed/_transcripts/haizhu_2026_plan.json
      {"district","year","source","note","schools":[{"school","plan_classes"}, ...]}
用途: 与 haizhu_2026.json（服务地段表）合并 → records 班数（官方真源：海珠公办有班数无人数）
依赖: pip3 install pyobjc-framework-Vision pyobjc-framework-Quartz
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DATA = os.path.join(ROOT, "data", "primary", "enrollment")
RAW = os.path.join(ROOT, "data", "enrollment", "raw")
OUT = os.path.join(DATA, "parsed", "_transcripts", "haizhu_2026_plan.json")
OCR_TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr", "vision_ocr.py")

SOURCE = "海珠区教育局《2026年海珠区公办小学招生计划表》（官网正文图，Vision OCR）"


OCR_CACHE = os.path.join(DATA, "parsed", "_transcripts", "ocr", "haizhu_2026_plan_ocr.json")


def ocr_lines():
    """Vision OCR 每次运行存在偶发漏检/抖动，缓存固定一次完整结果保证可复现审计；
    如需重跑 OCR，删除缓存文件即可（--no-cache 同理）。"""
    if os.path.exists(OCR_CACHE):
        return json.load(open(OCR_CACHE, encoding="utf-8"))
    tmp = "/tmp/haizhu_plan_ocr_lines.json"
    subprocess.run(["python3", OCR_TOOL, os.path.join(RAW, "haizhu_2026_gongban_plan.png"), "--json", tmp], check=True)
    lines = json.load(open(tmp, encoding="utf-8"))
    os.makedirs(os.path.dirname(OCR_CACHE), exist_ok=True)
    json.dump(lines, open(OCR_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return lines


def parse_dual_cols(lines):
    """双列表格：y 聚类成视觉行（容差 0.008：行内词 y 差 0.002-0.005，相邻行 y 差 ≥0.019），
    行内每列 校名(x 序) ↔ 班数(x 序) 配对。

    Vision OCR 行高抖动（同一视觉行词 y 差 0.002-0.005，相邻行差 0.019-0.026），
    容差过大（0.02）会把相邻行并组导致错配；0.008 可稳分视觉行。
    """
    rows = []
    for ln in lines:
        placed = False
        for r in rows:
            if abs(r["y"] - ln["y"]) < 0.008:
                r["items"].append(ln)
                placed = True
                break
        if not placed:
            rows.append({"y": ln["y"], "items": [ln]})
    out = []
    for r in sorted(rows, key=lambda r: r["y"]):
        items = sorted(r["items"], key=lambda it: it["x"])
        # 双列分界：官方表格中线约 x=0.46（左列班数 0.39 / 右列校名 0.49-0.55）；
        # 用 0.5 会把右列校名（如海珠外附二小 x=0.485）误分左列致丢行
        for col in ([it for it in items if it["x"] < 0.45], [it for it in items if it["x"] >= 0.45]):
            names = [it for it in col if not it["text"].isdigit() and not it["text"].startswith(("学校", "招生计划"))]
            nums = [it for it in col if it["text"].isdigit()]
            for n, u in zip(names, nums):
                out.append({"school": n["text"], "plan_classes": int(u["text"])})
    return out


# Vision OCR 误读校正（可审计）：当前无（公办计划表与 Read OCR 交叉一致）；
# 若 OCR 偶发误读，在此登记「官方名: 班数」并注明交叉依据
OCR_PLAN_CORRECTIONS = {}


def main():
    schools = parse_dual_cols(ocr_lines())
    # 去重（OCR 尾部重复框）保序 + OCR 误读校正
    seen, uniq = set(), []
    corr_schools = {s["school"] for s in schools}
    for name, cls in OCR_PLAN_CORRECTIONS.items():
        if name not in corr_schools:
            schools.append({"school": name, "plan_classes": cls})  # OCR 误读（非数字）致丢行，强制注入
    for s in schools:
        if s["school"] in OCR_PLAN_CORRECTIONS:
            s["plan_classes"] = OCR_PLAN_CORRECTIONS[s["school"]]
        k = (s["school"], s["plan_classes"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(s)
    out = {"district": "海珠区", "year": 2026, "source": SOURCE,
           "note": "招生计划（班）；仅班数，官方未公布人数", "schools": uniq}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✓ {OUT}（{len(uniq)} 条）")
    return len(uniq)


if __name__ == "__main__":
    main()
