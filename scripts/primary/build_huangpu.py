#!/usr/bin/env python3
"""构建黄埔区 2026 公办小学招生离线数据。

数据源: data/primary/enrollments/_raw/huangpu_2026.json
  （黄埔区教育局《2026年黄埔区义务教育学校招生工作实施细则》
   附件4 招生地段划分表 + 附件6 招生计划表，官网扫描件 OCR 转录）

POI 真源: data/primary/schools-gz.json (adcode=440112)
输出: data/primary/enrollments/2026-huangpu.json
匹配规则复用 scripts/primary/build_district_enrollment.py。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "primary"))
DATA = os.path.join(ROOT, "data", "primary")
OUT = os.path.join(DATA, "enrollments", "2026-huangpu.json")
RAW = os.path.join(DATA, "enrollments", "_raw", "huangpu_2026.json")

# 复用既有匹配函数与规则
import build_district_enrollment as bde

ADCODE = "440112"
DISTRICT_NAME = "黄埔区"

# 黄埔区专属名称映射：官方名 → 高德 POI 名；值为 None 表示 POI 库无对应（在建/新建/暂定名）
HP_NAME_MAP = {
    # 显式绑定（POI 实际命名与官方名不一致）
    "区教育研究院实验小学": "黄埔区教育研究院实验小学",
    "广州高新区第一小学": "黄埔区高新区第一小学",
    "科学城实验小学": "广州科学城实验小学",
    "铁英小学": "广铁一中铁英小学",
    "广大附中高新区实验学校(北校区)": "广大附中高新区实验学校北校区(小学部)",
    # 以下官方校 POI 库无对应（新建/在建/暂定名/九年制配建），不绑定
    "双沙旧村改造项目复建区AP0609024S十五号地块学校(暂定名)": None,
    "黄埔区CPPQ-A4-2地块(长岭.雅居建设项目)九年制学校(暂定名)": None,
    "刘村社区旧村改造项目(荷村复建工程项目)AG0222001地块九年制学校(暂定名)": None,
    "知识城南安置区(二期)小学(暂定名)": None,
    "湖南师范大学附属黄埔实验学校": None,
    "广大附中黄埔实验学校(西校区)": None,
    "广大附中高新区实验学校(南校区)": None,
    "广州知识城第二小学": None,
    "开元学校(东校区)": None,
    "开元学校(西校区)": None,
    "华峰学校": None,
    "萝峰小学": None,
    "铁铮学校": None,
    "九龙第一小学": None,
    "广东外语外贸大学附属黄埔实验学校": None,
    "广东外语外贸大学附属科学城实验学校": None,
    "华南师范大学附属黄埔实验学校": None,
}


def main():
    raw = json.load(open(RAW, encoding="utf-8"))
    with open(os.path.join(DATA, "schools-gz.json"), encoding="utf-8") as f:
        poi_data = json.load(f)
    pool = [s for s in poi_data.get("schools", []) if s.get("adcode") == ADCODE]
    BAD = ("建设中", "在建", "工地", "装修", "筹备", "规划", "选址", "劳动教育基地")
    pool = [s for s in pool if len(s["name"]) > 2 and not any(b in s["name"] for b in BAD)]

    records = []
    for s in raw["schools"]:
        records.append({
            "school": s["school"], "district": DISTRICT_NAME, "nature": "公办",
            "plan_classes": s.get("plan_classes"),
            "zone": s.get("zone", ""), "note": s.get("note", ""),
            "source": "黄埔区教育局2026",
        })

    # 历史锚定基线（政府文件校名 → 实体 school_id 的人工修正映射），重跑时优先于规则
    _anchors = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_anchors.json"), encoding="utf-8"))
    _matcher = bde.load_unified_matcher()

    bindings = []
    map_fail = []
    for idx, rec in enumerate(records):
        # 0. 历史锚定优先（1200，最高）：HEAD 人工修正映射不可被规则覆盖
        _anchor_sid = _anchors.get(rec["school"])
        if _anchor_sid:
            _apoi = next((p for p in pool if p.get("school_id") == _anchor_sid), None)
            if _apoi:
                bindings.append((1200, idx, _apoi))
                continue
            mapped = HP_NAME_MAP[rec["school"]]
            if mapped is None:
                # 值为 None：官方校在 POI 库中无对应（在建/新建/暂定名），跳过绑定
                continue
            poi = next((p for p in pool if p["name"] == mapped), None)
            if poi:
                bindings.append((1100, idx, poi))
            else:
                map_fail.append(rec["school"])
            continue
        mapped = bde.NAME_MAP.get(rec["school"])
        if mapped:
            poi = next((p for p in pool if p["name"] == mapped), None)
            if poi:
                bindings.append((1100, idx, poi))
            else:
                map_fail.append(rec["school"])
            continue
        cands = bde.rank_candidates(rec["school"], pool)
        if cands:
            bindings.append((cands[0][0], idx, cands[0][2]))
            continue
        # 自定义规则未命中 → 统一匹配库兜底（复用 build_district_enrollment.resolve_fallback）
        poi = bde.resolve_fallback(_matcher, rec["school"], ADCODE, pool)
        if poi:
            bindings.append((1050, idx, poi))

    bindings.sort(key=lambda x: -x[0])
    matched, ambiguous, used = [], [], {}
    for score, idx, poi in bindings:
        if poi["name"] in used:
            ambiguous.append({"school": records[idx]["school"], "poi": poi["name"],
                              "compete_with": used[poi["name"]]})
            continue
        used[poi["name"]] = records[idx]["school"]
        rec = dict(records[idx])
        # 历史 bug：曾把 POI 名写入 school_id 字段（poi["name"]），重跑即丢真 id。
        # POI 库自带 school_id（实体主键，与 _anchors.json 历史锚定 100% 一致）→ 写真 id。
        rec["school_id"] = poi.get("school_id")
        rec["poi_name"] = poi["name"]
        rec["lng"], rec["lat"] = poi["lng"], poi["lat"]
        matched.append(rec)

    poi_leftover = [s["name"] for s in pool if s["name"] not in used]
    matched_names = {r["school"] for r in matched}
    unmatched = [r["school"] for r in records if r["school"] not in matched_names]

    result = {
        "year": 2026, "district": DISTRICT_NAME,
        "source": raw["source"], "source_url": raw["source_url"],
        "records": matched, "unmatched": sorted(set(unmatched)),
        "ambiguous": ambiguous, "poi_leftover": sorted(set(poi_leftover)),
        "map_fail": sorted(set(map_fail)),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print(f"[黄埔区] 官方记录 {len(records)} | 匹配 {len(matched)} / 未匹配 {len(unmatched)} / 歧义 {len(ambiguous)} / POI无记录 {len(poi_leftover)}")
    print("未匹配:")
    for u in sorted(set(unmatched)):
        print("  -", u)
    if ambiguous:
        print("歧义:", ambiguous)
    print("POI leftover 数:", len(poi_leftover))


if __name__ == "__main__":
    main()
