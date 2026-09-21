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
import json, re, sys, os, glob, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 孤儿学校清单快照（sha256 前 16 位）：公办且「无招生或无升学」的异常学校清单。
# 方向：孤儿数量越小越好（每修复一所数据缺口就少一所，属纯正向改进）；
# 快照失败时看孤儿清单 diff——减少→改进，UPDATE_SNAPSHOT 显式更新即可；
# 新增/名单变化→数据回退或误伤，必须先排查来源再更新，禁止直接更新快照掩盖。
# 存量孤儿逐一排查修复（修复一所 → 重跑 → 显式更新此快照）；孤儿新增/变化立即失败。
# 首次固化 2026-09-16：primary 256 + middle 166 + high 2（详见 outputs/orphan_schools_20260916.md）
# 2026-09-18 更新：南武教育集团入册补 2 个校区 POI（江南外国语南校区、南二实北校区，高德官方点位），
#   招生/升学真源未单列校区 → 孤儿 +2（预期新增，非回归）
# 2026-09-16 更新：小学缺口修复 9 所（荔湾文昌小学、越秀八一/知用/七中实验、白云新和/云湖/棠景、
#   黄埔华中师范、番禺沙北）→ 孤儿 221→212，消除 9、新增 0（纯正向）
# 2026-09-16 更新：初中缺口修复 4 所（白云六十五中桃园/明德、培英科技城、培英实验云景；
#   另新增匹配奥中智谷/华工初中部/暨大初中部/六中珠江万胜围但升学仍缺，仍属孤儿）→ middle 165→161，新增 0
# 2026-09-16 更新：孤儿判定补记 school_ids（铁英东/西、明德+同德共担计划）→ 374，新增 0（纯正向）
# 2026-09-17 更新：剔除脏 POI 实体 18 所（楼栋/游泳馆/便利店/充电站/大学校区/外籍校/咏春/后门/教学区）
#   → 孤儿 374→357，新增 0（纯正向）；build_entities 加 NON_SCHOOL_POI 过滤（复用既有词表）
# 2026-09-17 更新：孤儿排查口径收窄为只看 7 区（荔湾/越秀/海珠/天河/白云/黄埔/番禺）公办——
#   远郊（花都/从化/增城/南沙）与无 adcode 市属实体本就无招生/升学采集，不属于异常排查
#   → 孤儿 357→353（排除 9 所非 7 区孤儿：黄广中学/英豪/香江/暨大增城/广外空港/南外/理工实验/
#     斐特思/黄广附属），新增 0
# 2026-09-17 更新：孤儿判定「有升学」计入 quota 法人行 school_ids（校区升学聚合在法人行，
#   主 id 归一后避免东湖/桂花/麓湖/育才等校区误判孤儿）→ 孤儿 353→339，新增 0
# 2026-09-17 更新：初中招生文件（build_middle_enrollment.py）法人行补 school_ids——
#   政府招生按法人公布（一条「广州市第十六中学」覆盖东湖/本部/水荫），校区实体经
#   school_ids 命中「有招生」，消除 39 所「无招生」误报孤儿（东湖/水荫/育才东西/
#   桂花/麓湖/一一三中三校区/真光各校区等 57 所校区实体中仍有 18 所缺升学）→ 339→300，新增 0
# 2026-09-17 更新：校区「办不办初中」是业务事实不能从法人名推导（部分校区非完中、
#   初中部只在某些校区；其余为表生产错误）——attach 收紧为 CONFIRMED_CAMPUS 白名单
#   （官方 raw/用户确认：十六中东湖+本部、知识城东+南、六十五中明德+同德、铁英东+西），
#   水荫纯高中 middle 实体删除（build_entities NON_MIDDLE_CAMPUS）→ 孤儿 300→335
#   （未确认校区宁缺、回孤儿待逐校确认；净消除 4 所），新增 0
# 2026-09-17 二更：仲元二校区官方明文「二校区（初中部）」10 班 450 人（番禺招生计划），
#   build_middle_enrollment 补挂 gz-440113-6dbdc462（原 school_id=None 过时）→ 孤儿 335→334，新增 0
ORPHAN_SNAPSHOT = "5ca25cde9506f8ac"

# 同段同址冗余候选快照（sha256 前 16 位）：同学段+同区+≤50m 的实体对（含民办）。
# 方向：候选越少越好（每合并一对冗余实体就少一组，属纯正向改进）。
# 与孤儿快照同款防线：新增候选立即失败，须排查后再 UPDATE_SNAPSHOT=1 显式更新。
# 首次固化 2026-09-17：15 组候选（含省实荔湾 初中部/初中部一期/花地湾 同址北文街2号、
#   景泰小学柯子岭校区/43号A座 等，逐一排查中，见提交说明）。
CO_LOCATED_SNAPSHOT = "78bd7925e8bb2651"

