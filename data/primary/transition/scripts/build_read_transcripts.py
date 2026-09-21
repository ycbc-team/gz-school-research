#!/usr/bin/env python3
"""复现天河/黄埔的 Read 直读转录 json（parsed/_transcripts/）。

数据来源：scripts/read_transcripts/*.py（2026-09-21 用 Read 多模态直读官网 PDF 后人工核对转写）：
  tianhe_2026_part{1,2}.py  → tianhe_2026.json（附件5 招生地段及招生计划表，76 条含校区子行）
  huangpu_2026_{zone,plan}.py → huangpu_2026.json（附件4 地段 95 校 + 附件6 计划 94 条，按校名合并）

用法: python3 data/primary/transition/scripts/build_read_transcripts.py
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
OUT_DIR = os.path.join(ROOT, "data", "primary", "transition", "parsed", "_transcripts")
TRANSCRIPT_DIR = os.path.join(HERE, "read_transcripts")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TRANSCRIPT_DIR, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_tianhe():
    d1 = load("tianhe_2026_part1")
    d2 = load("tianhe_2026_part2")
    data = d1.DATA + d2.DATA2
    seen = set()
    for seq, school, plan, phone, zone, note in data:
        assert (seq, school) not in seen, f"重复: {seq} {school}"
        seen.add((seq, school))
    schools = [{"seq": seq, "school": school, "plan_classes": plan, "zone": zone, "phone": phone, "note": note}
               for seq, school, plan, phone, zone, note in data]
    return {"district": "天河区", "year": 2026,
            "source": "天河区教育局《2026年天河区义务教育阶段学校招生工作实施细则》附件5（公办小学招生地段及招生计划表，官网 PDF 第35-42页）",
            "note": "Read 多模态直读官网 PDF 转录（2026-09-21），校名经 POI/历史官方源交叉核对；含校区子行",
            "schools": schools}


def build_huangpu():
    z = load("huangpu_2026_zone")
    p = load("huangpu_2026_plan")
    schools = []
    for seq, school, zone in z.ZONE:
        plan, phone = p.PLAN.get(school, (None, ""))
        assert plan is not None, f"{school} 无计划数据"
        schools.append({"seq": seq, "school": school, "plan_classes": plan, "zone": zone, "phone": phone})
    return {"district": "黄埔区", "year": 2026,
            "source": "黄埔区教育局《广州市黄埔区2026年义务教育学校招生工作实施细则》附件4（公办小学招生地段划分表，第19-26页）+附件6（公办小学招生计划表，第30-35页）",
            "note": "Read 多模态直读官网 PDF 转录（2026-09-21），附件4/附件6 按校名合并；九龙第二小学含大坦校区 1 班",
            "schools": schools}


if __name__ == "__main__":
    for name, fn in [("tianhe_2026", build_tianhe), ("huangpu_2026", build_huangpu)]:
        out = fn()
        path = os.path.join(OUT_DIR, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"✓ {name}.json（{len(out['schools'])} 条）→ {path}")
