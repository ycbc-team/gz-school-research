#!/usr/bin/env python3
"""
POI 匹配工具：输入学校名列表，输出 poi_match 四分类。
用法：python3 match_poi.py <json_file_with_names>
输入 JSON: {"schools": ["校名1", "校名2", ...]}
输出 JSON: {"results": [{"name": "...", "poi_match": "...", "matched_name": "...", "stage": "...", "district": "..."}]}
"""
import json, re, sys, os

BASE = "/Users/bytedance/Developer/gz_school_research"
SEVEN_DISTRICTS = {"440103":"荔湾","440104":"越秀","440105":"海珠","440106":"天河","440111":"白云","440112":"黄埔","440113":"番禺"}
FAR_DISTRICTS = {"440114":"花都","440115":"南沙","440117":"从化","440118":"增城"}
FAR_KEYWORDS = ["花都","南沙","增城","从化","英德","清远","佛山","东莞","韶关","梅州","河源","惠州","汕头","湛江","肇庆","江门","阳江","茂名","揭阳","潮州","汕尾","云浮","珠海","中山"]

# 括号内是“校区/学部/地址类”限定词时保留（影响校区区分）；状态词与泛化词不参与匹配
_PAREN_KEEP = ("校区", "校区)", "部", "园", "本部", "分教点", "教学点", "南", "北", "东", "西", "中")
_PAREN_DROP = ("建设中", "在建", "筹建", "规划", "拟建", "待建", "新开办", "暂定", "筹办", "装修", "工地", "选址", "暂停营业")

# 泛词后缀：substring 匹配前先剥离，避免「广州实验中学」规约成「实验中学」后吸附任何含「实验中学」的成员
_GENERIC_SUFFIX = ("实验中学", "附属实验学校", "外国语实验学校", "实验学校", "外国语学校", "附属中学", "中学", "附属小学", "小学", "学校", "初中部", "小学部", "高中部")

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

def norm(name):
    if not name: return ""
    s = name.strip()
    s = s.replace("（","(").replace("）",")").replace("【","[").replace("】","]")
    # 只剥离状态/泛化括号（如“建设中”），保留校区类括号（如“(东风广场校区)”）
    s = re.sub(r"[\(\[][^()\[\]]*[\)\]]", lambda m: "" if any(k in m.group(0) for k in _PAREN_DROP) else m.group(0), s)
    # 只去"广州市"行政区划前缀
    s = s.replace("广州市","")
    # 区名归一：仅剥离"XX区"中的区字（限已知区名），使「白云区广大附中实验中学」与「广州市白云广大附中实验中学」对齐
    s = re.sub(r"(越秀|海珠|天河|荔湾|白云|黄埔|番禺|南沙|增城|从化|花都|萝岗)区", r"\1", s)
    # 前导区名剥离：成员名常带区名前缀而 POI 名不带（「白云区广大附中实验中学(南校区)」vs「广大附中实验中学(南校区)」），
    # 剥除前导区名使精确命中成立；但剩余过短或为纯泛词时保留（「白云中学」→「中学」、「天河外国语学校」→「外国语学校」都是泛词毁名）
    for _d in ("白云", "越秀", "海珠", "天河", "荔湾", "黄埔", "番禺", "萝岗"):
        if s.startswith(_d) and len(s) - len(_d) >= 4 and s[len(_d):] not in _GENERIC_SUFFIX:
            s = s[len(_d):]
            break
    # 前导"广州"是校名成分（「广州中学」剥成「中学」是泛词毁名），仅在剩余非纯泛词时剥离
    # （「广州大学附属中学」→「大学附属中学」对齐；须在区名剥离后，区名后的「广州」同样要处理）
    if s.startswith("广州") and len(s) - 2 >= 4 and s[2:] not in _GENERIC_SUFFIX:
        s = s[2:]
    s = re.sub(r"\s+","",s)
    return s

def load_poi(path, stage):
    d = json.load(open(path))
    out = []
    for s in d.get("schools",[]):
        out.append({"name":s["name"],"norm":norm(s["name"]),"adcode":s.get("adcode",""),"stage":stage,"school_id":s.get("school_id","")})
    return out