# 民办学校名单快照（sha256 前 16 位）：data/registry/private/dist/minban_schools.json 民办名单权威表。
# 民办身份由 build_entities 按此表联表生产 entities nature（表驱动，非手写 id 列表）。
# 名单是业务事实集合（非"越小越好"）：新增民办 / 误标公办 / 漏标民办都算名单变化，
# 必须先排查官方来源（各区教育局年检/招生计划/积分入学等，表内 source_urls 可追溯），
# 再 UPDATE_SNAPSHOT=1 显式更新。防止"手写 id 列表"式误标（如 2026-09-18 剑桥郡小学
# 被误标民办：公办的番禺区剑桥郡小学 vs 民办的剑桥郡加拿达外国语学校）无人感知。
# 首次固化 2026-09-18：228 所（含剑桥郡小学误标剔除后；另新增 7 区 minban_*.md 查漏补缺
# 来源链接共 88 所可追溯）。
PRIVATE_MINBAN_SNAPSHOT = "c3ee85789c726b50"
POI_PATHS = ["data/poi/dist/primary_poi.json", "data/poi/dist/middle_poi.json", "data/poi/dist/high_poi.json"]
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
    return json.load(open(os.path.join(ROOT, "data/registry/group/dist/education_groups.json"))).get("groups", [])

def load_entities():
    return json.load(open(os.path.join(ROOT, "data/registry/entity/dist/entities.json"))).get("entities", [])

