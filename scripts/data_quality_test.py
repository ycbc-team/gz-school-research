#!/usr/bin/env python3
"""教育集团/POI 数据质量回归测试。

覆盖历史 bug：
1. POI 库含"建设中/在建"等状态词（高德采集未过滤，曾致东风东路小学 core_poi 指向"(建设中)"点位）
2. education_groups 引用的 school_id 在 POI 库中不存在（悬空引用）
3. entities 别名跨实体抢名（曾致 4 个东风东校区实体共用"东风东路小学"纯名别名）
4. 多校区 campus 的 school_id 悬空
5. 集团核心校/成员名无法匹配到任何 POI
6. tier1 口碑字段/摘要/school_id 悬空回归
7. 全量 POI 自我匹配（match_school 对每个 POI 用自身 adcode+学段必须解析回自身 school_id，
   防"修复A引入B"的校名匹配全局回归）
8. 初中招生计划 school_id 存在性 + 区一致性（跨区白名单）+ 合并招生 school_ids 存在性
9. 校名匹配关键案例 golden（改动后必须逐条复核再更新）

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

    # ---- 3. entities 纯名别名不得被同区同 stage 多个实体共用（抢名） ----
    # 跨区同名（不同学校）放行；同区多校区共用纯名 → 匹配不确定，报错。
    # 同区跨 stage（初中部 middle / 高中部 high 各自持裸名，如「广州中学」五山/凤凰）放行：
    # resolve 按 stage 过滤后唯一，匹配确定（初中表命中 middle、高中表命中 high）。
    entities = load_entities()
    alias_owner = {}  # alias -> (school_id, adcode, stage)
    for ent in entities:
        # 纯名 = 无括号/无校区限定词的别名
        adcode = ent["school_id"].split("-")[1] if ent.get("school_id") else ""
        stage = ent.get("stage")
        for a in ent.get("aliases", []):
            if "(" not in a and "校区" not in a and "本部" not in a and "学校" not in a.split("（")[0] and "、" not in a \
               and "初中部" not in a and "高中部" not in a and "小学部" not in a and "年级" not in a and "教学" not in a and "楼" not in a:
                if a in alias_owner and alias_owner[a][1] == adcode and alias_owner[a][2] == stage and alias_owner[a][0] != ent["school_id"]:
                    check(False, f"[3] 同区同stage纯名别名被多实体共用: '{a}' → {alias_owner[a][0]} 与 {ent['school_id']}（{adcode}/{stage}）")
                alias_owner.setdefault(a, (ent["school_id"], adcode, stage))

    # ---- 4. 集团必须有来源 ----
    for g in groups:
        check(bool(g.get("source_urls")), f"[4] 集团无来源: {g['brand']}")

    # ---- 5. 成员数 > 0（已知例外：黄埔3集团官方名册未发布，见P3报告） ----
    KNOWN_EMPTY = {"广州市黄埔区怡园教育集团", "广州开发区外国语学校教育集团", "广州开发区中学教育集团"}
    for g in groups:
        if len(g.get("members", [])) > 0:
            continue
        check(g["brand"] in KNOWN_EMPTY, f"[5] 集团无成员: {g['brand']}（已知例外清单外）")

    # ---- 6. tier1 数据质量回归 ----
    OLD_FIELDS = {"rumor_tier", "rumor_sources", "rumor_notes", "conclusion",
                  "conclusion_basis", "tier_rank", "tier_rank_note",
                  "tier1_eligible", "exclude_reason", "provincial_level_title",
                  "plan_classes_2026", "zhongkao", "reputation"}
    entity_ids = {e["school_id"] for e in entities}

    def check_tier1(path, stage):
        d = json.load(open(os.path.join(ROOT, path)))
        schools = []
        for dname, dobj in d.get("districts", {}).items():
            for s in dobj.get("schools", []):
                s["_district"] = dname
                schools.append(s)
        label = f"[6/{stage}]"

        # 6a. 旧字段不得出现
        for s in schools:
            leaked = set(s.keys()) & OLD_FIELDS
            check(not leaked, f"{label} 旧字段残留: {s['name']} → {leaked}")

        # 6b. summary 与实际一致
        summary = d.get("summary", {})
        check(summary.get("total_schools") == len(schools),
              f"{label} summary.total_schools={summary.get('total_schools')} 实际={len(schools)}")
        actual_by_dist = {}
        for s in schools:
            actual_by_dist[s["_district"]] = actual_by_dist.get(s["_district"], 0) + 1
        check(summary.get("by_district") == actual_by_dist,
              f"{label} summary.by_district 不一致: {summary.get('by_district')} vs {actual_by_dist}")

        # 6c. 初中不得有增城残留
        if stage == "middle":
            check("增城区" not in d.get("districts", {}),
                  f"{label} 初中数据含增城区（应为7区）")

        # 6d. 必填字段
        for s in schools:
            check("name" in s and s["name"], f"{label} 缺 name")
            check("historical_titles" in s, f"{label} {s['name']} 缺 historical_titles")
            check("data_gaps" in s, f"{label} {s['name']} 缺 data_gaps")
            check("evidence" in s, f"{label} {s['name']} 缺 evidence")

        # 6e. school_id 可解析（有则必须存在于 entities）
        for s in schools:
            for sid in s.get("school_ids", []):
                check(sid in entity_ids,
                      f"{label} {s['name']} school_id 悬空: {sid}")

    check_tier1("data/primary/tier1_schools_all.json", "primary")
    check_tier1("data/middle/tier1_schools_all.json", "middle")

    # ---- 7. 全量 POI 自我匹配：统一匹配服务对每个 POI 用自身 adcode+学段必须解析回自身 school_id ----
    # 校名匹配规则的核心回归（防"修复A引入B"）：任何 POI 被别的 POI 抢名/被泛名吸走都会在此失败
    # 统一入口：scripts/registry/school_match.py（项目唯一匹配库，含行政区/学段收敛）
    sys.path.insert(0, os.path.join(ROOT, "scripts/registry"))
    from school_match import SchoolMatcher
    _matcher = SchoolMatcher.load(
        poi_paths=[(os.path.join(ROOT, p), st) for p, st in
                   zip(POI_PATHS, ("小学", "初中", "高中"))],
        entities_path=os.path.join(ROOT, "data/registry/entities.json"))
    _poi_all = _matcher.poi_all
    for lib, stage in (("data/primary/schools-gz.json", "小学"), ("data/middle/schools-gz.json", "初中"), ("data/high/schools-gz.json", "高中")):
        d = json.load(open(os.path.join(ROOT, lib)))
        for s in d.get("schools", []):
            r = _matcher.resolve(s["name"],
                                 preferred_adcode=s.get("adcode"), preferred_stage=stage)
            check(r.get("school_id") == s.get("school_id"),
                  f"[7/{stage}] 自我匹配失败: {s['name']} -> {r.get('school_id')}（应为 {s.get('school_id')}）")

    # ---- 8. 初中招生计划 school_id 一致性：必须存在；区一致（跨区白名单）；合并招生 school_ids 均存在 ----
    # 跨区白名单：培英鹤洞校区(白云名单引用荔湾)、四中丰宁学校(荔湾区属，校址纸行路39号在越秀/荔湾交界，高德归越秀)
    CROSS_DISTRICT_OK = {"gz-440103-a3ee807c", "gz-440104-3b870a8e"}
    for f in sorted(os.listdir(os.path.join(ROOT, "data/primary/enrollments"))):
        if not f.startswith("middle_enrollment_2026_"):
            continue
        d = json.load(open(os.path.join(ROOT, "data/primary/enrollments", f)))
        for r in d.get("records", []):
            sid = r.get("school_id")
            if sid:
                check(sid in poi_ids, f"[8/{d['district']}] 招生记录 school_id 悬空: {r['school']} -> {sid}")
                if sid not in CROSS_DISTRICT_OK:
                    po = _poi_all
                    adc = next((p["adcode"] for p in po if p["school_id"] == sid), None)
                    expect_ad = {"番禺区": "440113", "越秀区": "440104", "海珠区": "440105",
                                 "荔湾区": "440103", "天河区": "440106", "白云区": "440111", "黄埔区": "440112"}[d["district"]]
                    check(adc == expect_ad, f"[8/{d['district']}] 招生记录跨区挂错: {r['school']} -> {sid} (POI 区 {adc} ≠ {expect_ad})")
            for sid2 in (r.get("school_ids") or []):
                check(sid2 in poi_ids, f"[8/{d['district']}] 合并招生 school_ids 悬空: {r['school']} -> {sid2}")

    # ---- 9. 关键案例 golden：校名匹配基线（改动后必须逐条复核再更新） ----
    # 校名取招生记录真实名（与 build_middle_enrollment 输入一致）；缺失为 None
    KEY_CASES = [
        ("广州大学附属中学", "440104", "gz-440104-b22c4eca"),          # 越秀派位 -> 黄华路校区
        ("广州大学附属中学（大学城校区）", "440113", "gz-440113-8f5e4721"),  # 番禺单校抽签 -> 大学城
        ("广铁一中番禺校区", "440113", "gz-440113-97e0acaa"),           # 番禺亚运城
        ("铁英中学", "440112", "gz-440112-c80ac6ac"),                    # 黄埔铁英中学（独立校）
        ("广铁一中铁英学校", "440113", None),                            # 番禺合并招生：无单一校区 id
        ("广州市白云区景泰中学分校区（原广州市白云区南悦中学）", "440111", "gz-440111-2186a02a"),  # 白云湖校区
        ("广州市西关外国语学校校本部", "440103", "gz-440103-b41a3512"),   # 西外初中部
        ("广州市西关外国语学校文昌南校区", "440103", "gz-440103-df535585"),  # 文昌南（新校区）
        ("广东实验中学荔湾学校广钢新城校区", "440103", "gz-440103-53cac770"),  # 省实荔湾初中部
        ("广东实验中学荔湾学校花地湾校区", "440103", "gz-440103-ff7538dc"),  # 花地湾（新校区）
        ("广州市白云区广州空港实验中学（本部）", "440111", "gz-440111-d4c4285e"),  # 空港本部（勿被黄埔广州实验中学吸走）
        ("广州市白云区六中实验中学（空港校区）", "440111", "gz-440111-4ab20f44"),  # 六中实验空港校区
    ]
    for name, adcode, expect in KEY_CASES:
        r = _matcher.resolve(name, preferred_adcode=adcode, preferred_stage="初中")
        check((r.get("school_id") or None) == expect,
              f"[9] 关键案例失配: {name} -> {r.get('school_id')}（应为 {expect}）")

    # ---- 汇总 ----
    print(f"数据质量测试: {checks} 项检查, {len(failures)} 项失败")
    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("  ✓ 全部通过")

if __name__ == "__main__":
    main()
