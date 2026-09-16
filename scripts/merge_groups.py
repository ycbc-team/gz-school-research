#!/usr/bin/env python3
"""合并7区partial + 2026招考办表 + brand_groups → education_groups.json"""
import json, re, os, sys

BASE = "/Users/bytedance/Developer/gz_school_research"
TODAY = "2026-09-14"

def norm(name):
    if not name: return ""
    s = name.strip().replace("（","(").replace("）",")").replace("【","[").replace("】","]")
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = s.replace("广州市","").replace("广州","")
    s = re.sub(r"\s+","",s)
    return s

def load_json(path):
    return json.load(open(os.path.join(BASE, path)))

# 1. 加载7区partial
partials = {}
district_files = {
    "越秀": "data/registry/_partial_yuexiu_groups.json",
    "海珠": "data/registry/_partial_haizhu_groups.json",
    "天河": "data/registry/_partial_tianhe_groups.json",
    "荔湾": "data/registry/_partial_liwan_groups.json",
    "黄埔": "data/registry/_partial_huangpu_groups.json",
    "白云": "data/registry/_partial_baiyun_groups.json",
    "番禺": "data/registry/_partial_panyu_groups.json",
}
all_groups = []
anchors = load_json("scripts/groups_anchors.json") if os.path.exists(os.path.join(BASE, "scripts/groups_anchors.json")) else {"members": {}, "core_poi": {}}
member_anchors = anchors.get("members", {})
core_anchors = anchors.get("core_poi", {})
for dist, fpath in district_files.items():
    d = load_json(fpath)
    for g in d.get("groups", []):
        g.setdefault("district", dist)
        # core_poi 回填：核心校 POI 锚定来自下游锚点表（partial 保持纯采集底稿）
        if g["brand"] in core_anchors:
            g["core_poi"] = [
                {"name": cp.get("poi_name") or (g.get("core") or [""])[0], "poi_match": "已锚定",
                 "poi_name": cp.get("poi_name"), "school_id": cp.get("school_id")}
                for cp in core_anchors[g["brand"]]
            ]
        # 成员锚定：锚点表命中（可多校区）→ 已锚定；未命中 → 留空走匹配器
        for m in g.get("members", []):
            a = member_anchors.get(m["name"])
            if not a or not a.get("school_ids"):
                continue
            ids = a["school_ids"]
            names = a.get("poi_names") or [""] * len(ids)
            m["poi_match"] = "已锚定"
            if len(ids) == 1:
                m["poi_name"] = names[0] if names else ""
                m["school_id"] = ids[0]
            else:
                # 多校区：不设单一 school_id（无主校语义），全部校区放 campuses（每校区独立实体命中）
                m["poi_name"] = ""
                m["school_id"] = ""
                m["campuses"] = [
                    {"poi_name": names[i], "school_id": ids[i]}
                    for i in range(len(ids)) if names[i]
                ]
        all_groups.append(g)

print(f"7区partial合计: {len(all_groups)}集团")

# 2. 加载2026表，合并7区示范高中集团的初中成员
d2026 = load_json("data/registry/education_groups_2026.json")
far_keywords = ["花都","南沙","增城","从化"]
seven_districts = ["荔湾","越秀","海珠","天河","白云","黄埔","番禺"]

# 建立partial group的核心校索引（norm core name → group）
core_index = {}
for g in all_groups:
    for c in g.get("core", []):
        core_index[norm(c)] = g

