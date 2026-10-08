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
  single_zone     单校划片（按地段/对口小学直接安排，无落选概念）
  zhi_sheng       对口直升（小学对口直升初中，不参加电脑派位）
  group_paidui    多校电脑派位（组内学校兜底，不安排到组外）
  single_paidui   电脑派位（自愿报名+超额电脑派位，未派中回原学区）
  min_zi_zhu      自主招生（民办/企事业办学校初中部）
  no_plan         2026 无招生计划
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
        # 2026-09-30：RESOLVE_OVERRIDE 聚合名锚定（官方一行多校区，如「第六十五中学
        # （明德校区、同德校区）」）显式展开全部锚定校区（school_id=None + school_ids=全部），
        # 不落 resolve 单值（单值只会命中首个别名校区）；未命中锚定保持单校区精准。
        _ov = _MATCHER._override_hits(name)
        if _ov and len(_ov) > 1:
            return None, sorted(r["school_id"] for r in _ov)
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

_SCOPE_SPLIT = re.compile(r"[、，,;；\n]")
# 小学名形态后缀：只对"看起来是小学名"的段做实体匹配，避免划片地段/楼盘/招生条件文本
# 拆段后的零碎词（如「金山谷」「车陂路以东」「…小学应届毕业生」）被 SchoolMatcher 宽松命中造成误跳转。
# 带限定词的段（「XX小学（地段生）」「…（不含北校区）」）宁缺毋滥：不匹配则前端保留文本展示。
_EDU_SUFFIX = ("小学", "学校", "中学", "学院", "幼儿园", "小学部", "初中部", "高中部",
               "校区", "分校", "教学点", "分部", "附中", "附小", "职中", "本部",
               "一小", "二小", "三小", "四小", "五小", "六小", "七小", "八小", "九小", "十小")
# 截断贪心顺序：复合后缀优先（小学部/初中部/高中部/附小/附中），再单字后缀
_EDU_TRUNC = ("小学部", "初中部", "高中部", "附小", "附中", "职中", "幼儿园",
              "小学", "学校", "中学", "学院", "校区", "分校", "教学点", "分部",
              "一小", "二小", "三小", "四小", "五小", "六小", "七小", "八小", "九小", "十小")
# 括号内招生条件词：命中即视该括号为「条件注解」（剥离），而非校区/分组限定（保留）。
# 不含「不含/除外」——（不含北校区）剥掉会误配北校区，宁缺毋滥。
_COND_KEYWORDS = ("地段生", "地段学生", "户籍生", "摇号", "人户一致", "毕业生", "普通生",
                  "安置区", "福和雅苑", "汉塘村", "民强村", "新兴村", "明星村",
                  "统筹生", "政策性照顾", "适龄儿童", "塘贝户籍", "符合条件",
                  "部分", "全部", "应届", "借读", "优待", "港澳", "人才", "积分", "租户")
# 招生条件文本阻断词：清洗（剥括号/截断）后候选仍含这些词 = 划片/户籍/计划描述文本而非学校名单，
# 宁缺（番禺官方无小学名单，纯地段文本不得 fuzzy 吸附成假小学）。
# 白云/天河候选为纯学校名，实测 140 个候选零命中。
_CAND_BLOCK = ("户籍", "招生", "面向", "应届", "毕业", "学位", "计划", "资格", "条件",
               "居住", "政策", "照顾", "适龄", "报名", "录取", "的", "在职", "人员", "子女")
# 范围限定词（修复2，2026-09-30）：官方原文段含这些词 = 明确限定招收范围（地段/村/安置区），
# 清洗后候选若无校区限定（法人多校区展开）则宁缺不猜，防止把范围外校区误挂到该初中。
_SCOPE_RANGE_WORDS = ("不含", "不包含", "除外", "村", "雅苑", "安置区", "旧村", "地块",
                      "住宅小区", "项目范围", "改造项目")


def _clean_one(seg):
    """单个候选清洗：剥条件括号 → 无括号残留则贪心截断尾部条件描述。返回清洗后候选或空。"""
    seg = seg.strip()
    if not seg:
        return ""
    # 招生条件描述段直接宁缺（「…在职在编人员适龄子女」「…小学应届毕业生」属计划文本，非学校名单；
    # 截断会产出「暨南大学新造校区」这类假小学，须在截断前拦截）
    if any(k in seg for k in ("在职在编", "适龄子女", "小学应届毕业生", "户籍的小学", "应届毕业生招生")):
        return ""
    # 剥条件括号（校区括号不含条件词则保留，整体按原逻辑匹配）
    def _drop_cond(m):
        return "" if any(k in m.group(1) for k in _COND_KEYWORDS) else m.group(0)
    cleaned = re.sub(r"[（(]([^（）()]*)[）)]", _drop_cond, seg).strip()
    if not cleaned:
        return ""
    if cleaned != seg:
        seg = cleaned
    # 无括号残留才截断尾部条件描述（「六中实验小学福和雅苑安置区地段生」→「六中实验小学」）；
    # 含校区括号的段（「空港实验小学（总校区、北校区）」）整体匹配，不截断防拆坏
    if "（" not in seg and "(" not in seg:
        best = None
        for suf in _EDU_TRUNC:
            idx = seg.rfind(suf)
            if idx != -1:
                best = idx + len(suf) if best is None else max(best, idx + len(suf))
        if best:
            seg = seg[:best]
    return seg


