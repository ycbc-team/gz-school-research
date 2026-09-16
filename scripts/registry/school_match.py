#!/usr/bin/env python3
"""
统一校名匹配库（Python 侧唯一实现，2026-09 收敛）。

背景：项目各脚本各自实现 norm/匹配逻辑（34 处定义、7 条链路），语义不一导致反复漂移
（「广州中学」→「中学」泛词毁名等）。本模块收敛为：

  一、norm 三档（对应不同匹配强度，规则与 shared 侧保持一致）：
    - normName   严格全等：全角括号→半角→去「广州市」前缀→删括号→去空白
                  （与 scripts/registry/build_entities.mjs 及 packages/shared/src/support.ts 的 normName 一致）
    - looseNorm  normName + 去尾部(初中部|高中部|小学部|校区|分校|学校|部)
                  （与 packages/shared/src/support.ts looseNorm、scripts/linkage/backfill_school_ids.py loose 一致）
    - matchNorm  泛词保护：状态/泛化括号剥、保留校区括号、区名归一、前导区名剥（纯泛词保护）、
                  「广州」剥（纯泛词保护）—— 集团成员→POI 匹配专用（原 scripts/match_poi.py norm）

  二、SchoolMatcher 统一匹配服务：
    输入任意校名 → 输出 school_id/POI，内置收敛顺序与 match_poi 一致：
      exact(normName name+aliases) → alias(去括号 key) → 主校前缀 → 远郊拦截 → substring 双支
    收敛：同区唯一 → 同区同阶段唯一 → 主 POI → 全局唯一（显式跨区放行）→ 缺失（宁可缺失不跨区错配）。
    参数：stage（学段匹配）/ adcode（行政区匹配）/ allow_cross_district / strategy。

用法：
    from school_match import SchoolMatcher, normName, looseNorm, matchNorm
    m = SchoolMatcher()
    m.add_poi(name, adcode, stage, school_id)
    m.add_entities([{"name":..., "stage":..., "aliases":[...]}, ...])
    r = m.resolve("广州市白云区星悦实验学校(初中部)", stage="初中", adcode="440111")
"""
import json, os, re, sys, unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEVEN_DISTRICTS = {"440103":"荔湾","440104":"越秀","440105":"海珠","440106":"天河","440111":"白云","440112":"黄埔","440113":"番禺"}
FAR_DISTRICTS = {"440114":"花都","440115":"南沙","440117":"从化","440118":"增城"}
FAR_KEYWORDS = ["花都","南沙","增城","从化","英德","清远","佛山","东莞","韶关","梅州","河源","惠州","汕头","湛江","肇庆","江门","阳江","茂名","揭阳","潮州","汕尾","云浮","珠海","中山"]

# 括号内是"校区/学部/地址类"限定词时保留（影响校区区分）；状态词与泛化词不参与匹配
_PAREN_KEEP = ("校区", "校区)", "部", "园", "本部", "分教点", "教学点", "南", "北", "东", "西", "中")
_PAREN_DROP = ("建设中", "在建", "筹建", "规划", "拟建", "待建", "新开办", "暂定", "筹办", "装修", "工地", "选址", "暂停营业")

# 泛词后缀：substring 匹配前先剥离，避免「广州实验中学」规约成「实验中学」后吸附任何含「实验中学」的成员
_GENERIC_SUFFIX = ("实验中学", "附属实验学校", "外国语实验学校", "实验学校", "外国语学校", "附属中学", "中学", "附属小学", "小学", "学校", "初中部", "小学部", "高中部")

# 学部/校区后缀（looseNorm 剥除，官方名单原文无学部后缀与 POI 名普遍带"（初中部）"对齐）
_LOOSE_SUFFIX = ("初中部", "高中部", "小学部", "校区", "分校", "学校", "部")

# 繁简/异体字补充（供采集脚本作输入清洗，不进入 normName——
# normName 须与 TS support.ts 完全一致：纯字符串替换，NFKC 会转全角标点改变匹配 key）
VARIANTS = {"穂": "穗", "敎": "教", "學": "学", "朮": "术", "甦": "苏"}


def fold_unicode(s):
    """NFKC 归一 + 繁简/异体字补充（采集侧输入清洗用，非共享 norm）。"""
    s = unicodedata.normalize("NFKC", str(s))
    for a, b in VARIANTS.items():
        s = s.replace(a, b)
    return s


