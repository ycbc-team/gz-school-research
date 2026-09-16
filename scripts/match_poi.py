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

def norm(name):
    if not name: return ""
    s = name.strip()
    s = s.replace("（","(").replace("）",")").replace("【","[").replace("】","]")
    # 只剥离状态/泛化括号（如“建设中”），保留校区类括号（如“(东风广场校区)”）
    s = re.sub(r"[\(\[][^()\[\]]*[\)\]]", lambda m: "" if any(k in m.group(0) for k in _PAREN_DROP) else m.group(0), s)
    s = s.replace("广州市","").replace("广州","")
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
            alias_map.setdefault(norm(a), []).append({"name":e["name"],"stage":e.get("stage",""),"aliases":[]})
    return alias_map

def match_school(name, poi_all, alias_map, preferred_adcode=None, preferred_stage=None):
    """
    preferred_adcode：构建某区招生计划时传入该区 adcode，命中候选时优先取同区 POI；
    preferred_stage：命中候选时优先取指定学段 POI（如初中计划优先初中部，避免选到高中部）。
    收敛顺序：同区唯一 → 同区同阶段唯一 → 全局唯一（跨区招生记录如培英鹤洞校区）→ 缺失。
    """
    n = norm(name)
    def _mk(p, poi_match):
        district = SEVEN_DISTRICTS.get(p["adcode"], FAR_DISTRICTS.get(p["adcode"],"未知"))
        return {"poi_match":poi_match,"matched_name":p["name"],"stage":p["stage"],"district":district,"school_id":p["school_id"]}
    def _pick(cands, poi_match):
        """收敛：先按 school_id 去重（同址多学部 POI 在初中/高中库各一份，视为同一候选），
        再按 同区唯一 → 同区同阶段唯一 → 全局唯一（允许跨区招生记录）→ 缺失。"""
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
        if preferred_adcode:
            same = [c for c in cands if c["adcode"] == preferred_adcode]
            if len(same) == 1:
                return _mk(same[0], poi_match)
            if same:
                r = by_stage(same)
                if r: return _mk(r, poi_match)
                return None
            # 同区无候选：跨区招生记录回退全局唯一（如白云名单里的培英鹤洞校区）
            r = by_stage(cands)
            if r: return _mk(r, poi_match)
            if len(cands) == 1:
                return _mk(cands[0], poi_match)
            return None
        r = by_stage(cands)
        if r: return _mk(r, poi_match)
        if len(cands) == 1:
            return _mk(cands[0], poi_match)
        return None
    # 1. exact norm match in POI
    r = _pick([p for p in poi_all if p["norm"] == n], "精确命中")
    if r: return r
    # 2. alias match（一个别名可能对应多个实体：跨实体收集 POI 候选，同区优先收敛）
    if n in alias_map:
        ents = alias_map[n]
        # 2a. 先精确匹配实体完整名（含校区括号，避免多校区 norm 歧义）
        ent_names = {e["name"] for e in ents}
        r = _pick([p for p in poi_all if p["name"] in ent_names], "变体命中")
        if r: return r
        # 2b. 再按 norm 匹配
        ent_norms = {norm(e["name"]) for e in ents}
        r = _pick([p for p in poi_all if p["norm"] in ent_norms], "变体命中")
        if r: return r
        # 2c. 实体存在但 POI 无坐标：未给区上下文时保留原兜底；给了区上下文则继续 substring 找同区 POI
        if not preferred_adcode:
            return {"poi_match":"变体命中","matched_name":ents[0]["name"],"stage":ents[0]["stage"],"district":"实体表无坐标","school_id":""}
    # 3. substring / contains match (variant)
    r = _pick([p for p in poi_all if n and (n in p["norm"] or p["norm"] in n)], "变体命中")
    if r: return r
    # 4. far district keyword check
    for kw in FAR_KEYWORDS:
        if kw in name:
            return {"poi_match":"远郊不在POI范围","matched_name":"","stage":"","district":kw,"school_id":""}
    # 5. default: 7区内真实缺失
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