def _clean_scope_part(part, adcode=None):
    """scope 段 → 候选小学名列表（白云 feed 形态清洗，其他区不受影响）：
    1) 段首整组括号形态（「（太和镇第一小学、…、石湖小学）部分毕业生」）→ 展开括号内学校；
    2) 含「:」前缀标签（「南校区：竹料一小、竹料二小、竹料四小」「明德校区：明德小学（本部）」）
       → 取冒号后内容并按顿号拆多子段；
    其余单段直接清洗。返回 [] 表示本段无候选。"""
    part = part.strip()
    if not part:
        return []
    # 1) 段首整组括号（先于长度检查——括号内为多校列表，展开后单校名均短）
    if part.startswith("（") or part.startswith("("):
        m = re.match(r"^[（(]([^（）()]+)[）)]", part)
        if m and any(k in part for k in ("毕业生", "部分", "地段", "户籍")):
            inner = m.group(1).replace("\u0001", "、").replace("\u0002", ",").replace("\u0003", "，")
            return [s.strip() for s in _SCOPE_SPLIT.split(inner) if s.strip()]
    if len(part) > 28 and "（" not in part and "(" not in part:
        return []  # 超长划片文本拦截；含括号段（学校名+长范围括号）剥括号后为短名，交给 _clean_one 后由主循环兜底
    # 2) 冒号校区标签前缀：取冒号后内容，拆成多子段逐段清洗
    if "：" in part or ":" in part:
        rest = re.split(r"[：:]", part)[-1].strip()
        segs = [s.strip() for s in _SCOPE_SPLIT.split(rest) if s.strip()]
    else:
        segs = [part]
    out = []
    for seg in segs:
        c = _clean_one(seg)
        if not c:
            continue
        # 修复2（2026-09-30）：范围限定宁缺——官方原文段含招收范围限定词（不含/村/雅苑/
        # 安置区/旧村/地块/住宅小区/改造项目等），清洗后候选又无校区限定（法人多校区展开
        # 无法确定官方所指校区）→ 宁缺不猜。如 seq44「六中实验小学（民强村、新兴村）」
        # 只收民强/新兴村的六中实小（本部），不得展开南校区误挂民航人和；seq43
        # 「六中实验小学福和雅苑安置区地段生」同理。范围词必须出现在被剥掉的内容里
        # （条件括号/尾部描述，c != seg）——「汤村小学」「旺村分校」等校名自带「村」字
        # 不触发；RESOLVE_OVERRIDE 锚定段（如「三元里小学（不含北校区）」）清洗后保留
        # 括号（c == seg）天然豁免，锚定已显式给出校区。
        if adcode and c != seg and any(w in seg for w in _SCOPE_RANGE_WORDS):
            ids = _primary_ids(c, adcode)
            if len(ids) > 1 and not _MATCHER._override_hits(c):
                continue
        out.append(c)
    return out