def load_aliases(path):
    """别名表：norm_alias -> 实体列表（一个别名可能被多个实体共享，如「广铁一中铁英学校」
    同时是番禺东/西校区别名、泛称「广州大学附属中学」同时是大学城/黄华路校区别名）。
    保留全部实体，由 match_school 结合 preferred_adcode 收敛，避免"后写覆盖"式错配。"""
    d = json.load(open(path))
    alias_map = {}  # norm_alias -> [entity]
    for e in d.get("entities",[]):
        key = norm(e["name"])
        alias_map.setdefault(key, []).append({"name":e["name"],"stage":e.get("stage",""),"aliases":[norm(a) for a in e.get("aliases",[])]})
        for a in e.get("aliases",[]):
            k = norm(a)
            alias_map.setdefault(k, []).append({"name":e["name"],"stage":e.get("stage",""),"aliases":[]})
            # build_entities 的 normName 会全删括号，match_poi.norm 保留校区括号（如「(本部)」）：
            # 补一个"去括号"key，使「广州空港实验中学(本部)」与别名「广州空港实验中学本部」对齐
            k2 = k.replace("(", "").replace(")", "")
            if k2 != k:
                alias_map.setdefault(k2, []).append({"name":e["name"],"stage":e.get("stage",""),"aliases":[]})
    return alias_map

