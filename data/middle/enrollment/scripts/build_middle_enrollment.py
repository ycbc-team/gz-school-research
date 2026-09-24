#!/usr/bin/env python3
"""构建 2026 各区公办初中招生计划离线库（初中视角）。

输出（2026-09-23 分层调整）:
  中间统一格式（各区独立，审计层）: data/middle/enrollment/parsed/middle_enrollment_2026/middle_enrollment_2026_<district>.json
  最终合并一份（前端运行时消费）:  data/middle/enrollment/dist/middle_enrollment_2026.json
                                  {"year": 2026, "note": ..., "districts": {"<district>": {...snapshot...}, ...}}
  支持 --out-dir DIR：全部输出到临时目录（快照测试用，不碰工作区）

数据源（按区，2026-09-23 迁入 data/middle/enrollment 分层）:
  番禺 panyu : 共享转录 data/primary/enrollment/parsed/_transcripts/panyu_2026_official.json
               "公办初中招生范围、计划" sheet（官方 xls 小学+初中+民办共用，权威源留在小学 enrollment）
  白云 baiyun: parsed/_transcripts/baiyun_2026_juniors.json（官方源 xlsx 与小学共享，raw 在
               data/enrollment/raw/baiyun_2026_official.xlsx，见 parse_baiyun_juniors.py）
  荔湾 liwan : parsed/_transcripts/liwan_2026_groups.json（派位组，共享 raw/liwan_2026_a3.docx，见 parse_liwan_groups.py）
  越秀/海珠/天河/黄埔: data/primary/transition/dist/xiaoshengchu_<district>.json 反推
               （班数/范围 raw 未抽，留空）

mechanism 枚举（区级定义，UI 据此渲染）:
  single_zone     单校划片（对口直升/直接安排，无落选概念）
  group_paidui    多校电脑派位（组内学校兜底，不安排到组外）
  single_lottery  单校电脑抽签（自愿报名+超额抽签，未中签回原学区）
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
RAW = os.path.join(ROOT, "data", "middle", "enrollment", "parsed", "_transcripts")  # 本业务初中转录
RAW_PANYU = os.path.join(ROOT, "data", "primary", "enrollment", "parsed", "_transcripts")  # 番禺共享转录（官方 xls 4 sheets：小学/初中/民办共用）
OUT = os.path.join(ROOT, "data", "middle", "enrollment", "dist")  # 最终合并产物（前端消费）
OUT_PARSED = os.path.join(ROOT, "data", "middle", "enrollment", "parsed", "middle_enrollment_2026")  # 中间统一格式（各区独立，审计层）

# 复用项目统一的 POI 匹配服务（data/registry/entity/scripts/school_match.py，实体表别名优先 + 行政区/学段收敛，不另起 norm 逻辑）
sys.path.insert(0, os.path.join(ROOT, "data/registry/entity/scripts"))
from school_match import SchoolMatcher as _SchoolMatcher

_MATCHER = _SchoolMatcher.load()

def match_school_ids(name, adcode=None):
    """官方名单校名 → (school_id, school_ids)。统一走 SchoolMatcher（实体表别名优先，业务侧无别名表）。
    adcode=本区 adcode：优先命中本区 POI，避免跨区同名校（如铁英学校/广大附中）被错配到异区校区。
    语义（SchoolMatcher resolve_all 契约）：
      - 官方只写法人名（无校区限定，如「广州市天河外国语学校」）→ 展开同一法人全部 middle 校区，
        多校区时 school_id=None + school_ids=[全部校区]（前端 byIdAll 全量索引，各校区详情页均可查到）
      - 官方写明校区（含括号，如「执信中学（执信路校区）」）→ 精准单校区
    SCHOOL_NORM 先归一官方转录名 → 实体表标准名；MIDDLE_ANCHORS 仅显式宁缺（None）。"""
    if not name:
        return None, None
    name = SCHOOL_NORM.get(name, name)
    if name in MIDDLE_ANCHORS:
        return MIDDLE_ANCHORS[name], None
    _campus_suffix = ("校区", "分校", "教学点", "分教点", "分部", "校本部", "初中部", "高中部", "小学部")
    if re.search(r"[（(].+?[）)]", name) or name.endswith(_campus_suffix):
        # 带校区/学部限定（括号式或后缀式）：精准匹配该校区/学部实体，宁缺毋滥（不展开其它校区）。
        # 「校本部/初中部/高中部/小学部」是无括号后缀限定（官方明确指该校区/学部），
        # 不得按法人名展开全部校区（如「广州市第一中学初中部」只指初中部实体）。
        r = _MATCHER.resolve(name, preferred_adcode=adcode, preferred_stage="初中")
        return (r.get("school_id") or None), None
    # 无校区限定：法人全部校区展开（单校区回退 school_id；多校区 school_ids）
    ra = _MATCHER.resolve_all(name, preferred_adcode=adcode, preferred_stage="初中")
    ids = [r["school_id"] for r in ra]
    if len(ids) == 1:
        return ids[0], None
    if len(ids) > 1:
        return None, sorted(ids)
    return None, None


# 历史修正/官方裸名 → 法人主校区锚定（resolve 宁缺、跨区吸附或漂移时固化；None=显式宁缺）。
# 来源：HEAD 初中计划 json 的历史人工/旧匹配器 id（用户纪律：历史修正固化进脚本，不可被覆盖成错误结果）
MIDDLE_ANCHORS = {
    # 2026-09-18 起：原 8 条官方裸名/校区锚定已全部下沉到实体表别名（OFFICIAL_MIDDLE_ALIAS /
    # SchoolMatcher 收敛规则：同区唯一优先、2a0 学段过滤），本表仅保留显式宁缺（None=resolve 会错配，宁缺毋滥）。
    "广州市三元里中学": None,                      # POI 无独立实体，resolve 吸附大学校区 → 宁缺
    "广东第二师范学院广州南站附属学校": None,       # resolve 命中小学（跨学段）→ 宁缺
}

# 官方转录名 → 实体表标准名（仅剩显示归一；匹配已全部由实体表别名承接）。
# 2026-09-23 下沉：官方阿拉伯数字简称（第18/113/75/89中学）已建实体表别名
# （SHARED_LEGAL_ALIAS/OFFICIAL_MIDDLE_ALIAS），CPPQ 全角中点·变体已入 EXTRA_ENTITY_ALIAS——
# 本表不再承担匹配别名，仅剩 3 条「括号/学部」条目做 school 字段全称显示归一
# （这三条匹配上已由实体表别名/adcode 收敛覆盖，SchoolMatcher 去括号后可直接命中，
#  保留仅为 school 字段与详情显示口径一致）。
SCHOOL_NORM = {
    # 匹配已由实体表别名承接；以下仅为显示归一（school 字段用全称，与反推版口径对齐）
    "广州市华颖外国语学校（广州市华颖中学）": "广州市华颖外国语学校",
    "暨南大学附属实验学校": "暨南大学附属实验学校（初中部）",    # 企事业行（附件7）；历史反推用带（初中部）名
    "华南师范大学附属中学": "华南师范大学附属中学初中部",        # 企事业行本部（天河石牌）；实体表 440106+初中 收敛即命中初中部
    "广州奥林匹克中学（含智谷校区）": "广州奥林匹克中学",              # 官方「含智谷校区」= 主校黄村西路 + 智谷校区（2026-09-24 修复：此前只挂智谷，黄村西路校区详情无招生）；归一后 resolve_all 双校区命中
}
# SCHOOL_ID_ANCHOR 已废弃（2026-09-23）：历史业务侧锚定全部下沉实体表别名——
# 清华附中湾区学校（智谷校区）/暨南大学附属实验学校（初中部）/广州市天河区暨南第一实验学校
# 均已在 build_entities.py OFFICIAL_MIDDLE_ALIAS 建别名，由 SchoolMatcher 统一命中；不再保留业务别名表。

# 派位组显示名：从机制备注提取组号，统一「电脑派位第N组」（越秀中文序数/海珠阿拉伯/荔湾无第字/番禺无号）。
# 小学升学 Badge 曾用小学侧组名（「XX区小升初第N组（电脑派位）」），直建后初中侧组号在 mechanism_note；
# 归一为简洁「电脑派位第N组」供前端 Badge（用户 2026-09-23 要求接回组信息）。
_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

def _cn2num(raw):
    if raw == "十":
        return 10
    if len(raw) == 1:
        return _CN_NUM.get(raw, 0)
    if raw.startswith("十"):          # 十一 → 11 … 十九 → 19（越秀 11 组上限）
        return 10 + _CN_NUM.get(raw[1:], 0)
    return 0

def _primary_ids(name, adcode):
    """转录小学名 → school_id 列表：统一走 SchoolMatcher（preferred_stage='小学'）——
    官方「法人名（校区A、校区B…）」多选项形态（括号内顿号/逗号分隔 >1 项，或含「、」）
    走第三种匹配 resolve_campus_list（去括号展开候选 + 与括号内选项逐项匹配，只保留
    命中的校区，不误配括号外校区）；单选项/无括号回退 resolve_all（法人全等展开 /
    带单校区限定精准）。按本区 adcode 过滤，不跨区错配。"""
    ra = _MATCHER.resolve_campus_list(name, preferred_adcode=adcode, preferred_stage="小学")
    if not ra:
        ra = _MATCHER.resolve_all(name, preferred_adcode=adcode, preferred_stage="小学")
    return sorted({r["school_id"] for r in ra})

_SCOPE_SPLIT = re.compile(r"[、，,;；]")
# 小学名形态后缀：只对"看起来是小学名"的段做实体匹配，避免划片地段/楼盘/招生条件文本
# 拆段后的零碎词（如「金山谷」「车陂路以东」「…小学应届毕业生」）被 SchoolMatcher 宽松命中造成误跳转。
# 带限定词的段（「XX小学（地段生）」「…（不含北校区）」）宁缺毋滥：不匹配则前端保留文本展示。
_EDU_SUFFIX = ("小学", "学校", "中学", "学院", "幼儿园", "小学部", "初中部", "高中部",
               "校区", "分校", "教学点", "分部", "附中", "附小", "职中",
               "一小", "二小", "三小", "四小", "五小", "六小", "七小", "八小", "九小", "十小")

def _scope_primary_ids(scope, adcode):
    """直升小学 scope → {小学名: school_ids}（数据层匹配，前端聚合为可点击行）：
    按顿号/逗号拆段，逐段 SchoolMatcher 匹配小学实体（preferred_stage='小学'）。
    仅匹配「小学名形态」（教育词后缀）的段——划片地段/说明文本（天河/番禺/白云部分）
    匹配不到则整体不输出，前端对该记录保留『招生服务范围』文本展示。宁缺毋滥：匹配不到不猜。"""
    if not scope:
        return {}
    out = {}
    for part in _SCOPE_SPLIT.split(scope):
        part = part.strip()
        if not part or len(part) > 28:
            continue
        t = part.rstrip("。；;，,、 ）】]}\u3000 ").rstrip("）")
        if not t.endswith(_EDU_SUFFIX):
            continue
        ids = _primary_ids(part, adcode)
        if ids:
            out[part] = ids
    return out or None

def _group_name(note):
    """机制备注 → 派位组显示名（「电脑派位第N组」）；无组号（番禺）→「电脑派位」。"""
    m = re.search(r"第\s*([一二三四五六七八九十\d]+)\s*组", note or "")
    if not m:
        m = re.search(r"([一二三四五六七八九十\d]+)\s*组", note or "")  # 荔湾「1组电脑派位」无「第」
    if not m:
        return "电脑派位"
    raw = m.group(1)
    n = int(raw) if raw.isdigit() else _cn2num(raw)
    return f"电脑派位第{n}组" if n else "电脑派位"

# 区键 → adcode（SchoolMatcher 匹配用：按本区过滤，不跨区错配）
_DK_ADCODE = {"yuexiu": "440104", "haizhu": "440105", "tianhe": "440106",
              "huangpu": "440112", "panyu": "440113", "baiyun": "440111", "liwan": "440103"}

# 区级枚举定义：UI 直接用 label / lose_text
MECHANISMS = {
    "single_zone":    {"label": "单校划片",     "can_lose": False, "lose_text": None},
    "group_paidui":   {"label": "多校电脑派位", "can_lose": False, "lose_text": "派位组内学校随机分配，组内兜底，不安排到组外。"},
    "single_lottery": {"label": "单校电脑抽签", "can_lose": True,  "lose_text": "符合报名条件 ≠ 一定录取。报名人数超计划时由区教育局统一组织电脑抽签；未中签者按区招生简章回户籍地学区申请入读公办初中，不保证安排到本校。"},
    "no_plan":        {"label": "2026 无招生计划", "can_lose": False, "lose_text": None},
}

# ---------- 番禺 ----------
def build_panyu():
    d = json.load(open(os.path.join(RAW_PANYU, "panyu_2026_official.json")))
    rows = d["sheets"]["公办初中招生范围、计划"]
    src_url = d["source"]
    recs = []
    group_tail = ""  # 学区列空则沿用上一行
    for r in rows[3:]:  # 跳表头3行
        school = (r[1] or "").strip()
        if not school or school.startswith("说明"): continue
        plan = r[2]
        scope = (r[3] or "").strip()
        note = (r[4] or "").strip()
        try:
            plan_n = int(float(plan)) if plan else None
        except: plan_n = None

        if "电脑抽签" in note:
            mech = "single_lottery"
        elif "电脑派位" in note:
            mech = "group_paidui"
        else:
            mech = "single_zone"

        # 亚运城派位组成员从备注提取
        members = None
        if mech == "group_paidui" and "铁英" in note:
            members = ["广铁一中番禺校区", "广铁一中铁英学校(西校区)", "广铁一中铁英学校(东校区)"]
        # 市桥城区多校派位组（番实验+其他7校）
        if mech == "group_paidui" and school == "番禺区实验中学":
            members = ["广东仲元中学一校区（初中部）","广东番禺中学附属学校","番禺区实验中学","市桥东风中学","市桥侨联中学","市桥星海中学","市桥桥城中学","市桥桥兴中学"]

        sid, sids = match_school_ids(school, "440113")
        # 铁英学校 = 东/西两校区合计 28 班（官方无单校区拆分）：school_id 置 None，school_ids 列出两校区，
        # 两个校区的详情页共用这一套招生计划
        if school == "广铁一中铁英学校":
            sid = None
            sids = ["gz-440113-43d027a5", "gz-440113-94c76638"]
            # 官方原文：番禺校区行备注「电脑派位；铁英学校西校区招生计划14个班，铁英学校东校区
            # 招生计划14个班」——铁英学校（东/西）与番禺校区同属亚运城配建初中电脑派位组，
            # 并非单校划片（本行备注列为空，走默认分支会误判为 single_zone）。
            mech = "group_paidui"
            members = ["广铁一中番禺校区", "广铁一中铁英学校(西校区)", "广铁一中铁英学校(东校区)"]
            scope = "亚运城户籍的小学应届毕业生（必须是业主子女身份）。"
            note = "电脑派位；与广铁一中番禺校区同组（见番禺校区行备注）。"
        # 仲元二校区（大龙街）：官方明文「二校区（初中部）」10 班 450 人（电脑派位），
        # 实体 gz-440113-6dbdc462 存在（middle POI 表在列，无独立地址点位）；
        # 挂独立实体 id——官方明文办初中，孤儿宁缺原则不适用（有官方招生记录）
        if school == "广东仲元中学二校区（初中部）":
            sid = "gz-440113-6dbdc462"
        # 广东第二师范学院广州南站附属学校（石壁街钟韦大道144号，10 班单校划片）：
        # 实体+POI 已补（2026-09-24），显式挂 id 消除 school_id=None 悬空
        if school == "广东第二师范学院广州南站附属学校":
            sid = "gz-440113-0bb52d06"
        _ss = _scope_primary_ids(scope, "440113") if scope else None
        recs.append({
            "school": school, "school_id": sid,
            **({"school_ids": sids} if sids else {}),
            "plan_classes": plan_n, "scope": scope,
            **({"scope_school_ids": _ss} if _ss else {}),
            "mechanism": mech, "mechanism_note": note or None,
            "group_members": members,
        })
    # 区属初中面向全区（或属地镇街）招生简章批次（2026-09-24 补解析，转录 panyu_2026_quju.json）：
    # 自愿报名、超计划电脑抽签；中签自动取消属地正常安排的学位、未中签回户籍地学区 → single_lottery。
    # 与计划表（属地划片/派位）互补，同校并存为两种机制（如仲元一校区 市桥划片 + 面向全区抽签）。
    quju = json.load(open(os.path.join(RAW, "panyu_2026_quju.json")))
    for q in quju["records"]:
        qsid, qsids = match_school_ids(q["school"], "440113")
        qnote = (f"区属初中{q['batch']}批次：招生 {q['plan_people']} 人（自愿报名，超计划电脑抽签；"
                 f"中签自动取消属地正常安排的学位，未中签回户籍地学区）。{q['note']}")
        recs.append({
            "school": q["school"], "school_id": qsid,
            **({"school_ids": qsids} if qsids else {}),
            "plan_classes": None, "scope": None,
            "mechanism": "single_lottery", "mechanism_note": qnote,
            "group_members": None,
        })
    return {
        "year": 2026, "district": "番禺区",
        "source": "番禺区教育局《2026年番禺区义务教育阶段学校招生计划、招生地段及条件》+《2026年番禺区区属初中面向全区招生简章》",
        "source_url": src_url,
        "records": recs,
    }

# ---------- 白云 ----------
def build_baiyun():
    raw = json.load(open(os.path.join(RAW, "baiyun_2026_juniors.json")))
    recs = []
    for r in raw:
        school = (r.get("school") or "").strip()
        if not school: continue
        try: plan_n = int(r.get("plan")) if r.get("plan") else None
        except: plan_n = None
        feed = (r.get("feed") or "").strip()
        note = (r.get("note") or "").strip()
        # 机制判断
        if "摇号" in feed or "摇号" in note:
            mech = "group_paidui"
        elif feed.count("、") >= 2 or feed.count(",") >= 2:
            mech = "group_paidui"
        else:
            mech = "single_zone"
        sid, sids = match_school_ids(school, "440111")
        # 三元里中学（2026 涉拆迁停招，官方地址三元里群英大街34号）：实体+POI 已补，显式挂 id
        if school == "广州市三元里中学":
            sid = "gz-440111-8629621c"
        # 明德校区+同德校区合并招生（官方同一条记录）：school_id 置 None，school_ids 列出两校区共担
        if school == "广州市第六十五中学（明德校区、同德校区）":
            sid = None
            sids = ["gz-440111-c8461d5d", "gz-440111-c7b90869"]
        _ss = _scope_primary_ids(feed, "440111") if feed else None
        recs.append({
            "school": school, "school_id": sid,
            **({"school_ids": sids} if sids else {}),
            "plan_classes": plan_n, "scope": feed or None,
            **({"scope_school_ids": _ss} if _ss else {}),
            "mechanism": mech, "mechanism_note": note or None,
            "group_members": None,
        })
    return {
        "year": 2026, "district": "白云区",
        "source": "白云区教育局 2026 公办初中招生计划（parsed/_transcripts/baiyun_2026_juniors.json）",
        "source_url": None,
        "records": recs,
    }

# ---------- 荔湾（官方派位组表，2026-09-23 改按组逐条：替代历史一校并集式） ----------
def build_liwan():
    """荔湾：官方派位组表 15 组（转录 liwan_2026_groups.json，组×中学×对口小学三列）。
    每组成员逐条记录（一校多规则：同一初中可属多组），对口小学列 → groups[gid].primaries。
    历史实现按 school 合并成员并集（组号丢失、官方组结构失真），本次改为与越秀/海珠同款逐组直建。
    2026-09-24：补解析附件1 计划表（liwan_2026_plan.json，raw/liwan_2026_a1.docx）——派位组记录注入
    官方班数；计划表有但派位组无的学校（协和学校初中部等）单列 single_zone 记录（此前整表未解析，
    荔湾全部班数缺失、协和学校详情页误显示无招生）。"""
    raw = json.load(open(os.path.join(RAW, "liwan_2026_groups.json")))
    plan = json.load(open(os.path.join(RAW, "liwan_2026_plan.json")))
    plan_map = {r["school"].strip(): r["plan"] for r in plan["records"]}
    recs = []
    for g in raw:
        cells = g.get("cells", [])
        if len(cells) < 3: continue
        group_name = cells[0][0] if cells[0] else ""
        if not re.match(r"^\d+组$", group_name): continue  # 跳过表头行
        members = [s.strip() for s in cells[1] if s.strip()]
        if not members: continue
        # 小学列官方文本跨行拼接；括号内顿号保护（「（竹苑校区、绿森林校区）」不被拆散）
        raw_pri = "".join(cells[2])
        raw_pri = re.sub(r"（[^（）]*）", lambda m: m.group(0).replace("、", "\u0001").replace(",", "\u0002").replace("，", "\u0003"), raw_pri)
        primaries = [p.replace("\u0001", "、").replace("\u0002", ",").replace("\u0003", "，").strip()
                     for p in re.split(r"[、,，]", raw_pri) if p.strip()]
        note = f"荔湾区{group_name}电脑派位"
        for m in members:
            recs.append({
                "school": m, "school_id": None, "plan_classes": plan_map.get(m.strip()), "scope": None,
                "mechanism": "group_paidui", "mechanism_note": note,
                "group_members": members, "_group_primaries": primaries or None,
            })
    for r in recs:
        _sid, _sids = match_school_ids(r["school"], "440103")
        r["school_id"] = _sid
        if _sids:
            r["school_ids"] = _sids
    # 附件1 计划表有、派位组无的学校：市属/单列（协和学校初中部等），单列 single_zone 记录
    group_schools = {r["school"].strip() for r in recs}
    for r in plan["records"]:
        nm = r["school"].strip()
        if nm in group_schools:
            continue
        _sid, _sids = match_school_ids(nm, "440103")
        recs.append({
            "school": nm, "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": r["plan"], "scope": None,
            "mechanism": "single_zone",
            "mechanism_note": "2026 荔湾区公办初中一年级招生计划（附件1）单列，不在电脑派位分组表内。",
            "group_members": None,
        })
    return {
        "year": 2026, "district": "荔湾区",
        "source": "荔湾区教育局 2026 公办初中招生派位组表（parsed/_transcripts/liwan_2026_groups.json）+ 附件1 公办初中一年级招生计划（raw/liwan_2026_a1.docx，转录 liwan_2026_plan.json）",
        "source_url": None,
        "records": recs,
    }

# ---------- 从 xiaoshengchu 反推（越秀/海珠/天河/黄埔） ----------
def build_from_xiaoshengchu(district_key, district_name, adcode):
    xs = json.load(open(os.path.join(ROOT, "data", "primary", "transition", "dist", f"xiaoshengchu_{district_key}.json")))
    # 初中名 -> 记录
    rec_map = {}
    # 派位组：group 名 -> 成员初中列表
    group_members_map = {}
    for r in xs["records"]:
        group = r.get("group") or ""
        juniors = r.get("feed_junior_highs") or []
        if not juniors: continue
        for j in juniors:
            if j not in rec_map:
                rec_map[j] = {"school": j, "school_id": None, "plan_classes": None,
                              "scope": None, "mechanism": None,
                              "mechanism_note": None, "group_members": None}
            # 机制判定：先排除"不参加电脑派位"，再判派位/直升
            if "不参加" in group or "不参与" in group:
                continue
            elif "对口直升" in group or "单校" in group or "九年制" in group or "内部直升" in group:
                mech = "single_zone"
            elif "电脑派位" in group or "多校" in group:
                mech = "group_paidui"
            else:
                mech = "group_paidui"
            # 同一初中在多个小学记录里出现，取最严格机制（single_lottery > group_paidui > single_zone）
            order = {"single_zone":1, "group_paidui":2, "single_lottery":3}
            cur = rec_map[j]["mechanism"]
            if cur is None or order.get(mech,0) > order.get(cur,0):
                rec_map[j]["mechanism"] = mech
                rec_map[j]["mechanism_note"] = group
            # 组内成员：同一 group 名下的所有初中
            if mech == "group_paidui":
                group_members_map.setdefault(group, set()).add(j)
    # 回填 group_members；mechanism 为 None 的（"不参加电脑派位"记录里的初中）默认 single_zone
    for j, rec in rec_map.items():
        if rec["mechanism"] is None:
            rec["mechanism"] = "single_zone"
            rec["mechanism_note"] = "对口直升（不参加电脑派位）"
        if rec["mechanism"] == "group_paidui" and rec["mechanism_note"]:
            rec["group_members"] = sorted(group_members_map.get(rec["mechanism_note"], set()))
    recs = []
    for j, r in rec_map.items():
        _sid, _sids = match_school_ids(j, adcode)
        r["school_id"] = _sid
        if _sids:
            r["school_ids"] = _sids
        recs.append(r)
    return {
        "year": 2026, "district": district_name,
        "source": f"由 xiaoshengchu_{district_key}.json 反推（历史参照，已被官方直建替代）",
        "source_url": None,
        "records": recs,
    }

# ============================================================
# 4 区官方直建（2026-09-23 转录就绪后切换，替代 build_from_xiaoshengchu 反推）
# 官方口径：组结构/班数/范围直接来自 parsed/_transcripts/<区>_2026_juniors.json
# 派位组对口小学（primaries）走 groups 表（record._group_primaries → groups[gid].primaries），避免组内重复
# ============================================================

def build_yuexiu_official():
    """越秀：2022 官方分组表 11 组×10 初中（程序化 parse）+ 细则 8 直升。无班数/范围列。"""
    tr = json.load(open(os.path.join(RAW, "yuexiu_2026_juniors.json")))
    recs = []
    for g in tr["groups"]:
        members = g["juniors"]
        note = f"越秀区小学升初中电脑派位第{g['group']}组（组内 10 所初中均可填报）"
        for j in members:
            _sid, _sids = match_school_ids(j, "440104")
            recs.append({
                "school": SCHOOL_NORM.get(j, j), "school_id": _sid,
                **({"school_ids": _sids} if _sids else {}),
                "plan_classes": None, "scope": None,
                "mechanism": "group_paidui", "mechanism_note": note,
                "group_members": members, "_group_primaries": g["primaries"],
            })
    # 直升（细则第九条）：已派位的初中追加 single_zone 直升规则（一校多规则，官方真实并存）
    for pri, junior in tr["direct_feed"].items():
        _sid, _sids = match_school_ids(junior, "440104")
        _ss = _scope_primary_ids(pri, "440104") if pri else None
        recs.append({
            "school": SCHOOL_NORM.get(junior, junior), "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": None, "scope": pri,
            **({"scope_school_ids": _ss} if _ss else {}),
            "mechanism": "single_zone", "mechanism_note": "对口直升（2026 义务教育招生细则第九条）",
            "group_members": None,
        })
    return {
        "year": 2026, "district": "越秀区",
        "source": "2022 官方分组表 + 2026 细则（parse_yuexiu_juniors.py 程序化转录）",
        "source_url": "http://www.yuexiu.gov.cn/gzjg/qzf/qjyj/jyzl/gk/zswd/content/post_8301356.html",
        "records": recs,
    }

def build_haizhu_official():
    """海珠：问答附件1 派位 10 组 + 正文直升 19 + 计划表 28 校班数。"""
    tr = json.load(open(os.path.join(RAW, "haizhu_2026_juniors.json")))
    group_prim = {}
    # prim_group 值是 int（组号），groups 键是 str（'1'）→ 统一 str 再索引，否则对口小学全丢
    for pri, gid in tr["prim_group"].items():
        group_prim.setdefault(str(gid), []).append(pri)
    plan_classes = tr["plan_classes"]
    recs = []
    for gid, members in tr["groups"].items():
        note = f"海珠区 2026 年公办初中普通电脑派位第{gid}组"
        for j in members:
            _sid, _sids = match_school_ids(j, "440105")
            recs.append({
                "school": SCHOOL_NORM.get(j, j), "school_id": _sid,
                **({"school_ids": _sids} if _sids else {}),
                "plan_classes": plan_classes.get(j), "scope": None,
                "mechanism": "group_paidui", "mechanism_note": note,
                "group_members": members, "_group_primaries": group_prim.get(gid),
            })
    for pri, junior in tr["direct_feed"].items():
        _sid, _sids = match_school_ids(junior, "440105")
        _ss = _scope_primary_ids(pri, "440105") if pri else None
        recs.append({
            "school": SCHOOL_NORM.get(junior, junior), "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": plan_classes.get(junior), "scope": pri,
            **({"scope_school_ids": _ss} if _ss else {}),
            "mechanism": "single_zone", "mechanism_note": "对口直升（初中招生问答正文）",
            "group_members": None,
        })
    return {
        "year": 2026, "district": "海珠区",
        "source": "2026 初中招生问答附件1 派位组 + 正文直升 + 公办初中招生计划表",
        "source_url": "https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html",
        "records": recs,
    }

def build_tianhe_official():
    """天河：附件6 公办 24（划片范围+班数）+ 附件7 企事业 3 + 附件8 民办初中部 24。"""
    tr = json.load(open(os.path.join(RAW, "tianhe_2026_juniors.json")))
    recs = []
    for r in tr["gongban"]:
        school = SCHOOL_NORM.get(r["school"], r["school"])
        # 两校区合并行（22/23 号：天外/清华附中 各两个校区，官方同一条计划）→ school_ids 列出两校区
        if "、" in school:
            parts = [p.strip() for p in school.split("、")]
            ids = [match_school_ids(p, "440106")[0] for p in parts if p]
            ids = [x for x in ids if x]
            sid, sids = (None, sorted(ids)) if len(ids) >= 2 else (ids[0] if ids else None, None)
        else:
            sid, sids = match_school_ids(school, "440106")
        _zone = r.get("zone")
        _ss = _scope_primary_ids(_zone, "440106") if _zone else None
        recs.append({
            "school": school, "school_id": sid,
            **({"school_ids": sids} if sids else {}),
            "plan_classes": r["plan_classes"], "scope": _zone,
            **({"scope_school_ids": _ss} if _ss else {}),
            "mechanism": "single_zone", "mechanism_note": "公办初中划片招生（2026 细则附件6）",
            "group_members": None,
        })
    for r in tr["qiye"]:
        _sid, _sids = match_school_ids(r["school"], "440106")
        recs.append({
            "school": SCHOOL_NORM.get(r["school"], r["school"]), "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": r["plan_classes"], "scope": None,
            "mechanism": "single_zone", "mechanism_note": "企事业办学校招生（附件7）",
            "group_members": None,
        })
    for r in tr["minban"]:
        _school_norm = SCHOOL_NORM.get(r["school"], r["school"])
        _sid, _sids = match_school_ids(r["school"], "440106")
        # 天河东风/培智（民办附件8）与白云区公办同名校跨区候选混合（SchoolMatcher 索引化后
        # 同名跨区进入候选 → 多候选宁缺展开 school_ids 误并两校）。显式锚定天河实体。
        _TMB_ANCHOR = {"广州市天河区东风学校": "gz-440106-24ff78f9",
                       "广州市天河区培智学校": "gz-440106-0a2c7178"}
        if _school_norm in _TMB_ANCHOR:
            _sid, _sids = _TMB_ANCHOR[_school_norm], None
        recs.append({
            "school": _school_norm, "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": r["plan_classes"], "scope": None,
            "mechanism": "single_zone", "mechanism_note": "民办学校初中部自主招生（附件8）",
            "group_members": None,
        })
    return {
        "year": 2026, "district": "天河区",
        "source": "2026 义务教育阶段学校招生工作细则附件6/7/8（穗天教〔2026〕2号）",
        "source_url": "http://www.thnet.gov.cn/attachment/8/8016/8016210/10791180.pdf",
        "records": recs,
    }

def build_huangpu_official():
    """黄埔：附件5 电脑派位 7 组 + 对口直升 22 组。无班数列。"""
    tr = json.load(open(os.path.join(RAW, "huangpu_2026_juniors.json")))
    recs = []
    for gid, r in tr["paiwei_groups"].items():
        note = f"黄埔区 2026 年小升初电脑随机派位第{gid}组"
        for j in r["juniors"]:
            _sid, _sids = match_school_ids(j, "440112")
            recs.append({
                "school": SCHOOL_NORM.get(j, j), "school_id": _sid,
                **({"school_ids": _sids} if _sids else {}),
                "plan_classes": None, "scope": None,
                "mechanism": "group_paidui", "mechanism_note": note,
                "group_members": r["juniors"], "_group_primaries": r["primaries"],
            })
    for r in tr["zhisheng_groups"]:
        _sid, _sids = match_school_ids(r["junior"], "440112")
        _zh_scope = "、".join(r["primaries"])
        _ss = _scope_primary_ids(_zh_scope, "440112") if _zh_scope else None
        recs.append({
            "school": SCHOOL_NORM.get(r["junior"], r["junior"]), "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": None, "scope": _zh_scope,
            **({"scope_school_ids": _ss} if _ss else {}),
            "mechanism": "single_zone", "mechanism_note": "对口直升（2026 实施细则附件5）",
            "group_members": None,
        })
    return {
        "year": 2026, "district": "黄埔区",
        "source": "2026 义务教育学校招生工作实施细则附件5（穗埔教〔2026〕265号）",
        "source_url": "http://www.hp.gov.cn/attachment/8/8016/8016631/10791836.pdf",
        "records": recs,
    }

BUILDERS = {
    "panyu": build_panyu,
    "baiyun": build_baiyun,
    "liwan": build_liwan,
    "yuexiu": build_yuexiu_official,
    "haizhu": build_haizhu_official,
    "tianhe": build_tianhe_official,
    "huangpu": build_huangpu_official,
}

if __name__ == "__main__":
    _entities = json.load(open(os.path.join(ROOT, "data/registry/entity/dist/entities.json")))

    # 法人行挂 school_ids（与 quota_matrix 口径一致）：政府招生文件按法人单位公布
    # （一条「广州市第十六中学」覆盖多个校区，无独立校区行），校区实体须经法人行
    # school_ids 命中「有招生」；否则校区实体会被孤儿判定误报「无招生」。
    #
    # 【关键口径 2026-09-17】校区「办不办初中」是业务事实，不能从法人名/校区名推导：
    # 部分校区不是完中，初中部只设在某些校区（如十六中初中在东湖/本部，水荫校区是
    # 纯高中——middle 实体已由 build_entities NON_MIDDLE_CAMPUS 删除）；官方文件按
    # 校区招生的（白云/番禺/荔湾 raw）与人工核对的才确认。故只挂 CONFIRMED_CAMPUS
    # 白名单（来源：官方招生 raw / 用户核实），未确认校区宁缺（孤儿保留待逐校确认），
    # 不盲目挂全部同 core 校区。
    _CONFIRMED_CAMPUS = {
        'gz-440104-8964385d',  # 广州市第十六中学(东湖校区)：初中初一初二（用户+官方）
        'gz-440104-8a1a7b3d',  # 广州市第十六中学（本部）：初中初三回本部
        'gz-440112-badbc2ab',  # 广州知识城中学(东校区)：官方「东校区招收初中一年级新生」
        'gz-440112-ec15555e',  # 广州知识城中学(南校区)：官方「初中部设在东校区和南校区」
        'gz-440111-c8461d5d',  # 广州市第六十五中学初中部(明德校区)：白云官方 raw
        'gz-440111-c7b90869',  # 广州市第六十五中学(同德校区)：白云官方 raw
        'gz-440113-43d027a5',  # 广铁一中铁英学校(东校区)：番禺官方（东/西合计 28 班）
        'gz-440113-94c76638',  # 广铁一中铁英学校(西校区)：番禺官方（东/西合计 28 班）
        # —— 2026-09-17 联网核实（outputs/campus_middle_webverify_20260917.md），官方来源确认办初中 ——
        'gz-440103-41cb6344',  # 西关培英(西校区)=官方「广州市西关培英中学」完全中学
        'gz-440103-4cda3f9e',  # 四中(康园校区)=官方「四中(初中康园校区)」010324（民办聚贤初中部）+抖音百科2021
        'gz-440103-8e11a7d3',  # 南海中学(初中部)=官方「广州市南海中学」西华路460号初中部
        'gz-440111-e74c2e1d',  # 白云中学法人行=完全中学，初中承载于汇侨+棠景
        'gz-440111-f751344d',  # 广外实验(北校区) 沙亭东路 2023 启用含初一 10 班
        'gz-440111-150715c8',  # 空港实验(建南校区) 78 班完全中学 2026-09 启用，现开初中 19 班
        'gz-440111-4c9a3eaa',  # 龙归学校(初中部) 九年一贯制，裸名龙归学校初中 plan10
        'gz-440104-099a5868',  # 十七中(西校区)=原82中 2021 起为初中校区（2026-08 起临迁培正矿泉）
        'gz-440104-191aaa35',  # 育才(东校区) 水均南街21号=育才初中部（高中在福今路2号）
        'gz-440104-1e9bdce3',  # 执信(水荫路校区) 2017 专为初中部改建
        'gz-440104-9b88f912',  # 十三中(禺山校区) 禺山路14号=初中部（文德路83号为高中）
        'gz-440106-621b20d3',  # 75中(天平架校区) 广州大道北498号=初中部（官方表）
        'gz-440106-a989804b',  # 广州中学(名雅校区) 官方：名雅/五山/天润为初中部
        'gz-440106-b049d65a',  # 113中(东方校区) 官方新花城2020：东方=初中部
        'gz-440106-dd16c13e',  # 天河中学(花城校区) 猎德大道27号=初中部（官方表）
        'gz-440106-e32237e4',  # 清华附中湾区学校 2026 派位：智谷8班+智慧城8班均招初一
        'gz-440106-22fcbcd6',  # 执信(天河校区) 2026 派位总计划 10 班 420 人
        'gz-440105-2f31776e',  # 新滘中学(土华校区) 华洲路698号 2026 官方初中表并列
        'gz-440105-dd2723fc',  # 南武(岭南画派纪念校区) 玫瑰二街12号 2026 承担初一初三
        'gz-440105-ed868139',  # 97中(江南新苑校区) 晓港东横街12号 2026 承担初一初二
    }
    # 法人推导与 backfill_school_ids.py 相同：同 stage 下去括号+去「广州市」后同
    # core 名的全部校区实体；只挂白名单内确认办初中的校区（脚本生成不手改）。
    def attach_legal_school_ids(data):
        by_core = {}
        for _e in _entities["entities"]:
            if _e.get("stage") != "middle":
                continue
            _core = re.sub(r"^广州市", "", re.sub(r"[（(][^）)]*[）)]", "", _e["name"]).strip())
            by_core.setdefault(_core, set()).add(_e["school_id"])
        # 只收 middle 版实体（完中同 id 有 middle+high 双实体，dict 覆盖会误取 high 版导致
        # 该行 attach 被 stage 检查跳过、白名单校区失去共享招生）——setdefault 保 first middle。
        _by_id = {}
        for _e in _entities["entities"]:
            if _e.get("stage") == "middle":
                _by_id.setdefault(_e["school_id"], _e)
        for _r in data["records"]:
            if not _r.get("school_id") or _r.get("school_ids"):
                continue
            _e = _by_id.get(_r["school_id"])
            if not _e or _e.get("stage") != "middle":
                continue
            _core = re.sub(r"^广州市", "", re.sub(r"[（(][^）)]*[）)]", "", _e["name"]).strip())
            _sids = sorted((by_core.get(_core, set()) & _CONFIRMED_CAMPUS))
            # 写 school_ids 条件：白名单校区不同于记录本身才写——即「记录 school_id 是 A，
            # 同 core 另有白名单校区 B 时挂 [B]」让 B 共享 A 的招生（2026-09-17 改为单校区也挂，
            # 原 len>1 限制使「官方记录主实体 + 单个白名单校区」场景挂不上，孤儿无法消除）
            if _sids and set(_sids) != {_r["school_id"]}:
                _r["school_ids"] = _sids
        return data

    # 支持 --out-dir DIR：产物一致性重跑（check_groups_drift）输出到临时目录，不改工作区
    _args = list(sys.argv[1:])
    out_dir = None
    if "--out-dir" in _args:
        i = _args.index("--out-dir")
        out_dir = _args[i + 1]
        del _args[i:i + 2]
    targets = _args or list(BUILDERS.keys())
    # 中间统一格式目录：默认 parsed/middle_enrollment_2026/；--out-dir 时输出到临时目录（快照测试）
    dist_dir = out_dir if out_dir is not None else OUT_PARSED
    districts = {}
    # 合理无招生说明（src/leftover_notes.json，业务人工确认、可展示给家长，机制同小学）：
    #   对 2026 官方无招生计划的学校注入「2026 无招生计划」展示记录（mechanism=no_plan，
    #   理由在 mechanism_note，详情页直接展示）；已有招生记录（如三元里中学涉拆迁停招 0 班）
    #   跳过注入——停招理由已在其 mechanism_note，前端统一展示。
    # 副作用即豁免：注入后 school_id 进入招生 id 集合 → 孤儿判定「无招生」消失；
    # 「无升学」由 data_quality_test _MID_LEFT_NOTE_SIDS 豁免（业务确认合理，非数据缺口）。
    _LEFT_NOTES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "../src/leftover_notes.json"), encoding="utf-8"))
    _ADCODE_DK = {v: k for k, v in _DK_ADCODE.items()}
    for dk in targets:
        data = BUILDERS[dk]()
        data = attach_legal_school_ids(data)
        for _sid, _note in _LEFT_NOTES.items():
            if _ADCODE_DK.get(_sid.split("-")[1]) != dk:
                continue
            if any(_r.get("school_id") == _sid or _sid in (_r.get("school_ids") or [])
                   for _r in data["records"]):
                continue
            _ent = next((_e for _e in _entities["entities"]
                         if _e.get("school_id") == _sid and _e.get("stage") == "middle"), None)
            if _ent is None:
                continue
            data["records"].append({
                "school": _ent["name"], "school_id": _sid, "plan_classes": None,
                "scope": None, "mechanism": "no_plan", "mechanism_note": _note,
                "group_members": None,
            })
            print(f"         注入合理无招生说明: {_ent['name']} ({_sid})")
        # 各区中间产物（统一格式，审计层）
        out = os.path.join(dist_dir, f"middle_enrollment_2026_{dk}.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        districts[dk] = data
        # 统计
        total = len(data["records"])
        matched = sum(1 for r in data["records"] if r["school_id"])
        mech_count = {}
        for r in data["records"]:
            mech_count[r["mechanism"]] = mech_count.get(r["mechanism"],0)+1
        print(f"{dk:8s} -> {out}")
        print(f"         总{total}所, POI匹配{matched}, 机制分布: {mech_count}")
    # group_members 去重为独立组表（包体优化：组内 N 校 × 每组重复 M 次的校名只存一次）：
    # record.group_id 引用；mechanisms 三档全 7 区一致，合并后顶层一份。
    # dist 层精简（2026-09-24）：record 不再存 school 名称（前端按 school_id 联查实体名）；
    # groups 只保留 name + primaryIds（map key 即小学名列表），members/memberIds 无前端消费已删。
    # parsed 区级产物保留 school/group_members 内嵌（审计层溯源，快照行键=school 不变）。
    groups = {}
    seen = {}  # 组内容（成员集合）→ group_id
    for dk in targets:
        for r in districts[dk]["records"]:
            members = r.pop("group_members", None)
            primaries = r.pop("_group_primaries", None)
            r.pop("school", None)  # dist 层不存名称（parsed 审计层保留）
            if members:
                # 去重 key 含对口小学：官方 1/2、8/9、13/14 组中学列表相同但小学列不同
                # （荔湾），仅按 members 去重会合并丢小学 → (members, primaries) 联合去重。
                key = (tuple(sorted(members)), tuple(sorted(primaries or [])))
                gid = seen.get(key)
                if gid is None:
                    gid = f"{dk}-{len(seen) + 1}"
                    seen[key] = gid
                    entry = {"district": districts[dk]["district"], "name": _group_name(r.get("mechanism_note"))}
                    # 生源小学名 → school_id 列表（构建期实体匹配；多校区多个 id，前端弹窗选校区）
                    entry["primaryIds"] = {p: _primary_ids(p, _DK_ADCODE[dk]) for p in (primaries or [])}
                    groups[gid] = entry
                r["group_id"] = gid
    # 最终合并一份（dist 前端消费；--out-dir 时与区产物同目录）
    # mechanisms 三档全 7 区一致 → 顶层一份；group_members → 独立 groups 表 + record.group_id
    merged = {"year": 2026,
              "note": "7 区公办初中招生计划合并（前端运行时消费；区级独立产物见 parsed/middle_enrollment_2026/）",
              "mechanisms": MECHANISMS,
              "groups": groups,
              "districts": districts}
    merge_out = os.path.join(out_dir if out_dir is not None else OUT, "middle_enrollment_2026.json")
    with open(merge_out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    print(f"合并    -> {merge_out}（{len(districts)} 区）")