def _scope_primary_ids(scope, adcode):
    """直升小学 scope → {小学名: school_ids}（数据层匹配，前端聚合为可点击行）：
    按顿号/逗号拆段，逐段清洗（条件括号剥离/尾部条件词截断）后 SchoolMatcher 匹配小学实体
    （preferred_stage='小学'）。仅匹配「小学名形态」（教育词后缀）的段——划片地段/说明文本
    （天河/番禺/白云部分）匹配不到则整体不输出，前端对该记录保留『招生服务范围』文本展示。
    宁缺毋滥：匹配不到不猜。"""
    if not scope:
        return {}
    # 拆段前保护括号内顿号/逗号（校区列表「（总校区、北校区）」、整组小学「（太和…石湖小学）」不被拆散），
    # _clean_scope_part 内按需还原
    _prot = re.sub(r"[（(]([^（）()]*)[）)]",
                   lambda m: m.group(0).replace("、", "\u0001").replace(",", "\u0002").replace("，", "\u0003"),
                   scope)
    out = {}
    for part in _SCOPE_SPLIT.split(_prot):
        for cand in _clean_scope_part(part, adcode):
            cand = cand.replace("\u0001", "、").replace("\u0002", ",").replace("\u0003", "，")
            if len(cand) > 28:
                continue
            t = cand.rstrip("。；;，,、 ）】]}\u3000 ").rstrip("）")
            # 「XX（不含/除外 XX）」排除限定形态：官方原文带排除括号，剥「）」后不以教育
            # 后缀结尾会被误判为划片文本。此类整体放行，交由 RESOLVE_OVERRIDE 官方原文锚定
            # （如「三元里小学（不含北校区）」→ 校本部+南校区，2026-09-30 修复）。
            # 「（暂定名）」同理（2026-09-30）：官方暂定名学校（如黄埔
            # 「知识城南安置区（二期）小学（暂定名）」）剥「）」后以「（暂定名」结尾，
            # 不以教育后缀收尾 → 误判丢弃。整体放行交由实体表匹配（实体无则宁缺）。
            if not t.endswith(_EDU_SUFFIX) and not any(x in cand for x in ("（不含", "（不包含", "（除外", "（暂定名")):
                continue
            if any(w in cand for w in _CAND_BLOCK):
                continue
            ids = _primary_ids(cand, adcode)
            if ids:
                out.setdefault(cand, ids)
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

# ---------- 数据层平铺（B 层构建期完成，运行时不再做文本匹配）----------
def _panyu_explains(stage):
    """番禺官方表尾「说明：」1-6（转录原文，小学/初中两版），返回 {编号: 内容}。"""
    d = json.load(open(os.path.join(RAW_PANYU, "panyu_2026_official.json"), encoding="utf-8"))
    sheet_name = "公办小学招生地段、计划" if stage == "primary" else "公办初中招生范围、计划"
    rows = d["sheets"][sheet_name]
    start = next(i for i, r in enumerate(rows) if r and str(r[0]).strip().startswith("说明"))
    explains = {}
    for r in rows[start + 1:]:
        m = re.match(r"^(\d+)\.", str(r[0] or "").strip())
        if not m:
            break
        explains[int(m.group(1))] = _strip_list_numbers(str(r[0]).strip())
    return explains


def _tianhe_attachment():
    """天河细则附件10/11 平铺数据（放 primary 转录目录——小学 B 层附件11 同源使用）"""
    return json.load(open(os.path.join(RAW_PANYU, "tianhe_attachment.json"), encoding="utf-8"))


def _strip_attachment_refs(text):
    """平铺语义清理：去掉「（…附件N…）」来源注与「附件N #N」表内序号引用，只留具体规则。"""
    if not text:
        return text
    return re.sub(r"（[^（）]*附件\d+[^（）]*）", "", re.sub(r"附件\d+\s*#\d+\s*", "", text))


def _strip_list_numbers(text):
    """去招生说明里的数字序号（「2.凡小区内配建…」「； 3.市桥富豪…」「）2.持有…」）→ 只留内容。
    前缀标点（；/。/：/）/（/，/、）保留作分隔，序号限两位内且后随中文/数字/引号才删，
    防误删正文数字（「3公里」「近6年」等无点号）。"""
    if not text:
        return text
    return re.sub(r"(^|[；;，,、。）(（:：])\s*(\d{1,2})\.(?=[\u4e00-\u9fff0-9“”\"A-Za-z（(])",
                  r"\1", text)


def _strip_concat_joiner(text):
    """多条说明平铺后残留的拼接顿号：句号/分号/逗号等后紧跟的顿号
    （「招生方案。、房地产开发商…」→「招生方案。房地产开发商…」）。
    只清标点后的顿号，正文「（一、二期）」「1、2、3、4幢」等前面是汉字不受影响。"""
    if not text:
        return text
    return re.sub(r"([。；;，,！？!?])\s*、", r"\1", text)


def _expand_middle_texts(data, dk):
    """B 层构建期平铺（产物即最终形态，双端一致）：
    番禺 mechanism_note「(见)说明N」→ 说明原文；天河附件10 记录 scope 展开 + 机制归位 single_paidui；
    全区 mechanism_note/scope 去「附件N」来源注。"""
    if dk == "panyu":
        explains = _panyu_explains("middle")
        for r in data["records"]:
            mn = r.get("mechanism_note") or ""
            if "说明" in mn:
                r["mechanism_note"] = re.sub(r"见?说明(\d+)",
                                             lambda m: explains.get(int(m.group(1)), m.group(0)), mn)
    if dk == "tianhe":
        att = _tianhe_attachment()
        for r in data["records"]:
            scope = r.get("scope") or ""
            if "详见附件10" in scope:
                school_ids = [x for x in [r.get("school_id"), *(r.get("school_ids") or [])] if x]
                parts = [att["a10_by_school"][sid] for sid in school_ids if sid in att["a10_by_school"]]
                if parts:
                    r["scope"] = scope.replace("详见附件10", "".join(parts))
                    # 此类学校走「自主报名+电脑派位」，机制本身即电脑派位 → 直接归位 single_paidui（不再 label 覆盖）
                    r["mechanism"] = "single_paidui"
                    r["mechanism_note"] = None
    for r in data["records"]:
        mn = r.get("mechanism_note")
        if mn:
            r["mechanism_note"] = _strip_concat_joiner(_strip_list_numbers(_strip_attachment_refs(mn)))
        scope = r.get("scope")
        if scope:
            r["scope"] = _strip_attachment_refs(scope)
    return data