def match_school(name, poi_all, alias_map, preferred_adcode=None, preferred_stage=None):
    """
    preferred_adcode：构建某区招生计划时传入该区 adcode，命中候选时优先取同区 POI；
    preferred_stage：命中候选时优先取指定学段 POI（如初中计划优先初中部，避免选到高中部）。
    收敛顺序：同区唯一 → 同区同阶段唯一 → 全局唯一（跨区招生记录如培英鹤洞校区）→ 缺失。
    """
    n = norm(name)
    def bare(s):
        return re.sub(r"[\(（][^()（）]*[\)）]", "", s)
    def _mk(p, poi_match):
        district = SEVEN_DISTRICTS.get(p["adcode"], FAR_DISTRICTS.get(p["adcode"],"未知"))
        return {"poi_match":poi_match,"matched_name":p["name"],"stage":p["stage"],"district":district,"school_id":p["school_id"]}
    def _pick(cands, poi_match, district_guard=True):
        """收敛：先按 school_id 去重（同址多学部 POI 在初中/高中库各一份，视为同一候选），
        再按 同阶段唯一 → 主 POI（无括号）唯一 → 同区唯一 → 全局唯一（允许跨区招生记录）→ 缺失。
        宁可缺失、不跨区错配：多候选且无法收敛到唯一时返回 None，由调用方以显式 school_id 锚定补救。
        district_guard=False 用于 alias 精确命中（2a/2b）：实体身份映射是人工确认的显式关系，
        跨区也成立（如白云培英集团核心校「广州市培英中学」本部在荔湾鹤洞校区）；模糊防错配只约束 substring 吸附。"""
        if not cands: return None
        seen = {}
        for c in cands:
            if c["school_id"] not in seen:
                seen[c["school_id"]] = c
            elif preferred_stage and c["stage"] == preferred_stage and seen[c["school_id"]]["stage"] != preferred_stage:
                # 同 id 多学部 POI（九年制/完中在小学/初中/高中库各一份）：保留与目标学段一致的副本，
                # 避免"去重后只剩小学部副本"导致初中阶段过滤落空（如广州华美英语实验学校）
                seen[c["school_id"]] = c
        cands = list(seen.values())
        def by_stage(cs):
            if preferred_stage:
                st = [c for c in cs if c["stage"] == preferred_stage]
                if len(st) == 1: return st[0]
            return None
        def by_main(cs):
            # 主 POI（名不含校区括号）优先于分校区 POI
            mains = [c for c in cs if "(" not in c["name"] and "（" not in c["name"]]
            if len(mains) == 1: return mains[0]
            return None
        if preferred_adcode and district_guard:
            same = [c for c in cands if c["adcode"] == preferred_adcode]
            if len(same) == 1:
                return _mk(same[0], poi_match)
            if same:
                r = by_stage(same)
                if r: return _mk(r, poi_match)
                r = by_main(same)
                if r: return _mk(r, poi_match)
                # 同区多候选无法收敛：宁可缺失（由调用方显式锚定），不跨区错配
                return None
            # 同区无候选：仅当成员名含"其他区"区名（如白云名单里的培英鹤洞校区→荔湾）才回退全局唯一；
            # 否则宁可缺失、不跨区错配（如「海珠晓港湾小学」不落到黄埔「港湾小学」）
            own_name = name.replace("广州市","")
            self_dist = SEVEN_DISTRICTS.get(preferred_adcode, "")
            has_other = any(k in own_name for k in ("越秀","海珠","天河","荔湾","白云","黄埔","番禺","萝岗") if k != self_dist)
            if has_other:
                r = by_stage(cands)
                if r: return _mk(r, poi_match)
                r = by_main(cands)
                if r: return _mk(r, poi_match)
                if len(cands) == 1:
                    return _mk(cands[0], poi_match)
            return None
        r = by_stage(cands)
        if r: return _mk(r, poi_match)
        r = by_main(cands)
        if r: return _mk(r, poi_match)
        if len(cands) == 1:
            return _mk(cands[0], poi_match)
        return None
    # 0. 远郊成员拦截：必须在 exact/alias 命中之后（POI 库自身含"暨南大学附属增城实验学校"等远郊 POI，
    #    自我匹配/同区成员须先精确命中自己），但要在 substring 吸附之前（防「新塘镇第三中学」→「广州市第三中学」）。
    #    含"中山"的七区真实校（中山三路小学/中山大学附属中学等）经 exact/alias 命中自己，不会被拦到。
    # 1. exact norm match in POI
    r = _pick([p for p in poi_all if p["norm"] == n], "精确命中")
    if r: return r
    # 2. alias match（一个别名可能对应多个实体：跨实体收集 POI 候选，同区优先收敛）
    if n not in alias_map:
        # build_entities.normName 全删括号而本 norm 保留校区括号（如「(本部)」）：回退查去括号 key
        _n_flat = n.replace("(", "").replace(")", "")
        if _n_flat != n and _n_flat in alias_map:
            n = _n_flat
    if n in alias_map:
        ents = alias_map[n]
        # 2a. 先精确匹配实体完整名（含校区括号，避免多校区 norm 歧义）；身份映射显式确认，跨区不拦截
        ent_names = {e["name"] for e in ents}
        r = _pick([p for p in poi_all if p["name"] in ent_names], "变体命中", district_guard=False)
        if r: return r
        # 2b. 再按 norm 匹配
        ent_norms = {norm(e["name"]) for e in ents}
        r = _pick([p for p in poi_all if p["norm"] in ent_norms], "变体命中", district_guard=False)
        if r: return r
        # 2b5. 实体主校 POI 缺失时，用实体核心名前缀在同区找分校区 POI（如「华阳小学」→「华阳小学(华成校区)」）
        # 修复"主校无独立 POI、只有分校区 POI"导致的成员丢失（46 处漂移主因之一）
        # base 必须剥校区括号：实体全名含"(东校区)"时 startswith 只命中同校区 POI，
        # 会把共享别名（如「广铁一中铁英学校」=番禺东/西校区别名）错收敛到单个校区
        for e in ents:
            base = bare(norm(e["name"]))
            if len(base) < 4:
                continue
            cands = [p for p in poi_all if p["norm"].startswith(base) and (not preferred_adcode or p["adcode"] == preferred_adcode)]
            # 学段限定优先：实体名含"初中部/小学部/高中部"时，只保留候选名含同限定词的 POI
            # （「云雅实验学校(初中部)」实体不应落到无括号的「云雅实验学校」主校）
            for _kw in ("初中部", "小学部", "高中部"):
                if _kw in norm(e["name"]) and len(cands) > 1:
                    suff = [c for c in cands if _kw in c["norm"]]
                    if suff:
                        cands = suff
                        break
            r = _pick(cands, "变体命中")
            if r:
                return r
        # 2c. 实体存在但 POI 无坐标：未给区上下文时保留原兜底；给了区上下文则继续 substring 找同区 POI
        if not preferred_adcode:
            return {"poi_match":"变体命中","matched_name":ents[0]["name"],"stage":ents[0]["stage"],"district":"实体表无坐标","school_id":""}
    # 2d. far district keyword check（exact/alias 均未命中后才拦截远郊）
    for kw in FAR_KEYWORDS:
        if kw in name:
            return {"poi_match":"远郊不在POI范围","matched_name":"","stage":"","district":kw,"school_id":""}
    # 3. substring / contains match (variant)：剥离泛词后按核心词匹配，同区优先，防「实验中学」类泛词吸附
    if n:
        n_core = strip_generic(n)
        _WEAK_CORE = ("白云", "越秀", "海珠", "天河", "荔湾", "黄埔", "番禺", "萝岗",
                      "第一", "第二", "第三", "第四", "第五", "第六", "第七", "第八", "第九", "第十")
        _NON_SCHOOL = ("充电站", "停车场", "广场", "大厦", "中心", "公园", "小区", "花园", "银行", "医院", "超市", "餐厅", "酒店", "公司", "商厦")
        a_cands, b_cands = [], []  # A支=成员核心在POI（专属高）；B支=POI核心在成员（按位置收敛）
        for p in poi_all:
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
            # A 支优先（成员核心词直接命中 POI，如「云英实验学校」→「云英实验附属小学」）
            if suffix:
                suff = [c for c in a_cands if bare(c[0]["norm"]).endswith(suffix) or c[0]["norm"].endswith(suffix)]
                if len(suff) >= 1:
                    a_cands = suff  # 后缀一致的候选优先；全不一致时保留原候选（南悦充电站类已被 _NON_SCHOOL 排除）
            cands = a_cands
        else:
            cands = b_cands
            # B 支位置优先：POI 核心词在成员名中出现位置越靠后越专属
            # （「宝源学校」→「宝源」优于集团名「乐贤坊」；「金广实验学校」→「金广实验」优于区名「白云」）
            if len(cands) > 1:
                b_pos = [(p, n.find(pc)) for p, pc in cands if pc and pc in n]
                if b_pos:
                    maxpos = max(pos for _, pos in b_pos)
                    if maxpos > 0:
                        top = [p for p, pos in b_pos if pos == maxpos]
                        if len(top) == 1:
                            cands = [(p, pc) for p, pc in cands if p in top]
        # 泛词后缀一致优先：成员"…小学"时候选"…小学"优先于"…中学"（如耀华小学 vs 耀华中学）
        if suffix and len(cands) > 1:
            suff = [c for c in cands if bare(c[0]["norm"]).endswith(suffix) or c[0]["norm"].endswith(suffix)]
            if suff:
                cands = suff
        # 学段限定优先：成员名含"(初中部)/(小学部)/(高中部)"等限定词时，候选名含对应限定词的优先
        # （如「云雅实验学校(初中部)」应命中「云雅实验学校初中部」而非无括号的「云雅实验学校」主校）
        for _kw in ("(初中部)", "初中部", "(小学部)", "小学部", "(高中部)", "高中部", "(中学)", "中学部"):
            if _kw in n and len(cands) > 1:
                suff = [c for c in cands if _kw in c[0]["norm"]]
                if suff:
                    cands = suff
                    break
        r = _pick([c[0] for c in cands], "变体命中")
        if r: return r
    # 4. default: 7区内真实缺失
    return {"poi_match":"7区内真实缺失","matched_name":"","stage":"","district":"","school_id":""}

def main():
    if len(sys.argv) < 2:
        print("usage: match_poi.py <input.json>", file=sys.stderr)
        sys.exit(1)
    inp = json.load(open(sys.argv[1]))
    names = inp.get("schools", inp.get("names", []))
    poi_all = []
    poi_all += load_poi(os.path.join(BASE,"data/primary/schools-gz.json"),"小学")
    poi_all += load_poi(os.path.join(BASE,"data/middle/schools-gz.json"),"初中")
    poi_all += load_poi(os.path.join(BASE,"data/high/schools-gz.json"),"高中")
    alias_map = load_aliases(os.path.join(BASE,"data/registry/entities.json"))
    results = []
    for name in names:
        r = match_school(name, poi_all, alias_map)
        r["name"] = name
        results.append(r)
    print(json.dumps({"results":results}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