def normName(s):
    """严格全等归一：全角括号→半角 → 去「广州市」前缀 → 删括号 → 去空白。
    与 scripts/registry/build_entities.mjs 及 packages/shared/src/support.ts 的 normName 完全一致。"""
    if not s:
        return ""
    return (str(s).replace("（", "(").replace("）", ")")
            .replace("广州市", "")
            .replace("[", "").replace("]", "")
            .replace("(", "").replace(")", "")
            .replace(" ", "").replace("\u3000", ""))


def looseNorm(s):
    """normName + 去尾部学部/校区后缀。用于官方名单原文（无学部后缀）与 POI 名（带「(初中部)」）跨源全等匹配。"""
    t = normName(s)
    for w in _LOOSE_SUFFIX:
        if t.endswith(w) and len(t) > len(w):
            return t[: -len(w)]
    return t


def brandNorm(s):
    """品牌/集团名容错归一：NFKC+繁简 → 去「广州市」+「广州」+ 删括号 + 去空白。
    仅用于品牌名/集团名互相包含判断（原 merge_groups.norm），不用于校名→POI 匹配
    （校名匹配用 matchNorm，含泛词保护，不会把「广州中学」毁成「中学」）。"""
    if not s:
        return ""
    return (str(s).replace("（", "(").replace("）", ")")
            .replace("广州市", "").replace("广州", "")
            .replace("[", "").replace("]", "")
            .replace("(", "").replace(")", "")
            .replace(" ", "").replace("\u3000", ""))


def strip_generic(s):
    """剥离学校名末尾的泛词后缀，返回核心词（如「白云广大附中实验中学」→「白云广大附中」；纯泛词→空）。"""
    t = s
    changed = True
    while changed:
        changed = False
        for w in _GENERIC_SUFFIX:
            if t.endswith(w) and len(t) > len(w):
                t = t[: -len(w)]
                changed = True
                break
    return t


def coreCampusName(name):
    """法人核心名：去括号校区后缀（「广州市第一一三中学(乐学校区)」→「广州市第一一三中学」；
    无括号则返回自身）。官方升学文件/教育集团按法人单位公布，同一法人的全部校区实体
    由「coreCampusName(实体名) 全等」聚合（backfill 法人 school_ids、merge_groups 品牌归属共用）。"""
    return re.sub(r"[（(][^）)]*[）)]", "", name or "").strip()


def _is_generic_core(s: str) -> bool:
    """剩余核心剥掉序数/修饰词后是否落入泛词表（区名/「广州」剥离会毁名 → 不应剥离）。
    「实验小学」→剥「实验」→「小学」∈泛词 → 保护（避免海珠/黄埔/番禺区实验小学归一成「实验小学」）；
    「星悦实验学校」→不以「实验」开头 →「星悦实验学校」∉泛词 → 可剥离区名；
    「第七中学」→剥「第七」→「中学」∈泛词 → 保护（避免「X区第七中学」与越秀七中撞车）。"""
    core = re.sub(r"^第?[一二三四五六七八九十0-9]+", "", s)
    core = re.sub(r"^(实验|附属|外国语|外语)", "", core)
    return core in _GENERIC_SUFFIX


def matchNorm(name):
    """泛词保护归一（集团成员→POI 匹配专用，原 match_poi.norm）：
    状态括号剥、保留校区括号；去「广州市」前缀；区名归一；前导区名剥离（剩余纯泛词保留）；
    「广州」仅在剩余非纯泛词时剥离（「广州中学」→「中学」是泛词毁名）。"""
    if not name:
        return ""
    s = str(name).strip()
    s = s.replace("（", "(").replace("）", ")").replace("【", "[").replace("】", "]")
    # 只剥离状态/泛化括号（如"建设中"），保留校区类括号（如"(东风广场校区)"）
    s = re.sub(r"[\(\[][^()\[\]]*[\)\]]", lambda m: "" if any(k in m.group(0) for k in _PAREN_DROP) else m.group(0), s)
    # 只去"广州市"行政区划前缀
    s = s.replace("广州市", "")
    # 区名归一：仅剥离"XX区"中的区字（限已知区名），使「白云区广大附中实验中学」与「广州市白云广大附中实验中学」对齐
    s = re.sub(r"(越秀|海珠|天河|荔湾|白云|黄埔|番禺|南沙|增城|从化|花都|萝岗)区", r"\1", s)
    # 前导区名剥离：成员名常带区名前缀而 POI 名不带；剩余过短或为纯泛词（含修饰型泛词）时保留（泛词毁名保护）
    for _d in ("白云", "越秀", "海珠", "天河", "荔湾", "黄埔", "番禺", "萝岗"):
        if s.startswith(_d) and len(s) - len(_d) >= 4 and not _is_generic_core(s[len(_d):]):
            s = s[len(_d):]
            break
    # 前导"广州"是校名成分（「广州中学」剥成「中学」是泛词毁名），仅在剩余非纯泛词时剥离
    # （「广州大学附属中学」→「大学附属中学」对齐；「广州实验小学」→「实验小学」同样受保护；须在区名剥离后）
    if s.startswith("广州") and len(s) - 2 >= 4 and not _is_generic_core(s[2:]):
        s = s[2:]
    s = re.sub(r"\s+", "", s)
    return s


