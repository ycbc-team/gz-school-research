#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建高中数据真源：
按 levels.json（学校清单+分类+指标）清洗高德 POI → data/high/schools-gz.json（清洗版真源）。

用法: python3 scripts/high/build_high_levels_js.py
依赖: data/high/schools-gz.json（fetch_high_schools.py 产物）、data/high/levels.json（人工调研产物）
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HIGH = ROOT / "data" / "high"

DISTRICT_ADCODE = {
    "荔湾区": "440103", "越秀区": "440104", "海珠区": "440105",
    "天河区": "440106", "白云区": "440111", "黄埔区": "440112", "番禺区": "440113",
    "南沙区": "440115",  # 补点：广州外国语学校（市属示范，南沙）
}
ADCODE_DISTRICT = {v: k for k, v in DISTRICT_ADCODE.items()}

# 楼栋/设施/机构特征词（命中即剔除 POI）
JUNK = [
    "楼", "馆", "正门", "后门", "宿舍", "球场", "商务中心", "发展中心",
    "教学区", "南教学楼", "尚学搂", "门卫室", "总站", "12栋", "创意园",
    "招生办", "停车场", "卓越", "教育(", "教育（",
]

# 招生校区口径确认不招收高中生的校区；即使仍出现在高德「中学」分类或旧 levels 清单中也不能进高中点位。
MIDDLE_ONLY_CAMPUSES = {
    "广州市真光中学(芳花校区)",
    "广州市真光中学(岭南校区)",
    "广州市西关培英中学(西校区)",
    "广州市第十三中学(禺山校区)",
    "广东外语外贸大学实验中学(北校区)",
    "广东仲元中学(第二校区)",
    "广州市南武中学",
    "广州奥林匹克中学(智谷校区)",  # 智谷=小学+初中，不招高中生（2026-09-18 用户确认）
}


# 统一匹配库：norm 收敛至 school_match.normName（对称 key 比较，原本地定义已删）
sys.path.insert(0, str(ROOT / "scripts" / "registry"))
from school_match import normName as norm


MIDDLE_ONLY_CAMPUS_KEYS = {norm(name) for name in MIDDLE_ONLY_CAMPUSES}


def is_high_campus(name: str) -> bool:
    return norm(name) not in MIDDLE_ONLY_CAMPUS_KEYS


ENTITY_DB = None  # 实体表（build_entities 产物，stage 已含 CAMPUS_STAGE_FIX 核实）


def load_entity_db():
    """读取入库实体表作为「高中资格」判定源（比 levels 人工 campuses 更新：
    含 9-17 办学联网核实 CAMPUS_STAGE_FIX 修正）。stage=middle/primary → 非高中，剔除。"""
    global ENTITY_DB
    if ENTITY_DB is not None:
        return ENTITY_DB
    path = ROOT / "data" / "registry" / "entities.json"
    db = json.loads(path.read_text(encoding="utf-8"))
    items = db["entities"] if isinstance(db, dict) and "entities" in db else db
    ENTITY_DB = {}
    for e in items:
        # 覆盖式写入（实体表顺序 primary→middle→high）：同名完中双 stage 时 high 优先，
        # 防止 middle 实体把完中高中部误判为初中
        ENTITY_DB[norm(e.get("name", ""))] = e.get("stage", "")
    return ENTITY_DB


def legal_name(name: str) -> str:
    """法人规范名：去校区括号（与 merge_groups coreOf 同语义）。"""
    return __import__("re").sub(r"[（(][^）)]*[）)]", "", name).strip()


def main():
    # --out-dir <dir>：产物重定向到指定目录（check_groups_drift 产物一致性重跑用，不污染工作区）
    out_dir = HIGH
    if "--out-dir" in sys.argv:
        out_dir = Path(sys.argv[sys.argv.index("--out-dir") + 1])
    levels = json.loads((HIGH / "levels.json").read_text(encoding="utf-8"))
    raw = json.loads((HIGH / "schools-gz.json").read_text(encoding="utf-8"))
    entity_stage = load_entity_db()

    # 1) 建立学校索引：campus 规范名 -> school（按 norm 后的 key）
    #    同时收集 aliases 兜底
    campus_to_school = {}
    alias_to_school = {}
    for sc in levels["schools"]:
        for c in sc.get("campuses", []):
            if not is_high_campus(c):
                continue
            campus_to_school[norm(c)] = sc
        for a in sc.get("aliases", []):
            alias_to_school.setdefault(norm(a), sc)

    # 2) 清洗并匹配 POI
    #    资格判定（2026-09-18 重构）：实体表 stage 优先（已含 CAMPUS_STAGE_FIX 办学核实），
    #    levels 退化为 school 规范名来源；未匹配实体 → 保留待复核（宁留勿漏，防 levels 漂移误删）
    points, seen = [], set()
    dropped = []  # 留痕：被剔除的点位（供复核）
    for p in raw.get("schools", []):
        name = p["name"]
        if not is_high_campus(name):
            dropped.append((name, "MIDDLE_ONLY_CAMPUSES"))
            continue
        key = norm(name)
        # 实体表判定：middle/primary → 初中/小学，剔除（智谷校区即由此剔除）
        ent_stage = entity_stage.get(key)
        if ent_stage in ("middle", "primary"):
            dropped.append((name, f"实体表stage={ent_stage}"))
            continue
        # 未匹配实体：楼栋/设施噪音剔除，其余保留待复核
        if not ent_stage and any(j in name for j in JUNK):
            dropped.append((name, "楼栋/设施"))
            continue
        # school 规范名：levels 校区/别名优先，否则实体表法人名推导
        sc = campus_to_school.get(key) or alias_to_school.get(key)
        school = sc["name"] if sc else legal_name(name)
        pt = {"name": name, "lng": p["lng"], "lat": p["lat"], "adcode": p["adcode"], "school": school}
        dup = (school, round(pt["lng"], 4), round(pt["lat"], 4))
        if dup in seen:
            continue
        seen.add(dup)
        points.append(pt)

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

    # 4) 输出清洗版点位（唯一真源）
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "updated": levels["updated"],
        "source": "高德地图 Web 服务 API 点位 + levels.json 补点",
        "note": "高中点位（含完全中学），已按实体表学段判定清洗（MIDDLE_ONLY 防线 + 实体表 stage），保留校名+校区；school 字段为规范校名",
        "schools": points,
    }
    (out_dir / "schools-gz.json").write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    # 5) 统计
    per = {}
    for p in points:
        d = ADCODE_DISTRICT.get(p["adcode"], "?")
        per[d] = per.get(d, 0) + 1
    sup = sum(1 for p in points if p.get("supplement"))
    print(f"点位: {len(points)}（含补点 {sup}）")
    print("各区: " + ", ".join(f"{k} {v}" for k, v in sorted(per.items())))
    print(f"剔除留痕: {len(dropped)} 条（见 schools-gz.json 复核）")
    with open(out_dir / "schools_dropped_review.txt", "w", encoding="utf-8") as f:
        for name, why in sorted(dropped):
            f.write(f"{why}\t{name}\n")


if __name__ == "__main__":
    main()
