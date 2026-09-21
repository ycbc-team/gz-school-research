#!/usr/bin/env python3
"""复现解析：天河区公办小学招生地段及招生计划表（tianhe_2026.json）

输入: raw/tianhe_2026_official.pdf（66 页扫描件，附件5=第35-42页 招生地段及招生计划表）
流程: pdftoppm 转页图 → Vision OCR → 按页表格结构解析（序号锚定 + 列分类）
输出: parsed/_transcripts/tianhe_2026.json
      {"district","year","source","note","schools":[{school,plan_classes,zone,phone}, ...]}

依赖: pip3 install pyobjc-framework-Vision pyobjc-framework-Quartz；poppler(pdftoppm)
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DATA = os.path.join(ROOT, "data", "primary", "enrollment")
RAW = os.path.join(DATA, "raw")
OUT = os.path.join(DATA, "parsed", "_transcripts", "tianhe_2026.json")
OCR_TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr", "vision_ocr.py")

PAGES = range(35, 43)  # 附件5 页码（1-based）
HEADER_MARKERS = ("学校", "招生报名地段范围", "招生计划", "联系电话", "备注", "序号", "（班）")

SOURCE = "天河区教育局《2026年天河区义务教育阶段学校招生工作实施细则》附件5（公办小学招生地段及招生计划表，第35-42页，扫描 PDF Vision OCR）"


def page_ocr(page):
    cache = f"/tmp/tianhe_ocr_{page}.json"
    if not os.path.exists(cache):
        subprocess.run(["pdftoppm", "-png", "-r", "150", "-f", str(page), "-l", str(page),
                        os.path.join(RAW, "tianhe_2026_official.pdf"), "/tmp/tianhe_p", "2>/dev/null"], check=True)
        subprocess.run(["python3", OCR_TOOL, f"/tmp/tianhe_p-{page:02d}.png", "--json", cache], check=True)
    return json.load(open(cache, encoding="utf-8"))


def clean_nl(s):
    return re.sub(r"\s+", "", s)


NAME_END = re.compile(r"(小学|学校|实验|校区)$")
PREFIX = "广州市天河区"


def split_name_zone(t):
    """把 OCR 行拆成 (校名片段, 地段片段)：首词若以校名特征结尾则为校名；前缀+校名/地段混合行拆分。"""
    t = t.strip()
    m = re.match(rf"^{PREFIX}\s*(.*)$", t)
    if m:
        rest = m.group(1)
        if not rest:
            return PREFIX, ""
        head = rest.split(" ", 1)[0]
        if NAME_END.search(head) or "教育集团" in head:
            return PREFIX + head, rest[len(head):].strip()
        return PREFIX, rest
    head = t.split(" ", 1)[0]
    if NAME_END.search(head) or "教育集团" in head:
        return head, t[len(head):].strip()
    # 普通行：可能是校名跨行续（如"兴国学校"在"体育东路小学"下一行）或地段
    return "", t


def is_name_line(t):
    """校名锚定行：首词以小学/学校/实验/校区结尾，或含教育集团。"""
    head = t.strip().split(" ", 1)[0]
    return bool(NAME_END.search(head) or "教育集团" in head)


def main():
    records = []
    for page in PAGES:
        lines = page_ocr(page)
        rows = sorted(lines, key=lambda l: l["y"])
        # 校名锚定行
        anchors = []
        for l in rows:
            t = l["text"].strip()
            if not t or l["x"] >= 0.35:
                continue
            t2 = re.sub(rf"^{PREFIX}", "", t).strip()
            if is_name_line(t2):
                anchors.append(l)
        for k, l in enumerate(anchors):
            y0 = l["y"] - 0.015  # 吸收上方前缀行（"广州市天河区"）
            y1 = anchors[k + 1]["y"] - 0.015 if k + 1 < len(anchors) else 1.0
            block = [b for b in rows if y0 <= b["y"] < y1]
            name_parts = []
            zone_parts = []
            plan = phone = note = ""
            seq = ""
            for b in block:
                t = b["text"].strip()
                x = b["x"]
                if not t or any(h in t for h in ("招生计划", "联系电话", "备注", "招生报名地段范围", "（班）", "学校")):
                    continue
                if x < 0.10 and clean_nl(t).isdigit():
                    seq = clean_nl(t)
                    continue
                if x < 0.35:
                    nm, zr = split_name_zone(t)
                    if nm:
                        name_parts.append(nm)
                    if zr:
                        zone_parts.append(zr)
                elif x < 0.62:
                    zone_parts.append(t)
                elif x < 0.73:
                    plan = clean_nl(t)
                elif x < 0.85:
                    phone = clean_nl(t)
                else:
                    note = clean_nl(t)
            name = clean_nl("".join(name_parts))
            name = re.sub(r"^广州市天河区(广州市天河区)+", "广州市天河区", name)
            if not name:
                continue
            zone = re.sub(r"[ \t]+", "", "\n".join(zone_parts)).strip()
            records.append({"seq": seq, "school": name, "plan_classes": plan,
                            "zone": zone, "phone": phone, "note": note})

    out = {"district": "天河区", "year": 2026, "source": SOURCE,
           "note": "Vision OCR 复现（2026-09-21），跨页表头已跳过",
           "schools": records}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✓ {OUT}  {len(records)} 条")


if __name__ == "__main__":
    main()
