#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""特色校认定聚合编译：parsed/*.json → dist/specialty_schools.json（运行时产物，体积压缩版）。

格式（2026-09-20 二版）：
  - recognition[]  唯一认定池（category/level/batch/year/project/issuer/url 去重），
                    537 条认定 → 26 个池条目，school 仅存索引复用文本
  - schools[]      每校一条：{ school, ids[], stage[], rec[池索引], notes?[] }
                    stage 来自 POI 分层（小学/初中/高中），多校区/多学段全挂；
                    ids 为空 = 未匹配；notes = [{ i: 池索引, g?: 未匹配原因, t?: 源备注 }]
                    仅当该认定的 gap/note 非空时写入，逐条保留不丢信息
  - 规则与 awards 一致：SchoolMatcher 匹配（preferred_adcode 区码收窄，不传 stage 全学段），
                    非学校在 parsed 阶段已排除
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # gz_school_research
SPECIALTY = Path(__file__).resolve().parent.parent
ENTITIES = ROOT / "data/registry/entities.json"

sys.path.insert(0, str(ROOT / "scripts" / "registry"))
from school_match import SchoolMatcher

DISTRICT_ADCODE = {"荔湾": "440103", "越秀": "440104", "海珠": "440105", "天河": "440106",
                   "白云": "440111", "黄埔": "440112", "番禺": "440113", "花都": "440114",
                   "南沙": "440115", "从化": "440117", "增城": "440118"}

GAP_RE = re.compile(r"未匹配registry（([^）]+)）")


def split_remark(remark):
    """备注拆为 (gap, note)：未匹配原因单独成 gap，其余源备注为 note。"""
    gap, note = "", ""
    m = GAP_RE.search(remark or "")
    if m:
        gap = m.group(1)
        rest = (remark[:m.start()] + remark[m.end():]).strip(";； ")
    else:
        rest = (remark or "").strip(";； ")
    if rest:
        note = rest
    return gap, note


def build_stage_index():
    """school_id → {小学/初中/高中}（一个 id 可能同属多学段，如完中）。"""
    sid_stage = {}
    for stage, path in [("小学", "primary_poi.json"), ("初中", "middle_poi.json"), ("高中", "high_poi.json")]:
        poi = json.loads((ROOT / "data/poi/dist" / path).read_text("utf-8"))
        schools = poi.get("schools", poi if isinstance(poi, list) else [])
        for s in schools:
            sid = s.get("school_id")
            if sid:
                sid_stage.setdefault(sid, set()).add(stage)
    return sid_stage


def main():
    matcher = SchoolMatcher.load(
        poi_paths=[
            (ROOT / "data/poi/dist/primary_poi.json", "小学"),
            (ROOT / "data/poi/dist/middle_poi.json", "初中"),
            (ROOT / "data/poi/dist/high_poi.json", "高中"),
        ],
        entities_path=ENTITIES,
    )
    sid_stage = build_stage_index()

    pool = []            # [{category,level,batch,year,project,issuer,url}]
    pool_idx = {}        # (7字段) → 池索引
    schools = {}         # school 名 → {ids, stage, rec:[], notes:{idx:{g,t}}}
    total = 0

    def pool_of(rec):
        key = (rec["category"], rec["level"], rec["batch"],
               int(rec["year"]) if str(rec.get("year", "")).isdigit() else rec.get("year", ""),
               rec["project"], rec["issuer"], rec["url"])
        if key not in pool_idx:
            pool_idx[key] = len(pool)
            pool.append({"category": key[0], "level": key[1], "batch": key[2], "year": key[3],
                         "project": key[4], "issuer": key[5], "url": key[6]})
        return pool_idx[key]

    for p in sorted((SPECIALTY / "parsed").glob("*.json")):
        doc = json.loads(p.read_text("utf-8"))
        for rec in doc.get("records", []):
            total += 1
            school = rec["school"]
            adcode = DISTRICT_ADCODE.get(rec.get("district", "").replace("区", ""))
            hits = matcher.resolve(school, preferred_adcode=adcode, preferred_stage=None, strategy="all") or []
            sids = sorted({h.get("school_id") for h in hits if h.get("school_id")})
            gap, note = split_remark(rec.get("remark", ""))
            entry = schools.setdefault(school, {"school": school, "ids": [], "stage": [], "rec": [], "notes": {}})
            entry["ids"] = sorted(set(entry["ids"]) | set(sids))
            entry["stage"] = sorted({st for sid in entry["ids"] for st in sid_stage.get(sid, [])},
                                    key=lambda x: ["小学", "初中", "高中"].index(x))
            idx = pool_of(rec)
            entry["rec"].append(idx)
            if gap or note:
                item = entry["notes"].setdefault(idx, {})
                if gap:
                    item["g"] = gap
                if note:
                    item["t"] = note

    for e in schools.values():
        e["rec"] = sorted(set(e["rec"]))          # 去重并保序（同校重复认定合并索引）
        if e["notes"]:
            e["notes"] = [{"i": i, **v} for i, v in sorted(e["notes"].items())]  # [{i,g?,t?}]
        else:
            del e["notes"]                        # 无备注不写字段

    out = {
        "updated": "2026-09-20",
        "metric": "specialty_schools",
        "summary": {
            "total_records": total,
            "total_schools": len(schools),
            "matched_schools": sum(1 for s in schools.values() if s["ids"]),
            "unmatched_schools": sum(1 for s in schools.values() if not s["ids"]),
            "recognition_pool": len(pool),
        },
        "recognition": pool,
        "schools": list(schools.values()),
    }
    dist_dir = SPECIALTY / "dist"
    dist_dir.mkdir(exist_ok=True)
    (dist_dir / "specialty_schools.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[specialty] 记录 {total} 条 → 学校 {len(schools)} 所（匹配 {out['summary']['matched_schools']} / "
          f"未匹配 {out['summary']['unmatched_schools']}），recognition 池 {len(pool)} 条")


if __name__ == "__main__":
    main()
