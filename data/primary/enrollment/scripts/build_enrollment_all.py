#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C 层：各区 B 层产物 → 合并为一份 dist 运行时产物（dist/2026-all.json）。

ABC 三层分层（2026-09-22）：
  A 层  raw/ → parsed/_transcripts/   转录（政府源解析，可审计可重跑）
  B 层  parsed/_transcripts/ → parsed/dist/2026-<区>.json   匹配产物（build_primary_2026.py，
        保留 school/poi_name/lng/lat 等调试字段，供排查匹配与展示核对）
  C 层  parsed/dist/ → dist/2026-all.json   合并瘦身（本脚本）：records/minban 只留
        school_id + 招生字段 + district（名称/坐标按 school_id 联查实体表/POI 表），
        各区元数据（source/unmatched/ambiguous/poi_leftover/map_fail）按区保留。

用法：python3 data/primary/enrollment/scripts/build_enrollment_all.py
产物：data/primary/enrollment/dist/2026-all.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
B_DIR = os.path.join(ROOT, "data", "primary", "enrollment", "parsed", "dist")
OUT = os.path.join(ROOT, "data", "primary", "enrollment", "dist", "2026-all.json")  # 可用 --out-dir 覆盖（快照走临时目录）

DISTRICTS = {"tianhe": "天河区", "yuexiu": "越秀区", "haizhu": "海珠区",
             "liwan": "荔湾区", "panyu": "番禺区", "baiyun": "白云区", "huangpu": "黄埔区"}
ADCODES = {"tianhe": "440106", "yuexiu": "440104", "haizhu": "440105",
           "liwan": "440103", "panyu": "440113", "baiyun": "440111", "huangpu": "440112"}

# C 层瘦身：records 去 school/poi_name/lng/lat（联查）；district 保留原值（番禺为片区名），
# 区标识用 adcode（splitEnrollments 按 adcode 分组还原，还原后删除）
RECORD_FIELDS = ("school_id", "district", "plan_classes", "zone", "note", "phone", "source", "adcode")
MINBAN_FIELDS = ("school_id", "district", "plan_classes", "plan_count", "adcode")


def main(argv: list[str]) -> int:
    out_dir, b_dir = os.path.dirname(OUT), B_DIR
    i = 0
    while i < len(argv):
        if argv[i] == "--out-dir" and i + 1 < len(argv):
            out_dir = argv[i + 1]; i += 2
        elif argv[i] == "--b-dir" and i + 1 < len(argv):
            b_dir = argv[i + 1]; i += 2
        else:
            print(f"未知参数: {argv[i]}（支持 --out-dir DIR / --b-dir DIR）")
            return 2
    meta = {}
    records, minban = [], []
    for key, district in DISTRICTS.items():
        p = os.path.join(b_dir, f"2026-{key}.json")
        if not os.path.exists(p):
            print(f"[C 层] 缺 B 层产物 {os.path.relpath(p, ROOT)}（先跑 build_primary_2026.py）")
            return 1
        j = json.load(open(p, encoding="utf-8"))
        ad = ADCODES[key]
        meta[district] = {**{f: j.get(f) for f in
                             ("source", "source_url", "unmatched", "ambiguous", "poi_leftover", "map_fail")},
                          "adcode": ad}
        records += [{**{f: r.get(f) for f in RECORD_FIELDS}, "adcode": ad} for r in j.get("records", [])]
        minban += [{**{f: m.get(f) for f in MINBAN_FIELDS}, "adcode": ad} for m in j.get("minban", [])]
    out = {"year": 2026, "districts": meta, "records": records, "minban": minban}
    out_path = os.path.join(out_dir, "2026-all.json")
    os.makedirs(out_dir, exist_ok=True)
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[C 层] {len(DISTRICTS)} 区合并 → {os.path.relpath(out_path, ROOT)}"
          f"（records {len(records)} / minban {len(minban)}，无 school 字段）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