class SchoolMatcher:
    """统一校名匹配服务：索引 = 实体表（normName 全等 + matchNorm 变体 + alias 去括号 key）+ POI 表（带 stage/adcode）。

    收敛顺序（与 match_poi.match_school 一致）：
      同区唯一 → 同区同阶段唯一 → 主 POI 唯一 → 全局唯一（显式跨区放行）→ 缺失。
    宁可缺失、不跨区错配：多候选且无法收敛到唯一时返回 None（调用方以显式 school_id 锚定补救）。
    """

    def __init__(self):
        self.poi_all = []            # [{"name","norm","adcode","stage","school_id"}]
        self.alias_map = {}          # matchNorm alias -> [entity]
        self.exact_map = {}          # normName(name/alias) -> [entity]（严格全等）
        self.loose_map = {}          # looseNorm(name/alias) -> [entity]

    # ---------- 索引构建 ----------
    def add_poi(self, name, adcode="", stage="", school_id=""):
        self.poi_all.append({"name": name, "norm": matchNorm(name), "adcode": adcode,
                             "stage": stage, "school_id": school_id})

    def add_entities(self, entities):
        """entities: [{name, stage, aliases?}]。一个别名可能对应多个实体（共享别名如「广铁一中铁英学校」），
        保留全部实体，由 resolve 结合 preferred_adcode 收敛，避免"后写覆盖"式错配。"""
        for e in entities:
            rec = {"name": e["name"], "stage": e.get("stage", ""), "aliases": []}
            for k in [e["name"]] + list(e.get("aliases", []) or []):
                # 严格全等索引（normName，与 build_entities 一致：全删括号）
                self.exact_map.setdefault(normName(k), []).append(rec)
                self.loose_map.setdefault(looseNorm(k), []).append(rec)
                # 变体索引（matchNorm，保留校区括号）
                key = matchNorm(k)
                self.alias_map.setdefault(key, []).append(rec)
                # matchNorm 保留校区括号（如「(本部)」）而 build_entities 全删：补一个去括号 key 对齐
                k2 = key.replace("(", "").replace(")", "")
                if k2 != key:
                    self.alias_map.setdefault(k2, []).append(rec)

    # ---------- 匹配 ----------
    def resolve(self, name, preferred_adcode=None, preferred_stage=None):
        """任意校名 → 匹配结果 dict（poi_match/matched_name/stage/district/school_id）或 None（无法收敛/缺失）。
        preferred_adcode：行政区匹配（构建某区招生计划时传入该区 adcode，命中候选优先取同区 POI）；
        preferred_stage：学段匹配（初中计划优先初中部，避免选到高中部）。"""
        n = matchNorm(name)

        def bare(s):
            return re.sub(r"[\(（][^()（）]*[\)）]", "", s)

        def _mk(p, poi_match):
            district = SEVEN_DISTRICTS.get(p["adcode"], FAR_DISTRICTS.get(p["adcode"], "未知"))
            return {"poi_match": poi_match, "matched_name": p["name"], "stage": p["stage"],
                    "district": district, "school_id": p["school_id"]}

        def _pick(cands, poi_match, district_guard=True):
            """收敛：先按 school_id 去重（同址多学部 POI 在初中/高中库各一份，视为同一候选），
            再按 同阶段唯一 → 主 POI（无括号）唯一 → 同区唯一 → 全局唯一（允许跨区招生记录）→ 缺失。
            宁可缺失、不跨区错配：多候选且无法收敛到唯一时返回 None，由调用方以显式 school_id 锚定补救。
            district_guard=False 用于 alias 精确命中：实体身份映射是人工确认的显式关系，
            跨区也成立（如白云培英集团核心校「广州市培英中学」本部在荔湾鹤洞校区）；模糊防错配只约束 substring 吸附。"""
            if not cands:
                return None
            seen = {}
            for c in cands:
                if c["school_id"] not in seen:
                    seen[c["school_id"]] = c
                elif preferred_stage and c["stage"] == preferred_stage and seen[c["school_id"]]["stage"] != preferred_stage:
                    # 同 id 多学部 POI（九年制/完中在小学/初中/高中库各一份）：保留与目标学段一致的副本
                    seen[c["school_id"]] = c
            cands = list(seen.values())

            def by_stage(cs):
                if preferred_stage:
                    st = [c for c in cs if c["stage"] == preferred_stage]
                    if len(st) == 1:
                        return st[0]
                return None

            def by_main(cs):
                mains = [c for c in cs if "(" not in c["name"] and "（" not in c["name"]]
                if len(mains) == 1:
                    return mains[0]
                return None

            if preferred_adcode and district_guard:
                same = [c for c in cands if c["adcode"] == preferred_adcode]
                if len(same) == 1:
                    return _mk(same[0], poi_match)
                if same:
                    r = by_stage(same)
                    if r:
                        return _mk(r, poi_match)
                    r = by_main(same)
                    if r:
                        return _mk(r, poi_match)
                    return None  # 同区多候选无法收敛：宁可缺失，不跨区错配
                # 同区无候选：仅当成员名含"其他区"区名（如白云名单里的培英鹤洞校区→荔湾）才回退全局唯一
                own_name = name.replace("广州市", "")
                self_dist = SEVEN_DISTRICTS.get(preferred_adcode, "")
                has_other = any(k in own_name for k in ("越秀", "海珠", "天河", "荔湾", "白云", "黄埔", "番禺", "萝岗") if k != self_dist)
                if has_other:
                    r = by_stage(cands)
                    if r:
                        return _mk(r, poi_match)
                    r = by_main(cands)
                    if r:
                        return _mk(r, poi_match)
                    if len(cands) == 1:
                        return _mk(cands[0], poi_match)
                return None
            r = by_stage(cands)
            if r:
                return _mk(r, poi_match)
            r = by_main(cands)
            if r:
                return _mk(r, poi_match)
            if len(cands) == 1:
                return _mk(cands[0], poi_match)
            return None

        # 0. 远郊成员拦截：在 substring 吸附之前（exact/alias 命中之后），防「新塘镇第三中学」→「广州市第三中学」
        # 1. exact norm match in POI
        r = _pick([p for p in self.poi_all if p["norm"] == n], "精确命中")
        if r:
            return r
        # 2. alias match（一个别名可能对应多个实体：跨实体收集 POI 候选，同区优先收敛）
        if n not in self.alias_map:
            _n_flat = n.replace("(", "").replace(")", "")
            if _n_flat != n and _n_flat in self.alias_map:
                n = _n_flat
        if n in self.alias_map:
            ents = self.alias_map[n]
            # 2a. 先精确匹配实体完整名（含校区括号，避免多校区 norm 歧义）；身份映射显式确认，跨区不拦截
            ent_names = {e["name"] for e in ents}
            r = _pick([p for p in self.poi_all if p["name"] in ent_names], "变体命中", district_guard=False)
            if r:
                return r
            # 2b. 再按 norm 匹配
            ent_norms = {matchNorm(e["name"]) for e in ents}
            r = _pick([p for p in self.poi_all if p["norm"] in ent_norms], "变体命中", district_guard=False)
            if r:
                return r
            # 2b5. 实体主校 POI 缺失时，用实体核心名前缀在同区找分校区 POI（如「华阳小学」→「华阳小学(华成校区)」）
            for e in ents:
                base = bare(matchNorm(e["name"]))
                if len(base) < 4:
                    continue
                cands = [p for p in self.poi_all if p["norm"].startswith(base) and (not preferred_adcode or p["adcode"] == preferred_adcode)]
                for _kw in ("初中部", "小学部", "高中部"):
                    if _kw in matchNorm(e["name"]) and len(cands) > 1:
                        suff = [c for c in cands if _kw in c["norm"]]
                        if suff:
                            cands = suff
                            break
                r = _pick(cands, "变体命中")
                if r:
                    return r
            # 2c. 实体存在但 POI 无坐标：未给区上下文时保留原兜底；给了区上下文则继续 substring 找同区 POI
            if not preferred_adcode:
                return {"poi_match": "变体命中", "matched_name": ents[0]["name"], "stage": ents[0]["stage"],
                        "district": "实体表无坐标", "school_id": ""}
        # 2d. far district keyword check（exact/alias 均未命中后才拦截远郊）
        for kw in FAR_KEYWORDS:
            if kw in name:
                return {"poi_match": "远郊不在POI范围", "matched_name": "", "stage": "", "district": kw, "school_id": ""}
        # 3. substring / contains match (variant)：剥离泛词后按核心词匹配，同区优先，防「实验中学」类泛词吸附
        if n:
            n_core = strip_generic(n)
            _WEAK_CORE = ("白云", "越秀", "海珠", "天河", "荔湾", "黄埔", "番禺", "萝岗",
                          "第一", "第二", "第三", "第四", "第五", "第六", "第七", "第八", "第九", "第十")
            _NON_SCHOOL = ("充电站", "停车场", "广场", "大厦", "中心", "公园", "小区", "花园", "银行", "医院", "超市", "餐厅", "酒店", "公司", "商厦")
            a_cands, b_cands = [], []  # A支=成员核心在POI（专属高）；B支=POI核心在成员（按位置收敛）
            for p in self.poi_all:
                if not p["norm"]:
                    continue
                if any(bare(p["name"]).endswith(k) for k in _NON_SCHOOL):
                    continue
                p_bare = bare(p["norm"])
                p_core = strip_generic(p_bare)
                if p_core in _WEAK_CORE:
                    p_core = ""
                if len(n_core) >= 2 and n_core not in _WEAK_CORE and (n_core in p_bare or n_core in p["norm"]):
                    a_cands.append((p, p_core))
                elif len(p_core) >= 2 and p_core in n:
                    b_cands.append((p, p_core))
            suffix = ""
            for w in ("小学", "中学", "初中", "高中", "学校"):
                if n.endswith(w):
                    suffix = w
                    break
            if a_cands:
                if suffix:
                    suff = [c for c in a_cands if bare(c[0]["norm"]).endswith(suffix) or c[0]["norm"].endswith(suffix)]
                    if len(suff) >= 1:
                        a_cands = suff
                cands = a_cands
            else:
                cands = b_cands
                # B 支位置优先：POI 核心词在成员名中出现位置越靠后越专属
                if len(cands) > 1:
                    b_pos = [(p, n.find(pc)) for p, pc in cands if pc and pc in n]
                    if b_pos:
                        maxpos = max(pos for _, pos in b_pos)
                        if maxpos > 0:
                            top = [p for p, pos in b_pos if pos == maxpos]
                            if len(top) == 1:
                                cands = [(p, pc) for p, pc in cands if p in top]
            if suffix and len(cands) > 1:
                suff = [c for c in cands if bare(c[0]["norm"]).endswith(suffix) or c[0]["norm"].endswith(suffix)]
                if suff:
                    cands = suff
            for _kw in ("(初中部)", "初中部", "(小学部)", "小学部", "(高中部)", "高中部", "(中学)", "中学部"):
                if _kw in n and len(cands) > 1:
                    suff = [c for c in cands if _kw in c[0]["norm"]]
                    if suff:
                        cands = suff
                        break
            r = _pick([c[0] for c in cands], "变体命中")
            if r:
                return r
        # 4. default: 7区内真实缺失
        return {"poi_match": "7区内真实缺失", "matched_name": "", "stage": "", "district": "", "school_id": ""}

    # ---------- 便捷工厂 ----------
    @classmethod
    def load(cls, poi_paths=None, entities_path=None):
        """从数据文件构建：poi_paths=[(path, stage)]，entities_path=entities.json 路径。"""
        m = cls()
        if poi_paths:
            for path, stage in poi_paths:
                d = json.load(open(path, encoding="utf-8"))
                for s in d.get("schools", []):
                    m.add_poi(s["name"], s.get("adcode", ""), stage, s.get("school_id", ""))
        if entities_path:
            d = json.load(open(entities_path, encoding="utf-8"))
            m.add_entities(d.get("entities", []))
        return m


if __name__ == "__main__":
    # CLI：python3 school_match.py "<校名>" [--adcode 440111] [--stage 初中]
    name = sys.argv[1]
    adcode = None
    stage = None
    if "--adcode" in sys.argv:
        adcode = sys.argv[sys.argv.index("--adcode") + 1]
    if "--stage" in sys.argv:
        stage = sys.argv[sys.argv.index("--stage") + 1]
    matcher = SchoolMatcher.load(
        poi_paths=[(os.path.join(BASE, "data/primary/schools-gz.json"), "小学"),
                   (os.path.join(BASE, "data/middle/schools-gz.json"), "初中"),
                   (os.path.join(BASE, "data/high/schools-gz.json"), "高中")],
        entities_path=os.path.join(BASE, "data/registry/entities.json"))
    r = matcher.resolve(name, preferred_adcode=adcode, preferred_stage=stage)
    print(json.dumps({"name": name, **r} if r else {"name": name, "result": None}, ensure_ascii=False, indent=2))