merged_2026 = 0
new_from_2026 = 0
for g2026 in d2026["groups"]:
    core = g2026["core"]
    # 跳过远郊核心校
    if any(k in core for k in far_keywords):
        continue
    # 省市属品牌（华附/广雅/二中/六中/侨中/广附/广外）由brand_groups处理，这里跳过
    provincial_brands = ["华南师范大学附属中学","广东广雅中学","广州市第二中学","广州市第六中学",
                         "广东华侨中学","广州大学附属中学","广州外国语学校"]
    if any(norm(b) in norm(core) or norm(core) in norm(b) for b in provincial_brands):
        continue
    
    ncore = norm(core)
    matched = None
    # 精确匹配优先
    for nc, g in core_index.items():
        if ncore == nc:
            matched = g
            break
    # 然后前缀/后缀匹配（较短长度>=4，避免"中学"匹配所有）
    if not matched:
        for nc, g in core_index.items():
            if len(ncore) >= 4 and len(nc) >= 4 and (ncore.startswith(nc) or nc.startswith(ncore) or ncore.endswith(nc) or nc.endswith(ncore)):
                matched = g
                break
    
    if matched:
        # 合并2026表的初中成员
        existing_names = {norm(m["name"]) for m in matched.get("members", [])}
        added = 0
        for mname in g2026.get("members", []):
            if norm(mname) not in existing_names:
                matched["members"].append({
                    "name": mname,
                    "stage": "初中",
                    "source_url": d2026.get("source",""),
                    "verified": TODAY,
                    "poi_match": "待比对",
                    "poi_name": "",
                    "school_id": "",
                    "note": "招考办2026名额分配表"
                })
                existing_names.add(norm(mname))
                added += 1
        if added > 0:
            merged_2026 += 1
            # 补充source_url
            src = d2026.get("source","")
            if src and src not in matched.get("source_urls", []):
                matched.setdefault("source_urls", []).append(src)
    else:
        # 7区示范高中集团但partial里没有（如番禺实验中学），新建
        members = []
        for mname in g2026.get("members", []):
            members.append({
                "name": mname, "stage": "初中",
                "source_url": d2026.get("source",""),
                "verified": TODAY,
                "poi_match": "待比对", "poi_name": "", "school_id": "",
                "note": "招考办2026名额分配表"
            })
        # 推断district
        district = ""
        for d in seven_districts:
            if d in core:
                district = d
                break
        if not district:
            district = "未知"
        all_groups.append({
            "brand": core + "教育集团",
            "district": district,
            "core": [core],
            "level": g2026.get("level","区属"),
            "type": "完中集团",
            "members": members,
            "source_urls": [d2026.get("source","")],
            "note": "招考办2026名额分配表口径，区文件未单独列集团"
        })
        new_from_2026 += 1

print(f"2026表合并: 补充{merged_2026}个集团的初中成员, 新建{new_from_2026}个集团")

# 3. 加载brand_groups，合并8个重点品牌
dbrand = load_json("data/registry/brand_groups.json")
brand_added = 0
for b in dbrand.get("brands", []):
    brand_name = b["brand"]
    # brand名可能已含"教育集团"，也可能不含（如清华附中湾区学校）
    group_brand = brand_name if "教育集团" in brand_name else brand_name + "教育集团"
    # 检查是否已在all_groups里
    exists = False
    for g in all_groups:
        if norm(group_brand) == norm(g["brand"]) or norm(g["brand"]) in norm(group_brand) or norm(group_brand) in norm(g["brand"]):
            if len(norm(group_brand)) >= 4 and len(norm(g["brand"])) >= 4:
                exists = True
                break
    if exists:
        continue
    # 找核心校
    core_school = brand_name
    for u in b.get("units", []):
        if "核心" in u.get("role",""):
            core_school = u["name"]
            break
    # 构建成员（排除核心校本部，核心校放core字段）
    members = []
    for u in b.get("units", []):
        role = u.get("role","")
        if "核心" in role and "本部" in role:
            continue
        # 推断学段
        stage = ""
        uname = u["name"]
        if "小学" in uname: stage = "小学"
        elif "幼儿园" in uname: continue  # 不录幼儿园
        elif "九年一贯" in uname or "实验学校" in uname or "外国语学校" in uname or "铁一学校" in uname or "铁英学校" in uname: stage = "九年一贯"
        elif "中学" in uname or "高中" in uname: stage = "完中"
        elif "湾区学校" in uname: stage = "完中"
        # 用poi_names里的名称做POI匹配（更准确）
        poi_match_name = uname
        if u.get("poi_names"):
            poi_match_name = u["poi_names"][0]
        members.append({
            "name": uname,
            "stage": stage,
            "source_url": u.get("source_url",""),
            "verified": TODAY,
            "poi_match": "已锚定" if u.get("school_ids") else "待比对",
            "poi_name": (u.get("poi_names") or [""])[0] if u.get("school_ids") else "",
            "school_id": u.get("school_ids", [""])[0] if u.get("school_ids") else "",
            "poi_match_name": poi_match_name,
            "legal": u.get("legal",""),
            "relation": role
        })
    all_groups.append({
        "brand": group_brand,
        "district": "跨区",
        "core": [core_school],
        "level": "省市属",
        "type": "混合学段集团",
        "members": members,
        "source_urls": sorted(set(u.get("source_url","") for u in b.get("units",[]) if u.get("source_url"))),
        "note": b.get("brand_note","")
    })
    brand_added += 1

print(f"brand_groups新增: {brand_added}个品牌集团")