def apply_inferred_feeds(data):
    """特殊学校对口小学推断回填（2026-09-30）：官方 zone/scope 未直接列出小学名单的学校，
    由 src/inferred_feed_schools.json 显式手工标注（零名字匹配，按 school_id 键控）。
    仅在 scope_school_ids 为空时回填（官方解析结果优先，不覆盖明文）；
    键即生源小学名（生源小学行=键→单 id 直链），scope 原文仍由 scope 字段独立展示。
    依据独立于 xiaoshengchu（该层将废弃，禁止循环依赖），来源说明见 src 表内 note。"""
    tbl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "../src/inferred_feed_schools.json")
    try:
        with open(tbl_path, encoding="utf-8") as f:
            tbl = json.load(f)
    except FileNotFoundError:
        return data
    schools = tbl.get("schools", {})
    for r in data["records"]:
        sid = r.get("school_id")
        if not sid or sid not in schools:
            continue
        if r.get("scope_school_ids"):
            continue  # 官方明文解析已有，推断不覆盖
        feed = schools[sid].get("scope_school_ids") or {}
        feed = {k: v for k, v in feed.items() if v}
        if not feed:
            continue
        r["scope_school_ids"] = feed
        print(f"         特殊对口小学推断回填: {sid} -> {list(feed)}（src/inferred_feed_schools.json）")
    return data


# 区键 → adcode（SchoolMatcher 匹配用：按本区过滤，不跨区错配）
_DK_ADCODE = {"yuexiu": "440104", "haizhu": "440105", "tianhe": "440106",
              "huangpu": "440112", "panyu": "440113", "baiyun": "440111", "liwan": "440103"}

