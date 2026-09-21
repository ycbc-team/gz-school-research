#!/usr/bin/env python3
"""构建公共 school_id → 集团映射（详情页品牌卡与初中明细分组的唯一权威产物）。

原则（用户拍板）：运行时完全用 school_id 匹配，不写名字匹配逻辑。
名称匹配只允许发生在本数据层构建期，且必须经 entities 表（1552 条，含 aliases）反查：

1. education_groups.json（85 集团）：core_poi / members / campuses 显式 school_id 全量收录
2. brand_groups.json（8 大品牌）：显式 school_ids 收录；缺外键的 unit 用 entities 表反查
   name / poi_names → school_id，解析成功写回 brand_groups.json（units.school_ids 补全，
   setdefault 不覆盖已有），让品牌数据层自洽（成员行可跳转）
3. 同一 school_id 同时命中 education 与 brand：education 优先（与 shared groupOfSchool 现序一致）

产物：data/registry/group/dist/school_groups.json
  {"schoolGroups": {"<school_id>": {"brand": "...", "source": "education|brand"}}}
纯 id 映射，运行时不感知任何名字。

另输出构建期缺失报告（stderr/stdout）：
- brand units 反查失败清单（区外校等 entities 表不覆盖 → 需人工补 school_ids 外键）
- education 源内无 school_id 的成员（数据源自身缺口）

用法：python3 data/registry/group/scripts/build_school_groups.py [--write-brand]
  --write-brand: 把反查成功的 school_id 写回 brand_groups.json（数据层补全，默认只报告不写）
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
REG = os.path.join(ROOT, "data", "registry")

EDU_PATH = os.path.join(REG, "group", "dist", "education_groups.json")
BRAND_PATH = os.path.join(REG, "group", "src", "brand_groups.json")
ENT_PATH = os.path.join(REG, "entity", "dist", "entities.json")
OUT_PATH = os.path.join(REG, "group", "dist", "school_groups.json")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def norm_key(s):
    """构建期名称归一：去全部括号、去「广州市」前缀、去空白（与 build_entities normName 同语义）。"""
    return re.sub(r"[（(）)]", "", s).replace("广州市", "").replace(" ", "").strip()


def resolve_school_ids(name, entities, strip_suffix=True):
    """entities 表反查 school_id 集合，分层短路（防泛名吸附）：
    1. name 精确全等 → 只收 name 命中的实体（如「清华附中湾区学校」只收本部，不收 aliases
       里泛名桥接的智谷/智慧城校区）
    2. norm_key 归一全等（去括号/去「广州市」/去空格）→ 只收该层命中
       （如「广州市黄埔区苏元学校（二中苏元）」去括号后命中苏元）
    3. aliases 命中 → 收集（别名桥接，如「会元学校」→「广州市黄埔区会元学校」）
    4. 剥「(小学|初中|高中)部」学部后缀再查（仅唯一命中才采用，避免吸附）
    同名多 school_id（同址多学部 POI 各一实体）全部收集——都是该品牌成员，不做唯一收敛。
    注意：必须逐实体比较 e 自己的 name/aliases，禁止用「全局 cands 列表 + 遍历全部实体」，
    否则任一同名实体存在会导致全部实体被误收。"""
    nk = norm_key(name)
    # 1. name 精确全等（含全半角括号/空格容忍）
    pat = re.compile("^" + re.escape(name).replace(r"\(", "[(（]").replace(r"\)", "[)）]").replace(r"\ ", r"\s*") + "$")
    s1 = {e["school_id"] for e in entities if pat.match(e["name"])}
    if s1:
        return s1
    # 2. norm_key 全等（对 e 自己的 name）
    s2 = {e["school_id"] for e in entities if norm_key(e["name"]) == nk}
    if s2:
        return s2
    # 3. 剥括号内容再查（别名/注释后缀，如「苏元学校（二中苏元）」「西关广雅实验学校（西雅）」：
    #    去括号内文字后，实体 name 或 aliases 归一全等即命中；多个校区共享泛名时全部收集）
    m0 = re.search(r"[（(][^（()）]*[）)]", name)
    if m0:
        bare = (name[: m0.start()] + name[m0.end():]).strip()
        bnk = norm_key(bare)
        s3b = set()
        for e in entities:
            if norm_key(e["name"]) == bnk:
                s3b.add(e["school_id"])
        if not s3b:
            # aliases 泛名桥接（如「西关广雅实验学校」→ 南岸路校区 aliases）：多候选不收敛，
            # 宁缺毋滥返回空（保留旧外键 / 人工补），避免「广东实验中学」泛名吸附全部校区
            s3a = set()
            for e in entities:
                if any(norm_key(a) == bnk for a in e.get("aliases") or []):
                    s3a.add(e["school_id"])
            if len(s3a) == 1:
                return s3a
        elif s3b:
            return s3b
    # 4. aliases 命中（精确或 norm）
    s3 = set()
    for e in entities:
        if any(a == name or norm_key(a) == nk for a in e.get("aliases") or []):
            s3.add(e["school_id"])
    if s3:
        return s3
    # 5. 剥学部后缀（仅唯一命中才采用）
    if strip_suffix:
        m = re.search(r"[（(](?:小学|初中|高中)部[）)]$", name)
        if m:
            base = name[: m.start()]
            bnk = norm_key(base)
            s4 = {e["school_id"] for e in entities
                  if e["name"] == base or norm_key(e["name"]) == bnk
                  or any(a == base or norm_key(a) == bnk for a in e.get("aliases") or [])}
            if len(s4) == 1:
                return s4
    return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-brand", action="store_true",
                    help="把反查成功的 school_id 写回 brand_groups.json")
    args = ap.parse_args()

    edu = load(EDU_PATH)["groups"]
    brand_data = load(BRAND_PATH)
    brands = brand_data["brands"]
    entities = load(ENT_PATH)["entities"]

    # 1. education 外键全量（education 优先，先写入再 setdefault）
    mapping = {}
    edu_no_sid = []
    for g in edu:
        for p in g.get("core_poi") or []:
            if p.get("school_id"):
                mapping.setdefault(p["school_id"], {"brand": g["brand"], "source": "education"})
            else:
                edu_no_sid.append(("core_poi", g["brand"], p.get("name") or p.get("poi_name")))
        for m in g.get("members") or []:
            if m.get("school_id"):
                mapping.setdefault(m["school_id"], {"brand": g["brand"], "source": "education"})
            for c in m.get("campuses") or []:
                if c.get("school_id"):
                    mapping.setdefault(c["school_id"], {"brand": g["brand"], "source": "education"})
                else:
                    edu_no_sid.append(("campuses", g["brand"], c.get("poi_name") or c.get("name")))

    # 2. brand：显式外键 + 缺外键的用 entities 反查（构建期唯一允许的名字匹配）
    resolved, failed = [], []
    for g in brands:
        for u in g.get("units") or []:
            cands = [u.get("name")] + list(u.get("poi_names") or [])
            cands = [c for c in cands if c]
            new_ids = []
            matched = []
            for cand in cands:
                sids = resolve_school_ids(cand, entities)
                for sid in sorted(sids):
                    if sid not in new_ids:
                        new_ids.append(sid)
                        matched.append(f"{cand}→{sid}")
            old_ids = list(u.get("school_ids") or [])
            if new_ids:
                # 品牌关联覆盖新旧两套 id 的并集：entities 重建后新旧实体并存，
                # 旧 id 仍被 quota/ranking 等数据链路引用（如苏元西校区 gz-440112-a0244635），
                # 新 id 是规范实体——任一端都不允许丢失品牌卡（"修改前后数据不缺少"）
                merged = []
                for sid in list(old_ids) + new_ids:
                    if sid and sid not in merged:
                        merged.append(sid)
                if merged != old_ids:
                    u["school_ids"] = merged
                    resolved.append({"unit": u.get("name"), "brand": g["brand"],
                                     "old": old_ids, "new": new_ids, "merged": merged,
                                     "matched": matched})
            else:
                failed.append({"unit": u.get("name"), "brand": g["brand"], "cands": cands,
                               "has_old": old_ids})
            for sid in (merged if new_ids else old_ids):
                if sid:
                    mapping.setdefault(sid, {"brand": g["brand"], "source": "brand"})

    # 3. 写回 brand_groups.json（可选）
    if args.write_brand and resolved:
        # 保持原文件 1 空格缩进（brand_groups.json 为人工审阅产物，避免全文件重排的不可 review diff）
        with open(BRAND_PATH, "w", encoding="utf-8") as f:
            json.dump(brand_data, f, ensure_ascii=False, indent=1)
        print(f"[写回] brand_groups.json 补全 {len(resolved)} 个 unit 的 school_ids")

    # 4. 产物
    out = {"schoolGroups": mapping}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n_edu = sum(1 for v in mapping.values() if v["source"] == "education")
    n_br = sum(1 for v in mapping.values() if v["source"] == "brand")
    print(f"[产物] school_groups.json: {len(mapping)} 个 school_id（education {n_edu} / brand {n_br}）")

    # 5. 缺失报告
    if edu_no_sid:
        print("\n[缺失] education 源内无 school_id 的成员（需数据源补外键）:")
        for kind, brand, nm in edu_no_sid[:50]:
            print(f"  - {kind} | {brand} | {nm}")
    if failed:
        print(f"\n[缺失] brand units 反查失败 {len(failed)} 个（entities 表不覆盖，需人工补 school_ids）:")
        for f_ in failed:
            print(f"  - {f_['brand']} | {f_['unit']} | cands={f_['cands']}")
    if resolved:
        print(f"\n[解析] brand units 以 entities 校正/补齐 {len(resolved)} 个:")
        for r_ in resolved:
            print(f"  ✓ {r_['brand']} | {r_['unit']}")
            print(f"      old={r_['old']} + new={r_['new']} → merged={r_['merged']}（{'; '.join(r_['matched'])}）")


if __name__ == "__main__":
    sys.exit(main())