def main():
    # 各序号检查的一行概要（[11]-[19]）：通过时全部隐藏，失败时才逐项输出
    _section_lines = []
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
    # 用户口径（2026-09）：别名非主键可重复；裸名「同区+学段+主校区」可唯一收敛
    # （resolve by_main 优先无括号主 POI）→ 只要冲突实体中存在无括号主名即放行；
    # 仅当冲突双方都带校区括号（无主 POI 可收敛，如「广钢校区」vs「岭南校区」裸名撞）才报错。
    entities = load_entities()
    # 官方划片表小学名共享裸名豁免（与 build_entities.py OFFICIAL_PRIMARY_ALIAS 多校区裸名键同步）：
    # 官方文件按小学法人名（裸名）公布，同区多校区并列招生是业务事实（华阳小学 4 校区、龙口西 5 校区等），
    # 匹配器/构建脚本按官方名解析出全部校区实体，不构成匹配歧义。新增共享裸名需同步更新本集合。
    _PRIMARY_SHARED_PLAIN = {'华康小学', '华阳小学', '龙口西小学', '华景小学', '天府路小学', '员村小学',
                             '昌乐小学', '五山小学', '银河小学', '侨乐小学', '龙洞小学', '天河第一小学',
                             '体育西路小学', '元岗小学', '棠德南小学'}
    alias_owner = {}  # alias -> (school_id, adcode, stage, 该实体名是否无括号)
    for ent in entities:
        # 纯名 = 无括号/无校区限定词的别名；实体名自身也参与（build_entities 不再把自身
        # norm 写进 aliases，纯名冲突检查须覆盖 name，避免同区同 stage 同名实体漏检）
        adcode = ent["school_id"].split("-")[1] if ent.get("school_id") else ""
        stage = ent.get("stage")
        has_main = "(" not in ent.get("name", "") and "（" not in ent.get("name", "")
        for a in [ent.get("name", "")] + ent.get("aliases", []):
            if a in _PRIMARY_SHARED_PLAIN:
                continue  # 官方划片表共享裸名（业务事实，见上注释）
            if "(" not in a and "校区" not in a and "本部" not in a and "学校" not in a.split("（")[0] and "、" not in a \
               and "初中部" not in a and "高中部" not in a and "小学部" not in a and "年级" not in a and "教学" not in a and "楼" not in a:
                if a in alias_owner and alias_owner[a][1] == adcode and alias_owner[a][2] == stage and alias_owner[a][0] != ent["school_id"]:
                    # 冲突双方都带括号（无主 POI）→ 真歧义；任一方为无括号主名 → resolve by_main 可收敛，放行
                    if not has_main and not alias_owner[a][3]:
                        check(False, f"[3] 同区同stage纯名别名被多实体共用且无主POI可收敛: '{a}' → {alias_owner[a][0]} 与 {ent['school_id']}（{adcode}/{stage}）")
                alias_owner.setdefault(a, (ent["school_id"], adcode, stage, has_main))

    # ---- 4. 集团必须有来源 ----
    for g in groups:
        check(bool(g.get("source_urls")), f"[4] 集团无来源: {g['brand']}")

    # ---- 5. 成员数 > 0（已知例外：官方文件/品牌组只列核心校自身 → 核心校成员去重后成员为空，
    # 校区由 core_poi 承载，属正常）----
    KNOWN_EMPTY = {
        # 官方名册未发布（见 P3 报告）
        "广州市黄埔区怡园教育集团", "广州开发区外国语学校教育集团", "广州开发区中学教育集团",
        # 区文件成员名单仅核心校自身（merge_groups 核心校成员去重后为空，校区在 core_poi）
        "广东实验中学荔湾学校教育集团", "广州市荔湾区沙面小学教育集团", "广州市荔湾区西关培正小学教育集团",
        "广州开发区第二小学教育集团", "京溪小学教育集团", "市桥桥城中学教育集团",
        "市桥实验小学教育集团", "沙头中心小学教育集团",
        # 品牌组仅核心校（清华附中 3 校区），无独立成员校
        "清华附中湾区学校教育集团",
    }
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
    # 统一入口：data/registry/entity/scripts/school_match.py（项目唯一匹配库，含行政区/学段收敛）
    sys.path.insert(0, os.path.join(ROOT, "data/registry/entity/scripts"))
    from school_match import SchoolMatcher
    _matcher = SchoolMatcher.load(
        poi_paths=[(os.path.join(ROOT, p), st) for p, st in
                   zip(POI_PATHS, ("小学", "初中", "高中"))],
        entities_path=os.path.join(ROOT, "data/registry/entity/dist/entities.json"))
    _poi_all = _matcher.poi_all
    for lib, stage in (("data/poi/dist/primary_poi.json", "小学"), ("data/poi/dist/middle_poi.json", "初中"), ("data/poi/dist/high_poi.json", "高中")):
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
        ("广东实验中学荔湾学校广钢新城校区", "440103", "gz-440103-53cac770"),  # 广钢新城=初中部一期=初中部(北文街2号，2026-09-17 合并)；法人聚合 school_ids 含 53cac770
        ("广东实验中学荔湾学校花地湾校区", "440103", "gz-440103-ff7538dc"),  # 花地湾（新校区）
        ("广州市白云区广州空港实验中学（本部）", "440111", "gz-440111-d4c4285e"),  # 空港本部（勿被黄埔广州实验中学吸走）
        ("广州市白云区六中实验中学（空港校区）", "440111", "gz-440111-4ab20f44"),  # 六中实验空港校区
    ]
    for name, adcode, expect in KEY_CASES:
        r = _matcher.resolve(name, preferred_adcode=adcode, preferred_stage="初中")
        check((r.get("school_id") or None) == expect,
              f"[9] 关键案例失配: {name} -> {r.get('school_id')}（应为 {expect}）")

    # ---- 10. education_groups 跨区同名撞车校验：core_poi 实体的法人 key（matchNorm(coreCampusName)
    # 含 aliases 通称）若与组 core/成员法人 key 相同、但存在不同行政区实体 → 报错。
    # 拦截「matchNorm 撞车」型跨法人误并（如海珠/黄埔/番禺实验小学曾归一成「实验小学」互相挂载）。
    # 法人 key 不在组内 → 放行：无括号校区/学部后缀（沙面小学悦江校区）、通称差异（桥城中学）
    # 等合法挂载不受影响；法人跨区校区（七中桂花校区属七中法人）key 命中即通过。
    from school_match import coreCampusName, matchNorm
    ent_by_id = {}
    _ent_by_norm = {}
    for _e in entities:
        ent_by_id.setdefault(_e["school_id"], []).append(_e)
        _ent_by_norm.setdefault(matchNorm(coreCampusName(_e.get("name", ""))), []).append(_e)
    for _g in groups:
        _legal = set()
        for _c in _g.get("core") or []:
            _cn = matchNorm(coreCampusName(_c))
            _legal.add(_cn)
            # 组 core 实体的 aliases（法人通称，如东山培正小学 alias「培正小学」）同为组法人集合
            for _ce in _ent_by_norm.get(_cn, []):
                for _a in (_ce.get("aliases") or []):
                    _legal.add(matchNorm(coreCampusName(_a)))
        for _m in _g.get("members") or []:
            _legal.add(matchNorm(coreCampusName(_m.get("name", ""))))
            for _cp in _m.get("campuses") or []:
                _legal.add(matchNorm(coreCampusName(_cp.get("poi_name", ""))))
        _legal.add(matchNorm(coreCampusName(_g.get("brand", "").replace("教育集团", ""))))
        for _cp in _g.get("core_poi") or []:
            _sid = _cp.get("school_id")
            _ad = _sid.split("-")[1] if _sid else ""
            for _e in ent_by_id.get(_sid, []):
                _en = matchNorm(coreCampusName(_e.get("name", "")))
                _hit = _en in _legal or any(matchNorm(coreCampusName(_a)) in _legal
                                            for _a in (_e.get("aliases") or []))
                if not _hit:
                    continue  # 合法差异挂载（无括号校区/学部后缀、通称），不拦截
                # 同 key 命中但存在「法人名不同且跨行政区」实体 → 跨区同名撞车
                # （matchNorm 撞车型误并：海珠/黄埔/番禺实验小学曾归一成「实验小学」；
                # 同一法人的跨区校区如铁一越秀/白云/番禺、七中桂花校区 → 法人名相同，不撞车）
                _my_legal = coreCampusName(_e.get("name", ""))
                _cross = [x for x in _ent_by_norm.get(_en, [])
                          if x["school_id"].split("-")[1] != _ad
                          and coreCampusName(x.get("name", "")) != _my_legal]
                if _cross:
                    check(False,
                          f"[10] 跨区同名撞车: {_g['brand']} core_poi {_cp.get('poi_name')} ({_sid}) "
                          f"法人 [{_en}] 与其他行政区不同法人撞车: "
                          f"{[(x['name'], x['school_id']) for x in _cross]}")

    # ---- 11. 孤儿学校：公办 + 无招生信息 或 无升学信息（逐一排查清单 + 快照防线）----
    # 口径（按学段）：
    #   primary：招生 = 2026 小学地段招生（enrollments/2026-*.json）；升学 = 小升初出口（xiaoshengchu_2026）
    #   middle： 招生 = 2026 初中招生计划（enrollments/middle_enrollment_2026_*.json）；
    #            升学 = ranking_middle（中考指标）或 quota_matrix（名额分配）
    #   high：   招生 = 2025/2026 中考录取分数（高考升学数据项目未采集，分数为唯一信息源）
    # 孤儿 = 公办（nature != 民办）且「无招生 或 无升学」任一缺失——均属异常 case，需逐校排查。
    #
    # 【方向：孤儿数量越小越好】孤儿是「公办学校数据缺口」（无招生或无升学）的度量，
    # 是负向指标：每修复一所孤儿（补上招生/升学数据）数量就减一，这是纯正向改进。
    # 快照 digest 只锁「当前孤儿清单」，不锁数量本身。
    #
    # 【测试失败时的判断方法】修复其他模块导致孤儿数变化、本检查失败时，不要慌：
    #   1. 先看上方打印的孤儿清单，与上一版快照对比 diff：
    #      - 孤儿减少（N 所从清单消失）→ 说明那些学校的数据缺口被补上了，是改进。
    #        确认消失的都是预期修复的学校后，用 UPDATE_SNAPSHOT=1 npm run check 显式
    #        更新快照即可，不是错误。
    #      - 孤儿增加（清单出现新学校）→ 数据回退/误伤，必须排查来源（哪次改动让
    #        某所学校丢了招生或升学），修复后再更新快照；禁止直接更新快照掩盖新增。
    #      - 数量相同但名单变化（修好 A 的同时又缺了 B）→ 同样按新增排查，两条都要查。
    #   2. 判断依据永远是「孤儿清单 diff」，不是数量本身：数量不变≠没变化。
    # 快照机制（与品牌卡全量回归同款）：孤儿清单 sha256 digest 固化——存量孤儿供排查
    # （每修复一所须显式更新快照），孤儿新增/变化立即失败（数据回退防线）。
    _orphan_files = glob.glob(os.path.join(ROOT, "data/primary/enrollment/dist/2026-*.json"))
    _pri_enroll_ids = set()
    for _f in _orphan_files:
        for _r in json.load(open(_f)).get("records", []):
            if _r.get("school_id"): _pri_enroll_ids.add(_r["school_id"])
    _mid_enroll_ids = set()
    for _f in glob.glob(os.path.join(ROOT, "data/primary/enrollments/middle_enrollment_2026_*.json")):
        for _r in json.load(open(_f)).get("records", []):
            if _r.get("school_id"): _mid_enroll_ids.add(_r["school_id"])
            for _s in _r.get("school_ids") or []: _mid_enroll_ids.add(_s)
    _xs_ids = {r.get("school_id") for r in json.load(open(os.path.join(ROOT, "data/primary/transition/dist/xiaoshengchu_2026.json"))).get("records", []) if r.get("school_id")}
    _rm_ids = {s.get("school_id") for s in json.load(open(os.path.join(ROOT, "data/linkage/ranking_middle.json"))).get("schools", []) if s.get("school_id")}
    _qm_names = {s.get("school") for s in json.load(open(os.path.join(ROOT, "data/linkage/quota_matrix.json"))).get("schools", []) if s.get("school")}
    # 法人行 school_ids 也算「有升学」：校区实体升学信息聚合在法人行（school_ids 数组），
    # 避免主 id 归一（法人行主 id 指向本部后）把校区实体误判为无升学孤儿。
    _qm_school_ids = {i for s in json.load(open(os.path.join(ROOT, "data/linkage/quota_matrix.json"))).get("schools", []) for i in (s.get("school_ids") or [])}
    _sc26 = json.load(open(os.path.join(ROOT, "data/high/cutoff_score/dist/scores_2026.json"))).get("by_school_id", {})
    _sc25 = json.load(open(os.path.join(ROOT, "data/high/cutoff_score/dist/scores_2025.json"))).get("by_school_id", {})
    _orphans = []
    # 孤儿排查只看 7 区（荔湾/越秀/海珠/天河/白云/黄埔/番禺）公办学校：
    # 远郊（花都/从化/增城/南沙）与无 adcode 市属实体本就无招生/升学采集，不属于异常排查范围。
    _SEVEN_ADCODES = {'440103', '440104', '440105', '440106', '440111', '440112', '440113'}
    for _e in entities:
        if _e.get("nature") == "民办" or _e.get("stage") not in ("primary", "middle", "high"):
            continue
        _ad = (_e.get("school_id") or "?").split("-")[1] if _e.get("school_id") else "?"
        if _ad not in _SEVEN_ADCODES:
            continue
        _lacks = []
        if _e["stage"] == "primary":
            if _e["school_id"] not in _pri_enroll_ids: _lacks.append("无招生")
            if _e["school_id"] not in _xs_ids: _lacks.append("无升学")
        elif _e["stage"] == "middle":
            if _e["school_id"] not in _mid_enroll_ids: _lacks.append("无招生")
            if _e["school_id"] not in _rm_ids and _e["school_id"] not in _qm_school_ids and _e["name"] not in _qm_names: _lacks.append("无升学")
        else:  # high
            if _e["school_id"] not in _sc26 and _e["school_id"] not in _sc25: _lacks.append("无招生")
            if _lacks: _lacks.append("无升学(高考未采集)")
        if _lacks:
            _orphans.append((_e["school_id"].split("-")[1] if _e.get("school_id") else "?", _e["name"], _e["school_id"], _e["stage"], "+".join(_lacks)))
    _orphans.sort()
    _orphan_lines = [f"      {_o[0]} | {_o[1]} | {_o[2]} | {_o[3]} | {_o[4]}" for _o in _orphans]
    _section_lines.append(f"[11] 孤儿学校（公办且无招生或无升学，待逐校排查）: {len(_orphans)} 所")
    _orphan_digest = hashlib.sha256("\n".join(f"{o[0]}|{o[1]}|{o[2]}|{o[4]}" for o in _orphans).encode()).hexdigest()[:16]
    if os.environ.get("UPDATE_SNAPSHOT") == "1":
        # 注释承诺的显式更新机制：把当前孤儿清单 digest 写回本文件 ORPHAN_SNAPSHOT 常量。
        # 仅在排查确认孤儿变化符合预期（修复/冗余实体归位）时使用，禁止用于掩盖新增。
        _txt = open(__file__, encoding="utf-8").read()
        _txt, _n = re.subn(r'ORPHAN_SNAPSHOT = "[0-9a-f]{16}"',
                            f'ORPHAN_SNAPSHOT = "{_orphan_digest}"', _txt, count=1)
        if _n:
            open(__file__, "w", encoding="utf-8").write(_txt)
            print(f"[11] UPDATE_SNAPSHOT=1：孤儿快照已更新 → {_orphan_digest}")
        else:
            print(f"[11] UPDATE_SNAPSHOT=1：未找到 ORPHAN_SNAPSHOT 常量，跳过写回")
    _orphan_ok = _orphan_digest == ORPHAN_SNAPSHOT
    check(_orphan_ok,
          f"[11] 孤儿学校清单漂移: digest {_orphan_digest} != 固化 {ORPHAN_SNAPSHOT}（新增孤儿须立即排查；修复孤儿后显式更新快照）")

    # ---- 12. 同段同址冗余候选：同学段（primary/middle/high）+ 同区 + 坐标距离 ≤50m 的实体（含民办）----
    # 复用「全实体坐标检测」思路（相邻点检测，曾用于发现九年一贯/完中同址多学部）：
    # 跨学段同址（小学+初中=九年一贯、初中+高中=完中）是正常办学形态，故只看同学段；
    # 同学段同址是冗余候选（如省实荔湾 初中部/初中部一期 同址北文街2号），须逐一排查
    # （部分候选可能是有意拆分/临迁同址，如十七中西校区=原82中 2026-08 临迁培正矿泉，
    #  由人工确认后决定保留或合并，并把修正固化到 POI/实体构建脚本，禁止手改）。
    # 快照防线同孤儿：候选清单 digest 固化，新增候选立即失败（防止悄悄引入新冗余点位）。
    _POI_FILES = {
        "primary": os.path.join(ROOT, "data/poi/dist/primary_poi.json"),
        "middle": os.path.join(ROOT, "data/poi/dist/middle_poi.json"),
        "high": os.path.join(ROOT, "data/poi/dist/high_poi.json"),
    }
    _ent_by_id = {e["school_id"]: e for e in entities}
    _co = []
    for _stg, _pf in _POI_FILES.items():
        for _p in json.load(open(_pf)).get("schools", []):
            if not _p.get("school_id"):
                continue
            _ad = str(_p.get("adcode", ""))
            if _ad not in _SEVEN_ADCODES:
                continue
            _e = _ent_by_id.get(_p["school_id"])
            if _p.get("lng") and _p.get("lat"):
                _co.append((_stg, _ad, _p["school_id"], _p["name"], float(_p["lng"]), float(_p["lat"])))
    import math as _math
    def _haversine(a, b):
        _R = 6371000.0
        _p1, _p2 = _math.radians(a[5]), _math.radians(b[5])
        _dp = _math.radians(b[5] - a[5])
        _dl = _math.radians(b[4] - a[4])
        _x = _math.sin(_dp / 2) ** 2 + _math.cos(_p1) * _math.cos(_p2) * _math.sin(_dl / 2) ** 2
        return 2 * _R * _math.asin(_math.sqrt(_x))
    _co_pairs = []
    # 同址但保留（用户/业务确认）：十七中(西校区)=原82中 2026-08 起临迁培正矿泉同址办学，
    # 两校均独立存在（0912-09-17 用户确认「都应该保留」），不算冗余候选。
    _CO_LOCATED_EXEMPT = {frozenset({'gz-440104-099a5868', 'gz-440104-d6c68349'})}
    for _i in range(len(_co)):
        for _j in range(_i + 1, len(_co)):
            _a, _b = _co[_i], _co[_j]
            if _a[0] != _b[0] or _a[1] != _b[1]:
                continue
            if frozenset({_a[2], _b[2]}) in _CO_LOCATED_EXEMPT:
                continue
            _d = _haversine(_a, _b)
            if _d <= 50:
                _co_pairs.append((round(_d, 1), _a[1], _a[0], _a[2], _a[3], _b[2], _b[3]))
    _co_pairs.sort()
    _section_lines.append(f"[12] 同段同址冗余候选（同学段+同区+≤50m，含民办）: {len(_co_pairs)} 组")

    # ---- 13. 小升初记录同组同校不得重复（upgrade 产物层去重防线）----
    # 同一小学多源名（更名残留）/多条源记录（实体合并、源表重复行）解析到同一实体后，
    # 若产物仍出现同 (group_id, school_id) 多行，前端同校重复展示且无声无息。
    # 该检查锁定「upgrade_xiaoshengchu.mjs 已按 (group, school_id) 去重」这一不变量：
    # 任何源头新增同名/多记录，产物重复立即失败（如陶育路小学→陶育实验学校小学部
    # 合并后曾出现两条同校记录，2026-09-17 修复）。
    _xs_records = json.load(open(os.path.join(ROOT, "data/primary/transition/dist/xiaoshengchu_2026.json"))).get("records", [])
    _xs_keys = {}
    for _r in _xs_records:
        _sid = _r.get("school_id")
        if not _sid:
            continue  # 未解析缺口记录不参与去重判定（逐条保留可排查）
        _k = (_r.get("group_id"), _sid)
        if _k in _xs_keys:
            check(False, f"[13] 小升初同组同校重复: group_id={_k[0]} school_id={_sid}（{_xs_keys[_k]} 与后续行）")
        else:
            _xs_keys[_k] = _r.get("source_note", "")[:24]
    _section_lines.append(f"[13] 小升初同组同校重复检查: {len(_xs_keys)} 唯一组，无重复")

    _co_lines = [f"      {_p[0]:6.1f}m | {_p[1]} {_p[2]} | {_p[3]} {_p[4]}  <->  {_p[5]} {_p[6]}" for _p in _co_pairs]
    _co_digest = hashlib.sha256("\n".join(f"{p[1]}|{p[2]}|{p[3]}|{p[5]}|{p[6]}" for p in _co_pairs).encode()).hexdigest()[:16]
    if os.environ.get("UPDATE_SNAPSHOT") == "1":
        _txt = open(__file__, encoding="utf-8").read()
        _txt, _n = re.subn(r'CO_LOCATED_SNAPSHOT = "[0-9a-f]{16}"',
                            f'CO_LOCATED_SNAPSHOT = "{_co_digest}"', _txt, count=1)
        if _n:
            open(__file__, "w", encoding="utf-8").write(_txt)
            print(f"[12] UPDATE_SNAPSHOT=1：同址候选快照已更新 → {_co_digest}")
        else:
            print(f"[12] UPDATE_SNAPSHOT=1：未找到 CO_LOCATED_SNAPSHOT 常量，跳过写回")
    _co_ok = _co_digest == CO_LOCATED_SNAPSHOT
    check(_co_ok,
          f"[12] 同段同址候选漂移: digest {_co_digest} != 固化 {CO_LOCATED_SNAPSHOT}（新增同址冗余候选须立即排查；修复后显式更新快照）")

    # ---- 14. 2026 特长生计划官方口径（体育1905不含领军龙 / 艺术1741 / 领军龙116） ----
    _sp = json.load(open(os.path.join(ROOT, "data/linkage/special_matrix.json"))).get("special_plan_summary", {})
    check(_sp.get("sports") == 1905, f"[14] 特长生体育计划合计 {_sp.get('sports')} != 1905（官方口径，不含领军龙）")
    check(_sp.get("arts") == 1741, f"[14] 特长生艺术计划合计 {_sp.get('arts')} != 1741（官方口径）")
    check(_sp.get("football_special") == 116, f"[14] 领军龙足球试点计划 {_sp.get('football_special')} != 116（官方口径）")
    _section_lines.append(f"[14] 特长生计划官方口径: 体育 {_sp.get('sports')}（不含领军龙） / 艺术 {_sp.get('arts')} / 领军龙 {_sp.get('football_special')}")

    # ---- 15. 民办学校名单快照（变化即感知）----
    _minban = json.load(open(os.path.join(ROOT, "data/registry/private/dist/minban_schools.json")))
    _minban_ids = sorted(s["school_id"] for s in _minban["schools"])
    _minban_digest = hashlib.sha256("\n".join(_minban_ids).encode()).hexdigest()[:16]
    if os.environ.get("UPDATE_SNAPSHOT") == "1":
        # 与孤儿/同址同款显式更新：民办名单变化排查确认（官方来源）后写回本文件常量。
        _mtxt = open(__file__, encoding="utf-8").read()
        _mtxt, _mn = re.subn(r'PRIVATE_MINBAN_SNAPSHOT = "[0-9a-f]{16}"',
                             f'PRIVATE_MINBAN_SNAPSHOT = "{_minban_digest}"', _mtxt, count=1)
        if _mn:
            open(__file__, "w", encoding="utf-8").write(_mtxt)
            print(f"[15] UPDATE_SNAPSHOT=1：民办名单快照已更新 → {_minban_digest}（{len(_minban_ids)} 所）")
        else:
            print(f"[15] UPDATE_SNAPSHOT=1：未找到 PRIVATE_MINBAN_SNAPSHOT 常量，跳过写回")
    check(_minban_digest == PRIVATE_MINBAN_SNAPSHOT,
          f"[15] 民办名单漂移: digest {_minban_digest} != 固化 {PRIVATE_MINBAN_SNAPSHOT}（民办名单变化须先排查官方来源；确认后 UPDATE_SNAPSHOT=1 显式更新）")
    _section_lines.append(f"[15] 民办学校名单: {len(_minban_ids)} 所（快照 {_minban_digest}，变化即感知）")

    # ---- 16. 民办学校不得有公办招生/升学信息（0 容忍，有即失败）----
    # 民办学校在公办划片/派位体系里不应有：真实地段的小学招生、公办初中招生、小升初派位。
    # 民办招生计划（zone 含"民办：无地段，报名人数超计划电脑派位"等）属民办自主招生，放行。
    # 出现 → 立即失败：要么民办误标（如金海岸学校被误标民办后出现公办地段），
    # 要么民办学校被错配进公办招生/升学文件。
    _minban_ids16 = {s["school_id"] for s in json.load(open(os.path.join(ROOT, "data/registry/private/dist/minban_schools.json")))["schools"]}
    _bad_pri, _bad_mid, _bad_xs = [], [], []
    for _f in sorted(glob.glob(os.path.join(ROOT, "data/primary/enrollment/dist/2026-*.json"))):
        _d = json.load(open(_f))
        for _r in _d.get("records", []):
            if _r.get("school_id") in _minban_ids16:
                _zone = str(_r.get("zone") or "")
                if "民办" not in _zone:
                    _bad_pri.append(f"{os.path.basename(_f)} | {_r.get('school')} | {_r.get('school_id')} | zone={_zone[:60]}")
    for _f in sorted(glob.glob(os.path.join(ROOT, "data/primary/enrollments/middle_enrollment_2026_*.json"))):
        _d = json.load(open(_f))
        for _r in _d.get("records", []):
            if _r.get("school_id") in _minban_ids16:
                _bad_mid.append(f"{os.path.basename(_f)} | {_r.get('school', _r.get('name'))} | {_r.get('school_id')}")
    # 综合表 data/primary/transition/dist/xiaoshengchu_2026.json / xiaoshengchu_all.json 也纳入；
    # 民办"不参与公办派位"缺口记录（source_note/data_gaps/group 含"民办"）属正常民办升学说明，放行。
    for _f in sorted(glob.glob(os.path.join(ROOT, "data/primary/transition/dist/xiaoshengchu_*.json"))):
        _d = json.load(open(_f))
        for _r in _d.get("records", []):
            if _r.get("school_id") in _minban_ids16:
                _gap_txt = str(_r.get("source_note") or "") + str(_r.get("data_gaps") or "") + str(_r.get("group") or "")
                # 放行两类正常民办升学：①"不参与公办派位"缺口（民办/其他）；②民办小学的
                # "地段生"升公办初中对口（白云官方对口表明确列出"XX小学（地段生）"，如方圆实验小学）
                if "民办" in _gap_txt or "地段" in _gap_txt:
                    continue
                _bad_xs.append(f"{os.path.basename(_f)} | {_r.get('school', _r.get('name'))} | {_r.get('school_id')}")
    for _b in _bad_pri + _bad_mid + _bad_xs:
        check(False, f"[16] 民办学校出现公办招生/升学信息: {_b}")
    _section_lines.append(f"[16] 民办学校公办招生/升学检测: 小学 {len(_bad_pri)} 异常 / 初中 {len(_bad_mid)} 异常 / 小升初 {len(_bad_xs)} 异常（民办自主招生计划放行，0 容忍）")

    # ---- 17. 番禺民办条目必须全部官方源（防手工名单）----
    # 番禺有官方文件（2026 义务教育民办招生计划 sheet + 广州市中考批次民办高中名单），
    # 民办名单必须由 build_minban_official.py 自动解析生成；md/手工不得直接追加番禺
    # （金海岸学校误标民办即为 md 手工追加所致）。manual/legacy 的番禺条目 → 失败。
    _panyu_entries = [s for s in json.load(open(os.path.join(ROOT, "data/registry/private/dist/minban_schools.json")))["schools"]
                      if s["school_id"].startswith("gz-440113")]
    _panyu_manual = [f"{s['school_id']} | {s.get('name')} | {s.get('source_type')}"
                     for s in _panyu_entries if not s.get("source_type", "").startswith("official")]
    for _b in _panyu_manual:
        check(False, f"[17] 番禺民办条目非官方源（番禺只能官方解析，禁止手工名单）: {_b}")
    _section_lines.append(f"[17] 番禺民办条目: {len(_panyu_entries) - len(_panyu_manual)}/{len(_panyu_entries)} 官方源"
          f"（manual/legacy {len(_panyu_manual)}，0 容忍）")

    # ---- 18. 实体名不得为招生/报名点位（防"招生处"点位实体回归）----
    # 高德 POI 常采集「XX学校招生处/招生办/报名点」等非学校点位（如星执学校小学招生处
    # a36980e5 曾误建实体，与执信中学附属小学同址），build_entities NON_SCHOOL_POI 已过滤；
    # 此处兜底：实体表再出现点位后缀 → 失败（0 容忍）。
    _poi_like = [f"{e['school_id']} | {e['name']}" for e in json.load(open(os.path.join(ROOT, "data/registry/entity/dist/entities.json")))["entities"]
                 if any(x in e['name'] for x in ('招生处', '招生办', '报名点', '报名处', '招生点'))]
    for _b in _poi_like:
        check(False, f"[18] 实体名为招生/报名点位（非学校，应被 build_entities 过滤）: {_b}")
    _section_lines.append(f"[18] 实体点位后缀检测: {len(_poi_like)} 异常（0 容忍，build_entities NON_SCHOOL_POI 兜底）")

    # ---- 19. 初中明细 group 必须由公共产物 schoolGroups 支撑（纯 id 一致性）----
    # build_ranking_middle.py 的 group 只查 data/registry/group/dist/school_groups.json（纯 id）；
    # 任何有 group 的明细行，其 school_id / school_ids 中至少一个必须命中产物且 brand 一致，
    # 否则说明产物漏收（该学校会从集团分组丢失）。无 school_id 的行不应有 group
    # （名称匹配已从运行时删除；如三元里中学 = entities 无实体，属待补真源的数据缺口）。
    _sg = json.load(open(os.path.join(ROOT, "data/registry/group/dist/school_groups.json")))["schoolGroups"]
    _rm = json.load(open(os.path.join(ROOT, "data/linkage/ranking_middle.json")))["schools"]
    _orphan = 0
    for _s in _rm:
        _g = _s.get("group") or {}
        if not _g:
            continue
        _ids = [i for i in [_s.get("school_id")] + list(_s.get("school_ids") or []) if i and i in _sg]
        if not _ids:
            _orphan += 1
            check(False, f"[19] 明细 {_s['name']} 有 group 但 school_id(s) 无 school_groups 产物支撑: {_g.get('brand')}")
        elif _sg[_ids[0]]["brand"] != _g["brand"]:
            check(False, f"[19] 明细 {_s['name']} 产物 brand 不一致: 产物={_sg[_ids[0]]['brand']} 明细={_g['brand']}")
    _section_lines.append(f"[19] 明细分组-产物一致性: {sum(1 for s in _rm if s.get('group'))} 有 group，{_orphan} 孤儿（0 容忍）")

    # ---- 汇总：通过时只输出一行结论；失败时逐项输出各序号概要 + 明细 + 失败项 ----
    if failures:
        print("\n".join(_section_lines))
        if not _orphan_ok:
            print()
            print("\n".join(_orphan_lines))
        if not _co_ok:
            print()
            print("\n".join(_co_lines))
        print(f"\n数据质量测试: {checks} 项检查, {len(failures)} 项失败")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("✓ 数据质量测试通过")

if __name__ == "__main__":
    main()
