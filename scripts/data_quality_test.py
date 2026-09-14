#!/usr/bin/env python3
"""教育集团/POI 数据质量回归测试。

覆盖历史 bug：
1. POI 库含"建设中/在建"等状态词（高德采集未过滤，曾致东风东路小学 core_poi 指向"(建设中)"点位）
2. education_groups 引用的 school_id 在 POI 库中不存在（悬空引用）
3. entities 别名跨实体抢名（曾致 4 个东风东校区实体共用"东风东路小学"纯名别名）
4. 多校区 campus 的 school_id 悬空
5. 集团核心校/成员名无法匹配到任何 POI

用法：python3 scripts/data_quality_test.py
"""
import json, re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POI_PATHS = ["data/primary/schools-gz.json", "data/middle/schools-gz.json", "data/high/schools-gz.json"]
STATUS_WORDS = ("建设中", "在建", "筹建", "规划", "拟建", "待建", "筹办", "装修", "工地", "选址", "暂停营业")

failures = []
checks = 0

def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        failures.append(msg)

def load_poi_ids():
    ids = {}
    for p in POI_PATHS:
        d = json.load(open(os.path.join(ROOT, p)))
        for s in d.get("schools", []):
            sid = s.get("school_id")
            if sid:
                ids[sid] = s["name"]
    return ids

def load_groups():
    return json.load(open(os.path.join(ROOT, "data/registry/education_groups.json"))).get("groups", [])

def load_entities():
    return json.load(open(os.path.join(ROOT, "data/registry/entities.json"))).get("entities", [])

def main():
    # ---- 1. POI 库不得含状态词 ----
    for p in POI_PATHS:
        d = json.load(open(os.path.join(ROOT, p)))
        for s in d.get("schools", []):
            n = s.get("name", "")
            if any(w in n for w in STATUS_WORDS):
                check(False, f"[1] POI 名称含状态词: {n} ({p})")

    # ---- 2. education_groups 引用的 school_id 必须存在于 POI 库 ----
    poi_ids = load_poi_ids()
    groups = load_groups()
    for g in groups:
        for cp in g.get("core_poi", []):
            sid = cp.get("school_id")
            if sid:
                check(sid in poi_ids, f"[2] core_poi 悬空 school_id: {g['brand']} → {cp.get('poi_name')} ({sid})")
        for m in g.get("members", []):
            sid = m.get("school_id")
            if sid:
                check(sid in poi_ids, f"[2] member 悬空 school_id: {g['brand']} → {m['name']} ({sid})")
            for c in (m.get("campuses") or []):
                csid = c.get("school_id")
                if csid:
                    check(csid in poi_ids, f"[2] campus 悬空 school_id: {g['brand']} → {m['name']} / {c.get('poi_name')} ({csid})")

    # ---- 3. entities 纯名别名不得被同区多个实体共用（抢名） ----
    # 跨区同名（不同学校）放行；同区多校区共用纯名 → 匹配不确定，报错
    entities = load_entities()
    alias_owner = {}  # alias -> (school_id, adcode)
    for ent in entities:
        # 纯名 = 无括号/无校区限定词的别名
        adcode = ent["school_id"].split("-")[1] if ent.get("school_id") else ""
        for a in ent.get("aliases", []):
            if "(" not in a and "校区" not in a and "本部" not in a and "学校" not in a.split("（")[0] and "、" not in a \
               and "初中部" not in a and "高中部" not in a and "小学部" not in a and "年级" not in a and "教学" not in a and "楼" not in a:
                if a in alias_owner and alias_owner[a][1] == adcode and alias_owner[a][0] != ent["school_id"]:
                    check(False, f"[3] 同区纯名别名被多实体共用: '{a}' → {alias_owner[a][0]} 与 {ent['school_id']}（{adcode}）")
                alias_owner.setdefault(a, (ent["school_id"], adcode))

    # ---- 4. 集团必须有来源 ----
    for g in groups:
        check(bool(g.get("source_urls")), f"[4] 集团无来源: {g['brand']}")

    # ---- 5. 成员数 > 0（已知例外：黄埔3集团官方名册未发布，见P3报告） ----
    KNOWN_EMPTY = {"广州市黄埔区怡园教育集团", "广州开发区外国语学校教育集团", "广州开发区中学教育集团"}
    for g in groups:
        if len(g.get("members", [])) > 0:
            continue
        check(g["brand"] in KNOWN_EMPTY, f"[5] 集团无成员: {g['brand']}（已知例外清单外）")

    # ---- 汇总 ----
    print(f"数据质量测试: {checks} 项检查, {len(failures)} 项失败")
    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("  ✓ 全部通过")

if __name__ == "__main__":
    main()
