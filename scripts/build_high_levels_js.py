#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建高中浏览器端数据：
1) 按 levels.json（学校清单+分类+指标）清洗高德 POI → data/high/schools-gz.json（清洗版真源）
   + apps/web/legacy/_generated/high/schools.js（window.GZ_HIGH_SCHOOLS）
2) levels.json → apps/web/legacy/_generated/high/levels.js（window.GZ_HIGH_LEVELS）

用法: python3 scripts/build_high_levels_js.py
依赖: data/high/schools-gz.json（fetch_high_schools.py 产物）、data/high/levels.json（人工调研产物）
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HIGH = ROOT / "data" / "high"
LEGACY_HIGH = ROOT / "apps" / "web" / "legacy" / "_generated" / "high"

DISTRICT_ADCODE = {
    "荔湾区": "440103", "越秀区": "440104", "海珠区": "440105",
    "天河区": "440106", "白云区": "440111", "黄埔区": "440112", "番禺区": "440113",
}
ADCODE_DISTRICT = {v: k for k, v in DISTRICT_ADCODE.items()}

# 楼栋/设施/机构特征词（命中即剔除 POI）
JUNK = [
    "楼", "馆", "正门", "后门", "宿舍", "球场", "商务中心", "发展中心",
    "教学区", "南教学楼", "尚学搂", "门卫室", "总站", "12栋", "创意园",
    "招生办", "停车场", "卓越", "教育(", "教育（",
]


def norm(s: str) -> str:
    """统一名称用于匹配：去广州前缀、全半角括号统一后去括号、去空白。"""
    s = s.replace("广州市", "").replace("广州", "")
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"[()]", "", s)
    return re.sub(r"\s+", "", s)


def build_levels_js(levels):
    js = "/* 由 scripts/build_high_levels_js.py 生成，勿手改 */\n"
    js += "window.GZ_HIGH_LEVELS = " + json.dumps(levels, ensure_ascii=False) + ";\n"
    (LEGACY_HIGH / "levels.js").write_text(js, encoding="utf-8")


def main():
    levels = json.loads((HIGH / "levels.json").read_text(encoding="utf-8"))
    raw = json.loads((HIGH / "schools-gz.json").read_text(encoding="utf-8"))

    # 1) 建立学校索引：campus 规范名 -> school（按 norm 后的 key）
    #    同时收集 aliases 兜底
    campus_to_school = {}
    alias_to_school = {}
    for sc in levels["schools"]:
        for c in sc.get("campuses", []):
            campus_to_school[norm(c)] = sc
        for a in sc.get("aliases", []):
            alias_to_school.setdefault(norm(a), sc)

    # 2) 清洗并匹配 POI
    points, seen = [], set()
    dropped = []  # 留痕：被剔除的点位（供复核）
    for p in raw.get("schools", []):
        name = p["name"]
        key = norm(name)
        # 先按校区/别名精确匹配（真实学校名可能含「楼/馆」，如石楼中学，须先匹配再剔噪音）
        sc = campus_to_school.get(key) or alias_to_school.get(key)
        if sc:
            pt = {"name": name, "lng": p["lng"], "lat": p["lat"], "adcode": p["adcode"], "school": sc["name"]}
            dup = (sc["name"], round(pt["lng"], 4), round(pt["lat"], 4))
            if dup in seen:
                continue
            seen.add(dup)
            points.append(pt)
            continue
        if any(j in name for j in JUNK):
            dropped.append((name, "楼栋/设施"))
            continue
        dropped.append((name, "非高中/初中"))

    # 3) levels.points 补点（高德缺失点位）
    for sc in levels["schools"]:
        for pt in sc.get("points", []):
            adcode = DISTRICT_ADCODE.get(sc["district"], "")
            dup = (sc["name"], round(pt["lng"], 4), round(pt["lat"], 4))
            if dup in seen:
                continue
            seen.add(dup)
            points.append({
                "name": pt["name"], "lng": pt["lng"], "lat": pt["lat"],
                "adcode": adcode, "school": sc["name"], "supplement": True,
            })

    # 4) 输出清洗版点位：json 写回 data/（唯一真源），js 写 legacy/_generated/（旧页面兼容产物）
    result = {
        "updated": levels["updated"],
        "source": "高德地图 Web 服务 API 点位 + levels.json 补点",
        "note": "高中点位（含完全中学），已按学校清单清洗，保留校名+校区；school 字段为规范校名",
        "schools": points,
    }
    LEGACY_HIGH.mkdir(parents=True, exist_ok=True)
    (LEGACY_HIGH / "schools.js").write_text(
        "window.GZ_HIGH_SCHOOLS = " + json.dumps(result, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    (HIGH / "schools-gz.json").write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    build_levels_js(levels)

    # 5) 统计
    per = {}
    for p in points:
        d = ADCODE_DISTRICT.get(p["adcode"], "?")
        per[d] = per.get(d, 0) + 1
    sup = sum(1 for p in points if p.get("supplement"))
    print(f"点位: {len(points)}（含补点 {sup}）")
    print("各区: " + ", ".join(f"{k} {v}" for k, v in sorted(per.items())))
    print(f"剔除留痕: {len(dropped)} 条（见 schools-gz.json 复核）")
    with open(HIGH / "schools_dropped_review.txt", "w", encoding="utf-8") as f:
        for name, why in sorted(dropped):
            f.write(f"{why}\t{name}\n")


if __name__ == "__main__":
    main()
