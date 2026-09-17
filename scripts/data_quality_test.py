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
ORPHAN_SNAPSHOT = "ea858a5979f84737"
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
    # 用户口径（2026-09）：别名非主键可重复；裸名「同区+学段+主校区」可唯一收敛
    # （resolve by_main 优先无括号主 POI）→ 只要冲突实体中存在无括号主名即放行；
    # 仅当冲突双方都带校区括号（无主 POI 可收敛，如「广钢校区」vs「岭南校区」裸名撞）才报错。
    entities = load_entities()
    alias_owner = {}  # alias -> (school_id, adcode, stage, 该实体名是否无括号)
    for ent in entities:
        # 纯名 = 无括号/无校区限定词的别名
        adcode = ent["school_id"].split("-")[1] if ent.get("school_id") else ""
        stage = ent.get("stage")
        has_main = "(" not in ent.get("name", "") and "（" not in ent.get("name", "")
        for a in ent.get("aliases", []):
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
    _orphan_files = glob.glob(os.path.join(ROOT, "data/primary/enrollments/2026-*.json"))
    _pri_enroll_ids = set()
    for _f in _orphan_files:
        for _r in json.load(open(_f)).get("records", []):
            if _r.get("school_id"): _pri_enroll_ids.add(_r["school_id"])
    _mid_enroll_ids = set()
    for _f in glob.glob(os.path.join(ROOT, "data/primary/enrollments/middle_enrollment_2026_*.json")):
        for _r in json.load(open(_f)).get("records", []):
            if _r.get("school_id"): _mid_enroll_ids.add(_r["school_id"])
            for _s in _r.get("school_ids") or []: _mid_enroll_ids.add(_s)
    _xs_ids = {r.get("school_id") for r in json.load(open(os.path.join(ROOT, "data/primary/xiaoshengchu_2026.json"))).get("records", []) if r.get("school_id")}
    _rm_ids = {s.get("school_id") for s in json.load(open(os.path.join(ROOT, "data/linkage/ranking_middle.json"))).get("schools", []) if s.get("school_id")}
    _qm_names = {s.get("school") for s in json.load(open(os.path.join(ROOT, "data/linkage/quota_matrix.json"))).get("schools", []) if s.get("school")}
    # 法人行 school_ids 也算「有升学」：校区实体升学信息聚合在法人行（school_ids 数组），
    # 避免主 id 归一（法人行主 id 指向本部后）把校区实体误判为无升学孤儿。
    _qm_school_ids = {i for s in json.load(open(os.path.join(ROOT, "data/linkage/quota_matrix.json"))).get("schools", []) for i in (s.get("school_ids") or [])}
    _sc26 = json.load(open(os.path.join(ROOT, "data/high/scores_2026.json"))).get("by_school_id", {})
    _sc25 = json.load(open(os.path.join(ROOT, "data/high/scores_2025.json"))).get("by_school_id", {})
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
    print(f"\n[11] 孤儿学校（公办且无招生或无升学，待逐校排查）: {len(_orphans)} 所")
    for _o in _orphans:
        print(f"      {_o[0]} | {_o[1]} | {_o[2]} | {_o[3]} | {_o[4]}")
    _orphan_digest = hashlib.sha256("\n".join(f"{o[0]}|{o[1]}|{o[2]}|{o[4]}" for o in _orphans).encode()).hexdigest()[:16]
    check(_orphan_digest == ORPHAN_SNAPSHOT,
          f"[11] 孤儿学校清单漂移: digest {_orphan_digest} != 固化 {ORPHAN_SNAPSHOT}（新增孤儿须立即排查；修复孤儿后显式更新快照）")

    # ---- 汇总 ----
    print(f"数据质量测试: {checks} 项检查, {len(failures)} 项失败")
    if failures:
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("  ✓ 全部通过")

if __name__ == "__main__":
    main()