# 4. 对"待比对"的成员跑POI匹配；已有 school_id 的成员是人工确认锚点，保留不再重匹配
#    （产物漂移根因之一：全量重跑会把锚点覆盖成匹配器的不同结果；锚点机制 + 区上下文收敛后重跑稳定）
import importlib.util
ADCODE_OF = {"荔湾":"440103","越秀":"440104","海珠":"440105","天河":"440106","白云":"440111","黄埔":"440112","番禺":"440113"}
_spec = importlib.util.spec_from_file_location("match_poi", os.path.join(BASE, "scripts/match_poi.py"))
mp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mp)

pending = []  # (group, member)
for g in all_groups:
    for m in g.get("members", []):
        # 锚点 = 锚点表已命中（poi_match="已锚定"，含多校区 campuses）；其余 school_id 空的一律交给匹配器
        if not m.get("school_id") and m.get("poi_match") != "已锚定":
            pending.append((g, m))

if pending:
    poi_all = []
    poi_all += mp.load_poi(os.path.join(BASE,"data/primary/schools-gz.json"),"小学")
    poi_all += mp.load_poi(os.path.join(BASE,"data/middle/schools-gz.json"),"初中")
    poi_all += mp.load_poi(os.path.join(BASE,"data/high/schools-gz.json"),"高中")
    alias_map = mp.load_aliases(os.path.join(BASE,"data/registry/entities.json"))
    matched = 0
    for g, m in pending:
        mname = m.get("poi_match_name", m["name"])
        # 成员级区名解析：成员名含区名（如「广州市增城区新塘镇第三中学」）时用成员区名覆盖集团区，
        # 避免"集团在越秀、成员在增城"时把成员匹配到集团所在区的同名校
        adc = ADCODE_OF.get(g.get("district", ""))
        for dist, code in ADCODE_OF.items():
            if dist in mname:
                adc = code
                break
        r = mp.match_school(mname, poi_all, alias_map, preferred_adcode=adc)
        m["poi_match"] = r.get("poi_match", "7区内真实缺失")
        m["poi_name"] = r.get("matched_name", "")
        m["school_id"] = r.get("school_id", "")
        if r.get("poi_match") == "精确命中" or r.get("poi_match") == "变体命中":
            matched += 1
        if "poi_match_name" in m:
            del m["poi_match_name"]
    print(f"匹配 {len(pending)} 个待比对成员，命中 {matched} 个")

# 5. 统计
total_groups = len(all_groups)
total_members = sum(len(g.get("members",[])) for g in all_groups)
exact = sum(1 for g in all_groups for m in g["members"] if m.get("poi_match")=="精确命中")
variant = sum(1 for g in all_groups for m in g["members"] if m.get("poi_match")=="变体命中")
missing = sum(1 for g in all_groups for m in g["members"] if m.get("poi_match")=="7区内真实缺失")
far = sum(1 for g in all_groups for m in g["members"] if m.get("poi_match")=="远郊不在POI范围")

print(f"\n=== 合并后统计 ===")
print(f"集团总数: {total_groups}")
print(f"成员总数: {total_members}")
print(f"精确命中: {exact}, 变体命中: {variant}, 7区内缺失: {missing}, 远郊: {far}")

# 按区统计
from collections import Counter
district_count = Counter(g["district"] for g in all_groups)
for d, c in sorted(district_count.items()):
    ms = sum(len(g["members"]) for g in all_groups if g["district"]==d)
    print(f"  {d}: {c}集团, {ms}成员")

# 6. 写出（支持 argv[1] 输出到指定路径，供 check_groups_drift.py 做"产物 vs 重跑"一致性校验）
out = {
    "title": "广州7区教育集团名录（区教育局官方口径+招考办名额分配表+品牌组）",
    "updated": TODAY,
    "source_scope": "荔湾/越秀/海珠/天河/白云/黄埔/番禺",
    "note": "P3全量补录：区属非示范集团+小学集团以各区政府/教育局官方文件为来源；示范高中集团初中成员来自招考办2026名额分配表；8个重点品牌来自brand_groups.json。远郊4区（花都/南沙/增城/从化）集团核心校不录，跨区成员标注'远郊不在POI范围'。",
    "stats": {
        "total_groups": total_groups,
        "total_members": total_members,
        "poi_exact": exact,
        "poi_variant": variant,
        "poi_missing_7dist": missing,
        "poi_far": far,
    },
    "groups": all_groups
}

OUT_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "data/registry/education_groups.json")
with open(OUT_PATH, "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"\n已写入 {OUT_PATH}")

# 输出7区内真实缺失清单
print(f"\n=== 7区内真实缺失清单（{missing}所）===")
for g in all_groups:
    for m in g["members"]:
        if m.get("poi_match") == "7区内真实缺失":
            print(f"  [{g['district']}] {g['brand']} → {m['name']} ({m.get('stage','')})")
