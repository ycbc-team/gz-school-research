#!/usr/bin/env python3
"""
统一校名匹配库（Python 侧唯一实现，2026-09 收敛）。

背景：项目各脚本各自实现 norm/匹配逻辑（34 处定义、7 条链路），语义不一导致反复漂移
（「广州中学」→「中学」泛词毁名等）。本模块收敛为：

  一、norm 三档（对应不同匹配强度，规则与 shared 侧保持一致）：
    - normName   严格全等：全角括号→半角→去「广州市」前缀→删括号→去空白
                  （与 data/registry/entity/scripts/build_entities.py 及 packages/shared/src/support.ts 的 normName 一致）
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
    m = SchoolMatcher.load()  # 只依赖实体表（data/registry/entity/dist/entities.json），无需传 POI 表
    r = m.resolve("广州市白云区星悦实验学校(初中部)", stage="初中", adcode="440111")
"""
import json, os, re, sys, unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

SEVEN_DISTRICTS = {"440103":"荔湾","440104":"越秀","440105":"海珠","440106":"天河","440111":"白云","440112":"黄埔","440113":"番禺"}
FAR_DISTRICTS = {"440114":"花都","440115":"南沙","440117":"从化","440118":"增城"}
DISTRICT_CODE = {v: k for k, v in {**SEVEN_DISTRICTS, **FAR_DISTRICTS}.items()}
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
    与 data/registry/entity/scripts/build_entities.py 及 packages/shared/src/support.ts 的 normName 完全一致。"""
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
    """剥离学校名末尾的泛词后缀，返回核心词（如「白云广大附中实验中学」→「白云广大附中」；纯泛词→空）。
    支持带括号形式「XX(小学部)」：剥「(小学部)」整体（含括号），避免残留括号破坏 substring 吸附；
    剥后若残留括号字符则继续剥（防御）。"""
    t = s
    changed = True
    while changed:
        changed = False
        for w in _GENERIC_SUFFIX:
            if t.endswith(w) and len(t) > len(w):
                t = t[: -len(w)]
                changed = True
                break
            for _open, _close in (("(", ")"), ("（", "）")):
                _wrapped = _open + w + _close
                if t.endswith(_wrapped) and len(t) > len(_wrapped):
                    t = t[: -len(_wrapped)]
                    changed = True
                    break
            if changed:
                break
        if not changed and t.endswith(("(", "（")):
            t = t[:-1]
            changed = True
    return t


def coreCampusName(name):
    """法人核心名：去括号校区后缀（「广州市第一一三中学(乐学校区)」→「广州市第一一三中学」；
    无括号则返回自身）。官方升学文件/教育集团按法人单位公布，同一法人的全部校区实体
    由「coreCampusName(实体名) 全等」聚合（backfill 法人 school_ids、merge_groups 品牌归属共用）。"""
    return re.sub(r"[（(][^）)]*[）)]", "", name or "").strip()


def legalKey(name):
    """法人推导 key：法人核心名再剥括号外学部后缀（「XX初中部/高中部/小学部/中职部」）。
    merge_groups 法人推导与 SchoolMatcher 多校区展开共用，避免两处实现漂移。"""
    return matchNorm(re.sub(r"(小学|初中|高中|中职)部$", "", coreCampusName(name)))


def legalCampuses(name, entities):
    """法人推导：返回同一法人的全部校区实体（[{"poi_name","school_id"}]，按 school_id 去重）。

    第一层：legalKey 全等（实体 name 或 aliases，括号式校区经 coreCampusName 剥括号后在此命中）。
    第二层（无括号后缀式校区统一归并规则）：实体核心名剥括号后以「校区」结尾、
    且以法人 key 开头、校区名部分 >= 2 字 → 归并为同法人校区。
    「东风东路小学锦城花园校区」→「东风东路小学」、「沙面小学岭南校区」→「沙面小学」等，
    凡「<法人><校区名>校区」形态一律自动归并，替代「手工给后缀式校区实体补括号式别名」的做法。
    """
    key = legalKey(name)
    seen = {}
    for e in entities:
        if legalKey(e["name"]) == key:
            seen.setdefault(e["school_id"], e["name"])
        elif any(legalKey(a) == key for a in (e.get("aliases") or [])):
            seen.setdefault(e["school_id"], e["name"])
        else:
            en = matchNorm(coreCampusName(e["name"]))
            if en.endswith("校区") and en.startswith(key) and len(en) >= len(key) + 3:
                seen.setdefault(e["school_id"], e["name"])
    return [{"poi_name": n, "school_id": sid} for sid, n in seen.items()]


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
        if s.startswith(_d) and len(s) - len(_d) >= 4 and not _is_generic_core(re.sub(r"[\(\[].*$", "", s[len(_d):])):
            s = s[len(_d):]
            break
    # 前导"广州"是校名成分（「广州中学」剥成「中学」是泛词毁名），仅在剩余非纯泛词时剥离
    # （「广州大学附属中学」→「大学附属中学」对齐；「广州实验小学」→「实验小学」同样受保护；须在区名剥离后）
    if s.startswith("广州") and len(s) - 2 >= 4 and not _is_generic_core(re.sub(r"[\(\[].*$", "", s[2:])):
        s = s[2:]
    s = re.sub(r"\s+", "", s)
    return s


class SchoolMatcher:
    """统一校名匹配服务：索引只依赖实体表（name/aliases 已全覆盖 POI 名，school_id 承载 adcode）。

    收敛顺序（与 match_poi.match_school 一致）：
      同区唯一 → 同区同阶段唯一 → 主 POI 唯一 → 全局唯一（显式跨区放行）→ 缺失。
    宁可缺失、不跨区错配：多候选且无法收敛到唯一时返回 None（调用方以显式 school_id 锚定补救）。

    两种匹配能力（resolve / resolve_all 语义）：
      - 精准匹配：带校区名（含括号校区限定）只返回命中的校区实体；无/多候选宁缺，不回落其它校区。
      - 泛匹配：官方只写法人名（无校区限定）时返回同一法人的全部校区实体。
    跨区办学特例（政策区 ≠ POI 物理区）由 POLICY_DISTRICT（quota_matrix 数据驱动白名单）内建承接，
    显式锚定（实体合并/跨区同名）由 RESOLVE_OVERRIDE 内建承接——各业务无需再单独适配。
    """

    # 升学归属区白名单：school_id → 政策区（「XX区」）。数据源 data/linkage/quota_matrix.json
    # （官方升学文件法人行，school_ids 全体标法人所属区），加载失败优雅降级为空。
    # 如「广州市第七中学(桂花校区)」POI 白云、政策越秀——官方越秀名单含桂花时须命中。
    POLICY_DISTRICT = None

    # 显式锚定白名单（normName(name) → school_id 列表）：跨区同名无法由通用规则收敛等场景，
    # 全部业务共用（原 xs_resolver RESOLVE_OVERRIDE 迁入）。POI 层已剔除的点位名
    # （如「景泰小学柯子岭校区43号A座」）不得残留为匹配规则。
    RESOLVE_OVERRIDE = {
        '龙溪小学': ['gz-440111-fd1c0f9d'],  # 跨区同名：白云民办「龙溪小学」≠ 荔湾公办「西关实验小学龙溪学校」
    }

    def __init__(self):
        self.all_entities = []       # 实体全量（substring 变体匹配遍历用）
        self.alias_map = {}          # normName/matchNorm(name/alias) -> [entity]
        self.exact_map = {}          # normName(name/alias) -> [entity]（严格全等）
        self.loose_map = {}          # looseNorm(name/alias) -> [entity]
        self.by_id = {}              # school_id -> entity rec（显式锚定/回连用）

    # ---------- 索引构建 ----------
    def add_entities(self, entities):
        """entities: [{name, stage, aliases?}]。一个别名可能对应多个实体（共享别名如「广铁一中铁英学校」），
        保留全部实体，由 resolve 结合 preferred_adcode 收敛，避免"后写覆盖"式错配。"""
        for e in entities:
            rec = {"name": e["name"], "stage": e.get("stage", ""), "aliases": [], "school_id": e.get("school_id", "")}
            if rec["school_id"]:
                self.by_id[rec["school_id"]] = rec
            self.all_entities.append(rec)
            for k in [e["name"]] + list(e.get("aliases", []) or []):
                # 严格全等索引（normName，与 build_entities 一致：全删括号）
                self.exact_map.setdefault(normName(k), []).append(rec)
                self.loose_map.setdefault(looseNorm(k), []).append(rec)
                # 别名索引主键：normName（全删括号+去广州市）——与查询端一致，符合「去括号匹配」；
                # matchNorm 键（保留校区括号+剥区）为兼容旧键保留
                self.alias_map.setdefault(normName(k), []).append(rec)
                key = matchNorm(k)
                self.alias_map.setdefault(key, []).append(rec)
                k2 = key.replace("(", "").replace(")", "")
                if k2 != key:
                    self.alias_map.setdefault(k2, []).append(rec)

    # ---------- 政策区白名单与显式锚定 ----------
    @classmethod
    def _load_policy_district(cls):
        """懒加载 quota_matrix 政策区白名单（school_id → 政策区）；数据缺失降级为空。"""
        cls.POLICY_DISTRICT = {}
        try:
            qm = json.load(open(os.path.join(BASE, 'data/linkage/quota_matrix.json'), encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return
        for s in qm.get('schools', []):
            d = s.get('district')
            if not d:
                continue
            if s.get('school_id'):
                cls.POLICY_DISTRICT[s['school_id']] = d
            for sid in s.get('school_ids') or []:
                cls.POLICY_DISTRICT[sid] = d

    @staticmethod
    def _adcode_of(e):
        """实体 school_id 的物理区 adcode（gz-440105-xxx → 440105）。"""
        sid = e.get('school_id') or ''
        parts = sid.split('-')
        return parts[1] if len(parts) >= 3 else ''

    def _policy_adcode(self, e):
        """实体的政策区 adcode（升学归属区白名单；无则空）。"""
        if self.POLICY_DISTRICT is None:
            self._load_policy_district()
        d = (self.POLICY_DISTRICT or {}).get(e.get('school_id'))
        return DISTRICT_CODE.get((d or '').replace('区', ''), '') if d else ''

    def _result(self, e):
        adcode = e["school_id"].split("-")[1] if e.get("school_id") else ""
        district = SEVEN_DISTRICTS.get(adcode, FAR_DISTRICTS.get(adcode, "实体表无坐标"))
        return {"poi_match": "多校区命中", "matched_name": e["name"], "stage": e["stage"],
                "district": district, "school_id": e["school_id"]}

    def _override_hits(self, name):
        """显式锚定白名单命中 → [result]（全部业务共用，跨区亦成立）；未命中 None。"""
        ov = self.RESOLVE_OVERRIDE.get(normName(name))
        if not ov:
            return None
        out = []
        for sid in ov:
            e = self.by_id.get(sid)
            if e:
                out.append(self._result(e))
        return out or None

    # ---------- 匹配 ----------
    def resolve_all(self, name, preferred_adcode=None, preferred_stage=None):
        """返回官方名对应的全部同法人校区（泛匹配）；带校区限定的名称只返回其精确实体（精准匹配，宁缺毋滥）。
        if not name:
            return []

        无校区限定（政策只写法人名）：按 ``matchNorm(coreCampusName(...))`` 全等展开同一法人的
        全部校区实体（如「小北路小学」→ 四个同法人校区）；带 preferred_adcode 时按
        「POI 物理区 + 政策区白名单」过滤，本区无则宁缺 []。
        带校区限定（含括号校区/学部）：只返回精确命中的校区实体；无唯一命中返回 []——
        不回落 single 策略（substring 可能错配「海珠中路小学」→「先烈中路小学」），也不返回其它校区。
        """
        stage_map = {"小学": "primary", "初中": "middle", "高中": "high"}
        wanted_stage = stage_map.get(preferred_stage, preferred_stage)

        def entities_for(records):
            seen = set()
            out = []
            for e in records:
                if wanted_stage and e["stage"] != wanted_stage:
                    continue
                if e["school_id"] in seen:
                    continue
                seen.add(e["school_id"])
                out.append(e)
            return out

        # 显式锚定白名单（跨区同名/实体合并）：优先于一切规则，跨区亦成立
        ov = self._override_hits(name)
        if ov:
            return ov

        has_campus = bool(re.search(r"[（(].+?[）)]", name or ""))
        candidates = entities_for(list(self.exact_map.get(normName(name), [])) +
                                  list(self.alias_map.get(normName(name), [])) +
                                  list(self.alias_map.get(matchNorm(name), [])))

        # 带校区限定：精准匹配，宁缺毋滥——只返回唯一命中的校区实体
        if has_campus:
            if preferred_adcode:
                f = [e for e in candidates if self._adcode_of(e) == preferred_adcode]
                f += [e for e in candidates if e not in f and self._policy_adcode(e) == preferred_adcode]
                candidates = f
            return [self._result(e) for e in candidates] if len(candidates) == 1 else []

        # 无校区限定：全部同法人校区展开（法人行公布即适用全部校区）
        core = matchNorm(coreCampusName(name))
        if len(core) >= 4:
            all_entities = [e for es in self.exact_map.values() for e in es]
            candidates += [
                e for e in all_entities
                if (not wanted_stage or e["stage"] == wanted_stage)
                and matchNorm(coreCampusName(e["name"])) == core
            ]
            candidates = entities_for(candidates)

        # 区过滤：POI 物理区命中优先；物理区不符但政策区（升学归属）命中保留；均无宁缺 []
        if preferred_adcode:
            f = [e for e in candidates if self._adcode_of(e) == preferred_adcode]
            f += [e for e in candidates if e not in f and self._policy_adcode(e) == preferred_adcode]
            candidates = f
        if candidates:
            return [self._result(e) for e in candidates]
        # 单值回落兜底（2026-09-21 修复 3067133 回归：resolve_all 只走 exact/alias/全等展开，
        # 无区前缀裸名/镇街前缀名（如「市桥东兴小学」→「东兴小学」「毓贤学校」→「番禺区毓贤学校」）
        # 全部失配——旧版候选空时 return [one] 兜底被删，入库产物即该行为）。
        # 仅无校区限定且 exact/alias/全等展开零候选时启用；resolve 单值仍走完整
        # exact/alias/substring 分支（海珠中路小学等无实体名宁缺，不强行吸附）。
        if not has_campus:
            one = self.resolve(name, preferred_adcode, preferred_stage, strategy="single")
            if one and one.get("school_id"):
                return [one]
        return []

    def resolve(self, name, preferred_adcode=None, preferred_stage=None, strategy="single"):        return []

    def resolve(self, name, preferred_adcode=None, preferred_stage=None, strategy="single"):
        """任意校名 → 匹配结果 dict（poi_match/matched_name/stage/district/school_id）或 None（无法收敛/缺失）。
        preferred_adcode：行政区匹配（构建某区招生计划时传入该区 adcode，命中候选优先取同区 POI）；
        preferred_stage：学段匹配（初中计划优先初中部，避免选到高中部）。"""
        if not name:
            return None
        if strategy in {"all", "multi", "campuses"}:
            return self.resolve_all(name, preferred_adcode, preferred_stage)
        if strategy != "single":
            raise ValueError(f"unknown matching strategy: {strategy}")
        # 显式锚定白名单（跨区同名/实体合并）：优先于一切规则
        ov = self._override_hits(name)
        if ov:
            return ov[0]
        # 输入自带区名前缀 → 提取为 preferred_adcode 约束（school_id 的 adcode 承担区定位，
        # 匹配键不依赖区名；调用方未传 adcode 时自动提取，如「白云区XXX」）。
        # 仅提取开头区名；泛词场景（如「海珠区实验小学」）同样提取，由 preferred_adcode
        # 收敛替代「区名参与匹配键」的旧消歧方式。
        if preferred_adcode is None:
            for _d, _code in DISTRICT_CODE.items():
                if name.startswith(_d + '区') or name.startswith(_d):
                    preferred_adcode = _code
                    break
        n = matchNorm(name)
        alias_multiple = False  # alias 命中多候选且无法收敛 → substring 禁用泛词吸附（防核心校裸名吸附集团成员）

        def bare(s):
            return re.sub(r"[\(（][^()（）]*[\)）]", "", s)

        _STAGE_WANT = {"小学": "primary", "初中": "middle", "高中": "high"}  # 中文 → 实体英文
        _STAGE_CN = {"primary": "小学", "middle": "初中", "high": "高中"}  # 实体英文 → 中文输出

        def _mk(p, poi_match):
            district = SEVEN_DISTRICTS.get(p["adcode"], FAR_DISTRICTS.get(p["adcode"], "未知"))
            return {"poi_match": poi_match, "matched_name": p["name"],
                    "stage": _STAGE_CN.get(p["stage"], p["stage"]),
                    "district": district, "school_id": p["school_id"]}

        def _ent(e):
            """实体 → _pick 候选（补 adcode；school_id 前缀承载物理区）。"""
            return {**e, "adcode": self._adcode_of(e)}

        def _pick(cands, poi_match, district_guard=True):
            """收敛：先按 school_id 去重（同址多学部 POI 在初中/高中库各一份，视为同一候选），
            再按 同阶段唯一 → 主 POI（无括号）唯一 → 同区唯一 → 全局唯一（允许跨区招生记录）→ 缺失。
            宁可缺失、不跨区错配：多候选且无法收敛到唯一时返回 None，由调用方以显式 school_id 锚定补救。
            district_guard=False 用于 alias 精确命中：实体身份映射是人工确认的显式关系，
            跨区也成立（如白云培英集团核心校「广州市培英中学」本部在荔湾鹤洞校区）；模糊防错配只约束 substring 吸附。"""
            if not cands:
                return None
            _want = _STAGE_WANT.get(preferred_stage) if preferred_stage else None
            seen = {}
            for c in cands:
                if c["school_id"] not in seen:
                    seen[c["school_id"]] = c
                elif _want and c["stage"] == _want and seen[c["school_id"]]["stage"] != _want:
                    # 同 id 多学段实体（九年制/完中 primary/middle/high 各一条）：保留与目标学段一致的副本
                    seen[c["school_id"]] = c
            cands = list(seen.values())

            def by_stage(cs):
                if _want:
                    st = [c for c in cs if c["stage"] == _want]
                    if len(st) == 1:
                        return st[0]
                return None

            def by_main(cs):
                mains = [c for c in cs if "(" not in c["name"] and "（" not in c["name"]]
                if len(mains) == 1:
                    return mains[0]
                return None

            if preferred_adcode:
                same = [c for c in cands if c["adcode"] == preferred_adcode]
                # 同区唯一优先（无论 district_guard）：「广东实验中学」在越秀上下文应收敛到越秀校区
                # 7c4a905f，而非在越秀/白云两校区间宁缺
                if len(same) == 1:
                    return _mk(same[0], poi_match)
            if preferred_adcode and district_guard:
                same = [c for c in cands if c["adcode"] == preferred_adcode]
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
                # 区名检测要求「XX区」完整形式：路/街名含区名（如「海珠中路小学」的「海珠」是路名）
                # 不构成跨区指认；跨区校区（如白云名单里的培英鹤洞→荔湾）由「鹤洞」类关键词/显式映射承接
                has_other = any((k + "区") in own_name for k in ("越秀", "海珠", "天河", "荔湾", "白云", "黄埔", "番禺", "萝岗") if k != self_dist)
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
        # 1. exact 命中：实体表 name/aliases 的 normName 全等（全删括号+去广州市）。
        #   「万松园小学云桂校区」→ 实体「万松园小学(云桂校区)」；全等要求，不引入 substring 吸附——
        #   「万松园小学」不会匹配「万松园小学(云桂校区)」
        #   「原始名全等」优先：POI 主校点位名 == 实体 name 时，不被校区/分部的共享别名抢占
        #   （「五一小学」→ 主校 3bc362f9，而非红英校区别名「五一小学」）
        _exact_ents = self.alias_map.get(normName(name), [])
        _named = [e for e in _exact_ents if e.get("name") == name]
        r = _pick([_ent(e) for e in (_named or _exact_ents)], "精确命中")
        # stage 约束：preferred_stage 已指定时，exact 命中但学段不符（如「广州市星执学校」
        # 初中/高中 POI 精确命中，但本次是小学记录）→ 不返回，继续 alias 分支找目标学段实体
        # （如星执学校小学部=执信附小 883c58c4），避免跨学段错挂。
        if r and (not preferred_stage or r["stage"] == preferred_stage):
            return r
        # 2. alias match（一个别名可能对应多个实体：跨实体收集 POI 候选，同区优先收敛）
        # 优先 normName 形态（去括号+去广州市，与索引主键一致）；再回退 matchNorm/去括号
        _n_norm = normName(name)
        if _n_norm in self.alias_map:
            n = _n_norm
        if n not in self.alias_map:
            _n_flat = n.replace("(", "").replace(")", "")
            if _n_flat != n and _n_flat in self.alias_map:
                n = _n_flat
        if n not in self.alias_map:
            _n_no_guang = n.replace("广州市", "")
            if _n_no_guang != n and _n_no_guang in self.alias_map:
                n = _n_no_guang
        if n in self.alias_map:
            ents = self.alias_map[n]
            # 2a0. 实体级学段过滤：preferred_stage 已指定且多候选时，优先同 stage 实体
            # （如裸名「广州知识城中学」同时挂在北校区 middle / 南校区 high，初中记录应收敛到 middle；
            #  单候选不受影响）
            if preferred_stage and len(ents) > 1:
                # POI 侧 stage 用中文（初中/高中），实体侧用英文（middle/high）
                _stage_map = {"小学": "primary", "初中": "middle", "高中": "high"}
                _want = _stage_map.get(preferred_stage, preferred_stage)
                _same_stage = [e for e in ents if e["stage"] == _want]
                if _same_stage:
                    ents = _same_stage
            # 2a. 别名命中的实体即候选（实体表唯一真源，name 已含 POI 名）；身份映射显式确认，跨区不拦截
            c2a = [_ent(e) for e in ents]
            r = _pick(c2a, "别名命中", district_guard=False)
            if r:
                return r
            if len(c2a) > 1:
                alias_multiple = True
            # 2b5. 实体主校无同名校区分校区时，用实体核心名前缀在同区找分校区实体（如「华阳小学」→「华阳小学(华成校区)」）。
            # 仅限实体名不带校区括号的主校/本部：带校区括号的实体已指明确切校区（如十三中文德校区 0a17f1eb、
            # 四十一中东校区 b210556b），剥括号前缀反而会吸附同核心名的其它校区
            # （文德→禺山 9b88f912、41中→40a80ebb），应走 2c 按实体 school_id 返回。
            _campus_re = re.compile(r"[\(（][^()（）]*校区[\)）]")
            for e in ents:
                if _campus_re.search(e["name"]):
                    continue
                base = bare(matchNorm(e["name"]))
                if len(base) < 4:
                    continue
                cands = [x for x in self.all_entities
                         if matchNorm(x["name"]).startswith(base)
                         and (not preferred_adcode or self._adcode_of(x) == preferred_adcode)]
                for _kw in ("初中部", "小学部", "高中部"):
                    if _kw in matchNorm(e["name"]) and len(cands) > 1:
                        suff = [c for c in cands if _kw in matchNorm(c["name"])]
                        if suff:
                            cands = suff
                            break
                r = _pick([_ent(c) for c in cands], "别名命中")
                if r:
                    return r
            # 2c. 实体存在但 POI 无坐标：未给区上下文时保留原兜底；给了区上下文且实体唯一（含 2a0
            # 学段过滤后）时直接返回实体 school_id（实体表 id 即榜单/配额主键，如十三中文德校区
            # 0a17f1eb、四十一中东校区 b210556b——substring 反而会吸附无榜单数据的同区校区）；多候选继续找同区 POI
            if not preferred_adcode:
                return {"poi_match": "变体命中", "matched_name": ents[0]["name"], "stage": ents[0]["stage"],
                        "district": "实体表无坐标", "school_id": ""}
            if len(ents) == 1:
                _e = ents[0]
                _dist = SEVEN_DISTRICTS.get(preferred_adcode, FAR_DISTRICTS.get(preferred_adcode, "未知"))
                return {"poi_match": "变体命中(实体无POI点位)", "matched_name": _e["name"], "stage": _e["stage"],
                        "district": _dist, "school_id": _e["school_id"]}
        # 2d. far district keyword check（exact/alias 均未命中后才拦截远郊）
        for kw in FAR_KEYWORDS:
            if kw in name:
                return {"poi_match": "远郊不在POI范围", "matched_name": "", "stage": "", "district": kw, "school_id": ""}
        # 3. substring / contains match (variant)：剥离泛词后按核心词匹配，同区优先，防「实验中学」类泛词吸附
        if n:
            n_core = strip_generic(n)
            # 去括号核心名（「第七中学实验学校(小学部)」→「第七中学实验学校」）：学部括号场景下
            # 泛词剥离会剥过头（「第七」/「八一」丢核心名或错配「八一希望学校」），
            # 故用完整去括号名优先精确包含，strip 泛词仅作弱兜底。
            n_bare = bare(n)
            _WEAK_CORE = ("白云", "越秀", "海珠", "天河", "荔湾", "黄埔", "番禺", "萝岗",
                          "第一", "第二", "第三", "第四", "第五", "第六", "第七", "第八", "第九", "第十")
            _NON_SCHOOL = ("充电站", "停车场", "广场", "大厦", "中心", "公园", "小区", "花园", "银行", "医院", "超市", "餐厅", "酒店", "公司", "商厦")
            a_cands, b_cands = [], []  # A支=成员核心在POI（专属高）；B支=POI核心在成员（按位置收敛）
            bare_cands = []            # 去括号核心精确包含（学部括号等场景），单独优先收敛
            for _x in self.all_entities:
                # 实体表即候选源（name 已含 POI 名，school_id 承载 adcode/stage）；构造兼容候选
                p = {"name": _x["name"], "norm": matchNorm(_x["name"]), "adcode": self._adcode_of(_x),
                     "stage": _x["stage"], "school_id": _x["school_id"]}
                if not p["norm"]:
                    continue
                if any(bare(p["name"]).endswith(k) for k in _NON_SCHOOL):
                    continue
                # 带「校区」括号输入（如「西关培正小学（如意坊校区）」）的 substring 吸附：
                # POI 名必须也带括号（如意坊校区实体缺失时宁缺，不得吸附无括号本部 POI）；
                # 学部括号（小学部/初中部）不受此限（「华侨外国语学校（小学部）」可匹配本部 POI）
                if n != n_bare and "校区" in n and "(" not in p["norm"] and "（" not in p["norm"]:
                    continue
                p_bare = bare(p["norm"])
                p_core = strip_generic(p_bare)
                if p_core in _WEAK_CORE:
                    p_core = ""
                # 「华阳教育集团高塘石小学」「华阳集团侨乐小学」类集团/集团化成员：
                # 核心校裸名（如「华阳小学」）不得吸附集团名下成员（集团名 ≠ 核心校名；
                # 成员应走 alias/显式映射命中）；仅当成员名以核心裸名为前缀（如「广州中学教育集团XX」），
                # 或 POI 以成员裸名为结尾（成员裸名匹配自身集团前缀 POI，如「高塘石小学」→
                # 「华阳教育集团高塘石小学」）才放行
                if "集团" in p_bare and not (p["norm"].startswith(n_bare) or p["norm"].endswith(n_bare)):
                    continue
                if len(n_bare) >= 4 and n_bare != n_core and n_bare in p_bare:
                    bare_cands.append(p)  # 「第七中学实验学校(小学部)」→「第七中学实验学校」精确包含，
                    # 与弱泛词候选（「八一实验学校」泛词剥离后可能吸附「八一希望学校」）隔离
                elif (not alias_multiple or len(n_core) >= 4) and len(n_core) >= 3 and n_core not in _WEAK_CORE and (n_core in p_bare or n_core in p["norm"]):
                    a_cands.append((p, p_core))
                elif len(n_core) < 3 and len(n_bare) >= 4 and n_bare in p_bare:
                    a_cands.append((p, p_core))
                elif (not alias_multiple or len(n_core) >= 4) and len(p_core) >= 2 and p_core in n:
                    b_cands.append((p, p_core))
            suffix = ""
            for w in ("小学", "中学", "初中", "高中", "学校"):
                if n.endswith(w):
                    suffix = w
                    break
            if bare_cands:
                # 去括号核心精确包含（学部括号场景）优先收敛：单独试，避免弱泛词候选
                # （「八一实验学校」泛词剥离吸附「八一希望学校」）混入 by_main 错选无括号者
                r = _pick(bare_cands, "变体命中")
                if r:
                    return r
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
    def load(cls, entities_path=None):
        """从实体表构建（唯一真源：name/aliases 已全覆盖 POI 名，school_id 承载 adcode，
        无需再传 POI 表）。entities_path 缺省用默认路径 data/registry/entity/dist/entities.json。"""
        m = cls()
        path = entities_path or os.path.join(BASE, "data/registry/entity/dist/entities.json")
        d = json.load(open(path, encoding="utf-8"))
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
    matcher = SchoolMatcher.load()
    r = matcher.resolve(name, preferred_adcode=adcode, preferred_stage=stage)
    print(json.dumps({"name": name, **r} if r else {"name": name, "result": None}, ensure_ascii=False, indent=2))


def resolve_primary_entities(entities, official, adcode):
    """官方小学名 → 实体名列表（实体表别名 + normName 全等，按区过滤）。

    官方划片表按小学法人名（裸名）公布，同区多校区并列招生（如「华阳小学」4 校区），
    返回全部命中实体名（由调用方建多条记录）；未命中返回 []（宁可缺失、不跨区错配）。

    entities: [{name, aliases, adcode}]（primary stage 实体 + POI join 的区码）
    """
    n = normName(official)
    hits = []
    for e in entities:
        if e.get("adcode") != adcode:
            continue
        if n == normName(e["name"]) or any(n == normName(a) for a in (e.get("aliases") or [])):
            hits.append(e["name"])
    return hits
