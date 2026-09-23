#!/usr/bin/env python3
"""复现解析：2026年海珠区义务教育阶段民办中小学招生计划表（haizhu_2026_minban_plan.png）

输入: raw/haizhu_2026_minban_plan.png（官网附件「4.2026年义务教育阶段民办中小学招生计划表_核定表.jpg」转换的 png）
流程: Vision OCR → 单列表格（序号/学校名称/小学招生计划(班数,人数)/初中招生计划(班数,人数)/备注）
输出: parsed/_transcripts/haizhu_2026_minban.json
      {"district","year","source","note","schools":[
        {"school","plan_classes","plan_count","middle_classes","middle_count"}, ...]}
用途: enrollment 产物 minban 段（民办小学招生计划：班数+人数；无地段）
依赖: pip3 install pyobjc-framework-Vision pyobjc-framework-Quartz
"""
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DATA = os.path.join(ROOT, "data", "primary", "enrollment")
RAW = os.path.join(ROOT, "data", "enrollment", "raw")
OUT = os.path.join(DATA, "parsed", "_transcripts", "haizhu_2026_minban.json")
OCR_TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr", "vision_ocr.py")

SOURCE = "海珠区教育局《2026年义务教育阶段民办中小学招生计划表》（官网附件，Vision OCR）"


OCR_CACHE = os.path.join(DATA, "parsed", "_transcripts", "ocr", "haizhu_2026_minban_ocr.json")


def ocr_lines():
    if os.path.exists(OCR_CACHE):
        return json.load(open(OCR_CACHE, encoding="utf-8"))
    tmp = "/tmp/haizhu_minban_ocr_lines.json"
    subprocess.run(["python3", OCR_TOOL, os.path.join(RAW, "haizhu_2026_minban_plan.png"), "--json", tmp], check=True)
    lines = json.load(open(tmp, encoding="utf-8"))
    os.makedirs(os.path.dirname(OCR_CACHE), exist_ok=True)
    json.dump(lines, open(OCR_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return lines


def parse_single_col(lines):
    """单列表格：y 聚类成行，组内按 x 分列（序号/学校/小学班/小学人/初中班/初中人/备注）。"""
    rows = []
    for ln in lines:
        placed = False
        for r in rows:
            if abs(r["y"] - ln["y"]) < 0.02:
                r["items"].append(ln)
                placed = True
                break
        if not placed:
            rows.append({"y": ln["y"], "items": [ln]})
    out = []
    for r in sorted(rows, key=lambda r: r["y"]):
        items = sorted(r["items"], key=lambda it: it["x"])
        # 按列 x 中心归类
        def pick(x0, x1):
            hit = [it for it in items if x0 <= it["x"] + it["w"] / 2 <= x1]
            return hit[0]["text"] if hit else ""
        school = pick(0.10, 0.37)
        if not school or school == "学校名称":
            continue
        pc = pick(0.38, 0.47)
        pn = pick(0.47, 0.56)
        mc = pick(0.57, 0.65)
        mn = pick(0.66, 0.76)
        rec = {"school": school}
        if pc and pc.isdigit():
            rec["plan_classes"] = int(pc)
        if pn and pn.isdigit():
            rec["plan_count"] = int(pn)
        if mc and mc.isdigit():
            rec["middle_classes"] = int(mc)
        if mn and mn.isdigit():
            rec["middle_count"] = int(mn)
        out.append(rec)
    return out


# OCR 偶发漏读校正（与官方原图 + web_fetch 内嵌图 OCR 交叉核实）：
# 华光小学班数 7 被 Vision OCR 读成「?」（非数字被 pick 丢弃），实测官方原图 7/266
OCR_MINBAN_CORRECTIONS = {
    "广州市海珠区华光小学": {"plan_classes": 7, "plan_count": 266},
}


def apply_corrections(schools):
    for s in schools:
        fix = OCR_MINBAN_CORRECTIONS.get(s["school"])
        if fix:
            s.update(fix)
    return schools


def main():
    schools = apply_corrections(parse_single_col(ocr_lines()))
    seen, uniq = set(), []
    for s in schools:
        if s["school"] in seen:
            continue
        seen.add(s["school"])
        uniq.append(s)
    out = {"district": "海珠区", "year": 2026, "source": SOURCE,
           "note": "民办小学+初中招生计划（班数/人数）；无招生地段（民办摇号）", "schools": uniq}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✓ {OUT}（{len(uniq)} 条）")
    return len(uniq)


if __name__ == "__main__":
    main()