# 区级枚举定义：UI 直接用 label / lose_text
# 机制是招生方式本身（对口直升/电脑派位/划片…），从官方文本解析时直接归位；不再用 label 覆盖
MECHANISMS = {
    "single_zone":    {"label": "单校划片",     "can_lose": False, "lose_text": None},
    "zhi_sheng":      {"label": "对口直升",     "can_lose": False, "lose_text": None},
    "group_paidui":   {"label": "多校电脑派位", "can_lose": False, "lose_text": "派位组内学校随机分配，组内兜底，不安排到组外。"},
    "single_paidui":  {"label": "电脑派位",     "can_lose": True,  "lose_text": "符合报名条件 ≠ 一定录取。报名人数超计划时由区教育局统一组织电脑派位；未派中者回户籍地学区申请入读公办初中，不保证安排到本校。"},
    "min_zi_zhu":     {"label": "自主招生",     "can_lose": False, "lose_text": None},
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
            mech = "single_paidui"
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
    # 自愿报名、超计划电脑派位；中签自动取消属地正常安排的学位、未派中回户籍地学区 → single_paidui。
    # 与计划表（属地划片/派位）互补，同校并存为两种机制（如仲元一校区 市桥划片 + 面向全区电脑派位）。
    quju = json.load(open(os.path.join(RAW, "panyu_2026_quju.json")))
    for q in quju["records"]:
        qsid, qsids = match_school_ids(q["school"], "440113")
        qnote = (f"区属初中{q['batch']}批次：招生 {q['plan_people']} 人（自愿报名，超计划电脑派位；"
                 f"中签自动取消属地正常安排的学位，未派中回户籍地学区）。{q['note']}")
        recs.append({
            "school": q["school"], "school_id": qsid,
            **({"school_ids": qsids} if qsids else {}),
            "plan_classes": None, "scope": None,
            "mechanism": "single_paidui", "mechanism_note": qnote,
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
    # 附件1 计划表有、派位组无的学校：市属/单列（协和学校初中部等）。
    # 协和初中部官方正文「原则上对口招收小学部毕业生（本校直升）」→ 机制 zhi_sheng，note 留「单列」计划特点；
    # 其余单列校无直升依据 → single_zone。
    group_schools = {r["school"].strip() for r in recs}
    for r in plan["records"]:
        nm = r["school"].strip()
        if nm in group_schools:
            continue
        _sid, _sids = match_school_ids(nm, "440103")
        if nm == "广州市协和学校初中部" or nm == "广州协和学校初中部":
            _mech, _note = "zhi_sheng", ("2026 荔湾区公办初中一年级招生计划单列，不在电脑派位分组表内。"
                                         "广州协和学校初中部原则上对口招收广州协和学校小学部毕业生（本校直升）。")
        else:
            _mech, _note = "single_zone", "2026 荔湾区公办初中一年级招生计划单列，不在电脑派位分组表内。"
        recs.append({
            "school": nm, "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": r["plan"], "scope": None,
            "mechanism": _mech,
            "mechanism_note": _note,
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
            # 机制判定：先排除"不参加电脑派位"，再判对口直升/划片/派位。
            # 机制是招生方式本身，从组名直接归位（对口直升 → zhi_sheng，不再并进 single_zone）
            if "不参加" in group or "不参与" in group:
                continue
            elif "对口直升" in group or "九年制" in group or "内部直升" in group:
                mech = "zhi_sheng"
            elif "单校" in group:
                mech = "single_zone"
            elif "电脑派位" in group or "多校" in group:
                mech = "group_paidui"
            else:
                mech = "group_paidui"
            # 同一初中在多个小学记录里出现，取最严格机制（single_paidui > group_paidui > single_zone ≈ zhi_sheng）
            order = {"single_zone":1, "zhi_sheng":1, "group_paidui":2, "single_paidui":3}
            cur = rec_map[j]["mechanism"]
            if cur is None or order.get(mech,0) > order.get(cur,0):
                rec_map[j]["mechanism"] = mech
                # 对口直升/单校划片：组名即机制名（「对口直升（细则第九条）」等），标签已展示机制 → note 清空
                rec_map[j]["mechanism_note"] = None if mech in ("zhi_sheng", "single_zone") else group
            # 组内成员：同一 group 名下的所有初中
            if mech == "group_paidui":
                group_members_map.setdefault(group, set()).add(j)
    # 回填 group_members；mechanism 为 None 的（"不参加电脑派位"记录里的初中）默认对口直升（不参加派位=直接安排）
    for j, rec in rec_map.items():
        if rec["mechanism"] is None:
            rec["mechanism"] = "zhi_sheng"
            rec["mechanism_note"] = None
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
    # 直升（细则第九条）：已派位的初中追加 zhi_sheng 直升规则（一校多规则，官方真实并存）
    for pri, junior in tr["direct_feed"].items():
        _sid, _sids = match_school_ids(junior, "440104")
        _ss = _scope_primary_ids(pri, "440104") if pri else None
        recs.append({
            "school": SCHOOL_NORM.get(junior, junior), "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": None, "scope": pri,
            **({"scope_school_ids": _ss} if _ss else {}),
            # 细则第九条对口直升：机制 zhi_sheng，note 不再重复机制名
            "mechanism": "zhi_sheng", "mechanism_note": None,
            "group_members": None,
        })
    # 育才实验学校（2026 越秀公办初中招生计划第 21 号 6 班 + 招生问答第一类直升）：
    # 面向全区公办小学招收部分直升生（自愿报名，录取后自动放弃公办初中电脑派位资格，
    # 未录取回原组派位）→ single_paidui（电脑派位），非固定对口小学、不在派位组内。
    _sid_yc, _sids_yc = match_school_ids("广州市越秀区育才实验学校", "440104")
    recs.append({
        "school": "广州市越秀区育才实验学校", "school_id": _sid_yc,
        **({"school_ids": _sids_yc} if _sids_yc else {}),
        "plan_classes": 6,
        "scope": "面向全区公办小学招收部分直升生（自愿报名；录取后不再具有公办初中电脑派位资格）",
        "mechanism": "single_paidui",
        "mechanism_note": "2026 越秀公办初中招生计划第 21 号（6 班）；招生问答第一类：面向全区公办小学招收部分直升生，报名人数超计划电脑派位",
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
            # 正文对口直升：机制 zhi_sheng，note 不再重复机制名
            "mechanism": "zhi_sheng", "mechanism_note": None,
            "group_members": None,
        })
    return {
        "year": 2026, "district": "海珠区",
        "source": "2026 初中招生问答附件1 派位组 + 正文直升 + 公办初中招生计划表",
        "source_url": "https://www.haizhu.gov.cn/gzhzjy/gkmlpt/content/10/10799/mpost_10799155.html",
        "records": recs,
    }

# 附件10 电脑派位可报名小学名单（官方小学名，2026-10-08 天河接入反推时按
# tianhe_attachment.json a10_by_school 原文逐字定稿；同一学校仅收「可报名」小学，不含校方自身）：
#   华附初中部 a565a93c：面向学校周边 3km 天河公办/企事业办小学穗籍毕业生（28 所）
#   华颖初中部 dab5b807：面向学校周边 5km（38 所）
#   省实天河初中部 0eb93435：面向学校周边 3km（21 所）
#   执信天河校区 22fcbcd6：7 班面向珠吉街范围「人户一致」（5 所，官方点名）
# 用作 single_paidui 记录的 _group_primaries / scope_school_ids，供小升初反推链产出
# 「可报名派位」feed 条目（与海珠派位组进 feed 同口径）；清湾两校区/天外两校区为
# 全区自主报名（无点名小学），不在此表。历史小学侧 TH_PAIWEI 的 3 处混入错误
# （华附池误含「华南师范大学附属中学（初中部）」、省实池误含自身、华颖池误含自身）
# 不继承，以本表为准。
TH_A10_POOLS = {
    "gz-440106-a565a93c": [  # 华附初中部 3km（官方 28 所；转录原文「体育西小学」按实体全称「体育西路小学」收录）
        "华景小学", "天府路小学", "南国学校（小学部）", "体育东路小学", "体育东路小学海明学校",
        "体育东路小学兴国学校", "石牌小学", "汇景实验学校（小学部）", "华康小学", "龙口西小学",
        "员村小学", "昌乐小学", "五山小学", "体育西路小学", "华阳小学", "天河区第一实验小学",
        "华融小学", "五一小学", "华颖外国语学校（小学部）", "天河中学猎德实验学校（小学部）",
        "一一三中学陶育实验学校（小学部）", "冼村小学", "华南农业大学附属小学",
        "华南师范大学附属小学", "长征小学", "天河第一小学",
        "华南理工大学附属实验学校（小学部）", "暨南大学附属实验学校（小学部）",
    ],
    "gz-440106-dab5b807": [  # 华颖初中部 5km（官方 38 所）
        "汇景实验学校（小学部）", "南国学校（小学部）", "天河中学猎德实验学校（小学部）",
        "一一三中学陶育实验学校（小学部）", "棠东小学", "体育东路小学",
        "体育东路小学海明学校", "体育东路小学兴国学校", "体育西路小学", "石牌小学",
        "华阳小学", "五山小学", "员村小学", "昌乐小学", "棠下小学", "石东小学", "华康小学",
        "华景小学", "龙口西小学", "东圃小学", "车陂小学", "棠德南小学", "天河区第一实验小学",
        "泰安小学", "骏景小学", "冼村小学", "新元小学", "华融小学", "中海康城小学",
        "旭景小学", "天府路小学", "五一小学", "天河第一小学", "华南师范大学附属小学",
        "华南农业大学附属小学", "长征小学", "华南理工大学附属实验学校（小学部）",
        "暨南大学附属实验学校（小学部）",
    ],
    "gz-440106-0eb93435": [  # 省实天河初中部 3km（官方 21 所）
        "岑村小学", "棠东小学", "沐陂小学", "五山小学", "员村小学", "昌乐小学", "棠下小学",
        "华景小学", "车陂小学", "棠德南小学", "泰安小学", "骏景小学", "华融小学",
        "中海康城小学", "天府路小学", "御景小学", "华南师范大学附属小学",
        "华南农业大学附属小学", "华颖外国语学校（小学部）", "汇景实验学校（小学部）",
        "华南理工大学附属实验学校（小学部）",
    ],
    "gz-440106-22fcbcd6": [  # 执信天河校区 7 班（珠吉街「人户一致」，官方点名 5 所）
        "灵秀小学", "奥体东小学", "吉山小学", "珠村小学", "体育东教育集团均和小学",
    ],
}

def _a10_scope_primaries(sid, adcode="440106"):
    """附件10 池小学名 → {小学名: [school_id]}（反推链 primary_ids 的 scope_school_ids 形态）。"""
    names = TH_A10_POOLS.get(sid)
    if not names:
        return None
    return {n: _primary_ids(n, adcode) for n in names}

def build_tianhe_official():
    """天河：附件6 公办 24（划片范围+班数）+ 附件7 企事业 3 + 附件8 民办初中部 24。
    附件10 电脑派位：天外/清华/执信 zone 直接引用 → _expand_middle_texts 展开；华颖/省实
    note 声明「部分招生计划采用电脑派位方式招生，详见附件10」→ 一校多规则，本处追加 single_paidui 记录；
    华附（附件7 企事业办）备注「其中面向天河区电脑派位招收4班168人」→ scope 补附件10 段、机制 single_paidui。"""
    tr = json.load(open(os.path.join(RAW, "tianhe_2026_juniors.json")))
    att = _tianhe_attachment()
    a10 = att["a10_by_school"]
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
        # 2026-10-08（天河接入反推）：zone「详见附件10」的行（天外两校区/清湾两校区/执信）
        # 直接归位 single_paidui（DIST 路径 _expand_middle_texts 同向覆盖，此处前置使反推链
        # 拿到正确机制）；执信附件10 池有点名小学 → _group_primaries 挂池（清湾/天外全区无名单）。
        _a10_zone = bool(_zone) and "详见附件10" in _zone
        _pool = TH_A10_POOLS.get(sid) if _a10_zone else None
        # 2026-10-08（天河详情页生源小学修复）：附件6 对口小学列（primaries）此前仅挂
        # _group_primaries（反推链内存消费），dist 序列化丢弃 → 详情页「生源小学」段
        # （scope_school_ids，前端 Object.keys 遍历）天河 single_zone 初中全空。
        # 现在同步写入 scope_school_ids（同 _a10_scope_primaries 的 {小学名: [school_id]} 形态）。
        _pri_ss = ({n: _primary_ids(n, "440106") for n in (r["primaries"] or [])}
                   if r.get("primaries") else None)
        _ss_final = _a10_scope_primaries(sid) if _pool else (_pri_ss or _ss)
        recs.append({
            "school": school, "school_id": sid,
            **({"school_ids": sids} if sids else {}),
            "plan_classes": r["plan_classes"], "scope": _zone,
            **({"scope_school_ids": _ss_final} if _ss_final else {}),
            # 附件6 公办划片：机制 single_zone（zone 引用附件10 的行归位 single_paidui）；
            # note 不再重复机制名；华颖/省实「部分招生计划…详见附件10」由下方追加的 single_paidui 记录承载，划片记录 note 清空
            "mechanism": "single_paidui" if _a10_zone else "single_zone",
            "mechanism_note": None if "详见附件10" in (r.get("note") or "") else (r.get("note") or None),
            "group_members": None,
            "_group_primaries": r["primaries"] or None,  # 附件6 对口小学列 → 反推链生源
            **({"_group_primaries": _pool} if _pool else {}),
        })
        # 华颖/省实：官方 note「部分招生计划采用电脑派位方式招生，详见附件10」→ 划片之外的附加电脑派位批次，
        # 一校多规则追加 single_paidui 记录（scope=附件10 段原文；_group_primaries=附件10 点名池 → 反推链生源）
        if sid in a10 and "详见附件10" in (r.get("note") or ""):
            _a10_ss = _a10_scope_primaries(sid)
            recs.append({
                "school": school, "school_id": sid,
                **({"school_ids": sids} if sids else {}),
                "plan_classes": None, "scope": a10[sid],
                **({"scope_school_ids": _a10_ss} if _a10_ss else {}),
                "mechanism": "single_paidui", "mechanism_note": None,
                "group_members": None,
                "_group_primaries": TH_A10_POOLS.get(sid),
            })
    for r in tr["qiye"]:
        _sid, _sids = match_school_ids(r["school"], "440106")
        _scope = a10.get(_sid) if _sid else None
        _ss = _a10_scope_primaries(_sid) if _sid in TH_A10_POOLS else (_scope_primary_ids(_scope, "440106") if _scope else None)
        recs.append({
            "school": SCHOOL_NORM.get(r["school"], r["school"]), "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": r["plan_classes"], "scope": _scope,
            **({"scope_school_ids": _ss} if _ss else {}),
            **({"_group_primaries": TH_A10_POOLS[_sid]} if _sid in TH_A10_POOLS else {}),
            # 附件7 企事业办：华附备注「其中，面向天河区电脑派位招收4个班168人」→ 机制 single_paidui + scope=附件10 段；
            # 其余企事业办（华工附/暨大附）无电脑派位依据 → min_zi_zhu（自主招生）
            "mechanism": "single_paidui" if _sid in a10 else "min_zi_zhu",
            "mechanism_note": None,
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
            # 附件8 民办学校初中部：自主招生 → min_zi_zhu，note 不再重复机制名
            "mechanism": "min_zi_zhu", "mechanism_note": None,
            "group_members": None,
        })
    # 2026-10-08（天河接入反推）：附件6 之外的一贯制学校小学部内部直升——
    # 智谷第一实验/省实/燕园/天外智谷/华工附/暨大附/清湾两校区/奥中智谷校区小学部
    # 官方未在附件6 单列小学部对口（智谷第一实验 seq17 仅列天英小学；省实/燕园/天外智谷
    # 仅列地段；清湾/奥中智谷为校区小学部），按九年/十二年制内部直升惯例补 zhi_sheng 记录，
    # 供小升初反推链产出 direct_feed（与越秀/海珠/黄埔直升口径统一）；
    # 附件6 在册的汇景/华颖/南国/猎德/陶育小学部对口已由对口小学列覆盖（single_zone），不重复。
    _TH_NINE_YEAR = (
        # (初中显示名, 小学部生源名)；school_id 由 match_school_ids 解析（九年制同实体双学段 → 自feed）
        ("广州市天河区智谷第一实验学校", "天河区智谷第一实验学校"),
        ("广东实验中学天河学校", "广东实验中学天河学校"),
        ("广州中学天河燕园学校", "广州中学天河燕园学校"),
        ("广州市天河外国语智谷学校", "广州市天河外国语智谷学校"),
        ("华南理工大学附属实验学校", "华南理工大学附属实验学校(小学部)"),
        ("暨南大学附属实验学校（初中部）", "暨南大学附属实验学校"),
        ("广州奥林匹克中学（含智谷校区）", "广州奥林匹克中学（智谷校区）小学部"),
        ("清华附中湾区学校", "清华附中湾区学校"),
        ("清华附中湾区学校（智慧城校区）", "清华附中湾区学校（智慧城校区）"),
    )
    for _school, _pri in _TH_NINE_YEAR:
        _sid, _sids = match_school_ids(_school, "440106")
        if not _sid and not _sids:
            continue
        _ny_ss = {_pri: _primary_ids(_pri, "440106")}
        recs.append({
            "school": _school, "school_id": _sid,
            **({"school_ids": _sids} if _sids else {}),
            "plan_classes": None, "scope": None,
            # 一贯制小学部内部直升：机制 zhi_sheng（不参加电脑派位）
            "mechanism": "zhi_sheng", "mechanism_note": None,
            "group_members": None, "_group_primaries": [_pri],
            # 2026-10-08（天河详情页生源小学修复）：小学部生源同步写 scope_school_ids，
            # 使九年制初中详情页「生源小学」段可展示直升小学部。
            **({"scope_school_ids": _ny_ss} if _ny_ss.get(_pri) else {}),
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
            # 附件5 对口直升：机制 zhi_sheng，note 不再重复机制名
            "mechanism": "zhi_sheng", "mechanism_note": None,
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
    # 【adcode 维度 2026-09-30】by_core 分组键含 adcode：招生行为按区独立，跨区校区不得
    # 共享招生记录（如执信中学：越秀执信路/水荫路校区走越秀电脑派位、天河校区在天河
    # 附件10 单独派位，若按裸 core 合并会把越秀派位组挂到天河校区详情页，出现「天河校区
    # 招生计划里的越秀小学」错配）。同区校区（如十六中东湖+本部）不受影响。
    def attach_legal_school_ids(data):
        by_core = {}
        for _e in _entities["entities"]:
            if _e.get("stage") != "middle":
                continue
            _core = re.sub(r"^广州市", "", re.sub(r"[（(][^）)]*[）)]", "", _e["name"]).strip())
            _ad = _e["school_id"].split("-")[1] if _e["school_id"].count("-") >= 2 else ""
            by_core.setdefault((_core, _ad), set()).add(_e["school_id"])
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
            _ad = _r["school_id"].split("-")[1] if _r["school_id"].count("-") >= 2 else ""
            _sids = sorted((by_core.get((_core, _ad), set()) & _CONFIRMED_CAMPUS))
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
        # 数据层平铺统一后处理（含 LEFT_NOTES 注入记录）：番禺说明/天河附件10/荔湾协和/附件N 清理
        data = _expand_middle_texts(data, dk)
        # 特殊学校对口小学推断回填（src/inferred_feed_schools.json，仅官方 scope_school_ids 为空时）
        data = apply_inferred_feeds(data)
        # 各区中间产物（统一格式，审计层）
        out = os.path.join(dist_dir, f"middle_enrollment_2026_{dk}.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        # 产物确定性排序（2026-09-29）：records 按 school_id 稳定排序 + sort_keys 统一键序
        data["records"].sort(key=lambda r: r.get("school_id") or "")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
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
    # 顶层 dict 键排序（groups/districts/mechanisms 统一键序，配合区级 records 排序）
    merged = {"year": merged["year"], "note": merged["note"],
              "mechanisms": {k: merged["mechanisms"][k] for k in sorted(merged["mechanisms"])},
              "groups": {k: merged["groups"][k] for k in sorted(merged["groups"])},
              "districts": {k: merged["districts"][k] for k in sorted(merged["districts"])}}
    with open(merge_out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"合并    -> {merge_out}（{len(districts)} 区）")
