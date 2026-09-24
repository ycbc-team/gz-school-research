#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
区级官方名录 → 实体表全量校验
================================
用官方全量中学名录（data/linkage/src/official_rosters/*.json）对所在区**所有中学**
做数据覆盖校验（不只孤儿待办清单），识别：
  - MISSING    ：官方确认办初中，但实体表该区无任何 middle/high 实体对应（缺失）
  - ONLY_HIGH  ：官方确认办初中，实体表仅有 high（学段可能错配，初中实体缺失）
  - EXTRA      ：实体表有 middle 但官方名录无对应（参考信息：天河表只覆盖完中、
                 荔湾表只覆盖公办初中，超出范围属正常；若属表内范围则是疑似多余/错配）

匹配用 data/registry/entity/scripts/school_match.py 的统一归一化（normName/looseNorm/coreCampusName），
与品牌关联/backfill 同语义，避免各自为政。
用法：python3 scripts/verify_official_rosters.py  （输出 outputs/official_roster_verify_20260917.md）
"""
import json, glob, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'registry', "entity", 'scripts'))
from school_match import normName, looseNorm, coreCampusName

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER_DIR = os.path.join(ROOT, 'data/linkage/src/official_rosters')
ENTITIES = os.path.join(ROOT, 'data/registry/entity/dist/entities.json')
OUT = os.path.join(ROOT, 'outputs/official_roster_verify_20260917.md')

# 校区级匹配：官方名中带括号校区（如"(本部校区)"）与实体名校区对齐
CAMPUS_RE = re.compile(r"[（(]([^（）()]+)[）)]")


def campus_of(name):
    m = CAMPUS_RE.findall(name)
    return m[-1] if m else None


def official_has_middle(campuses):
    """名录行是否办初中（官方标注或核实结论含 初中/完中/九年制/十二年制/初级中学）。"""
    if campuses is None:
        return True  # 荔湾名录全为公办初中行
    return any(any(k in str(c.get("stage_official", "")) + str(c.get("stage_verified", ""))
                   for k in ("初中", "完中", "九年制", "十二年制", "初级中学")) for c in campuses)


def load_entities():
    ents = json.load(open(ENTITIES))['entities']
    by_adcode = {}
    for e in ents:
        ad = e['school_id'].split('-')[1] if e['school_id'].startswith('gz-') else None
        by_adcode.setdefault(ad, []).append(e)
    return by_adcode


def match_entity(official_name, ent_list, campus):
    """在实体列表里匹配官方行；返回 (matched_middle_id, matched_high_id, note)。
    匹配键 = 实体 {name, aliases} 的 norm/loose/法人core（build_entities 已把
    OFFICIAL_MIDDLE_ALIAS/GROUP_MEMBER_ALIAS 桥接挂到实体 aliases，校验直接复用，
    避免别名表双份维护）；只取 middle/high（primary 不参与初中名录校验）。"""
    o_norm = normName(official_name)
    o_loose = looseNorm(official_name)
    o_core = coreCampusName(official_name)
    mids, highs = [], []
    for e in ent_list:
        if e['stage'] == 'primary':
            continue
        names = [e['name']] + list(e.get('aliases', []))
        n_set = {normName(x) for x in names}
        l_set = {looseNorm(x) for x in names}
        c_set = {coreCampusName(x) for x in names}
        if (o_norm in n_set or o_loose in n_set or o_norm in l_set or o_loose in l_set
                or o_core in n_set or o_core in c_set):
            (mids if e['stage'] == 'middle' else highs).append(e)
    # 校区级区分：官方带校区 → 优先同校区实体
    if campus:
        def same_campus(es):
            return [e for e in es if campus in e['name'] or any(campus in a for a in e.get('aliases', []))]
        mids2, highs2 = same_campus(mids), same_campus(highs)
        if mids2 or highs2:
            return mids2, highs2, "校区名对齐"
    return mids, highs, "法人/别名命中"


def main():
    by_adcode = load_entities()
    rows, report = [], []
    for f in sorted(glob.glob(os.path.join(ROSTER_DIR, '*.json'))):
        roster = json.load(open(f))
        ad = roster['district']
        ent_list = by_adcode.get(ad, [])
        report.append(f"\n## {roster['title']}（{ad}，{len(roster['schools'])} 行）")
        report.append(f"- 来源：{roster['source_url']}（发布于 {roster['published']}）")
        report.append(f"- 范围说明：{roster.get('scope_note', '')}")
        missing, only_high, matched, cross_region = [], [], [], []
        all_ents = [e for lst in by_adcode.values() for e in lst]
        for row in roster['schools']:
            has_mid = official_has_middle(row.get('campuses'))
            mids, highs, note = match_entity(row['name'], ent_list, campus_of(row['name']))
            if not mids and not highs:
                # 跨区兜底：官方区名录含跨区真实学校（如荔湾四中集团托管丰宁，POI 在越秀 440104）
                xmids, xhighs, xnote = match_entity(row['name'], all_ents, campus_of(row['name']))
                if xmids or xhighs:
                    cross_region.append((row, xmids or xhighs, xnote))
                    continue
            if has_mid and not mids and not highs:
                missing.append((row, note))
            elif has_mid and not mids and highs:
                only_high.append((row, highs, note))
            else:
                matched.append((row, mids, note))
        report.append(f"\n### 结果：MISSING {len(missing)} / ONLY_HIGH {len(only_high)} / 已匹配 {len(matched)} / 跨区命中 {len(cross_region)}")
        if cross_region:
            report.append("\n**跨区命中（官方区名录学校、实体在其他区——跨区真实，非缺失）**：")
            for row, es, note in cross_region:
                ids = ", ".join(f"{e['school_id']} {e['name']}" for e in es[:3])
                report.append(f"- {row['name']} → {ids} | {note}")
        if missing:
            report.append("\n**MISSING（官方办初中、实体表无对应）**：")
            for row, note in missing:
                report.append(f"- {row['name']} | {row.get('address','')} | {note}")
        if only_high:
            report.append("\n**ONLY_HIGH（官方办初中、实体仅高中）**：")
            for row, highs, note in only_high:
                ids = ", ".join(f"{h['school_id']} {h['name']}" for h in highs)
                report.append(f"- {row['name']} | {row.get('address','')} | {note} | 现有high: {ids}")
        report.append("\n**已匹配（官方行有对应 middle 实体）**：")
        for row, mids, note in matched:
            ids = ", ".join(f"{m['school_id']} {m['name']}" for m in mids[:4])
            extra = "…" if len(mids) > 4 else ""
            report.append(f"- {row['name']} → {ids}{extra}")
        # 反向 EXTRA：实体 middle 但官方名录无（参考）
        official_norms = {normName(r['name']) for r in roster['schools']}
        official_cores = {coreCampusName(r['name']) for r in roster['schools']}
        extras = [e for e in ent_list if e['stage'] == 'middle'
                  and normName(e['name']) not in official_norms
                  and coreCampusName(e['name']) not in official_cores]
        report.append(f"\n**EXTRA（实体 middle 但官方名录无，{len(extras)} 所，参考）**：")
        report.append("  " + "；".join(f"{e['name']}({e['school_id']})" for e in extras[:60]))
        if len(extras) > 60:
            report.append(f"  …等 {len(extras)} 所")
        rows.append((roster['title'], len(roster['schools']), len(missing), len(only_high)))

    header = ["# 区级官方名录 × 实体表 全量校验", "",
              "校验基线：`data/linkage/src/official_rosters/*.json`（官方政府/教育局公开页面采集）",
              "对比对象：`data/registry/entity/dist/entities.json`（实体表，同区 middle/high）",
              "匹配语义：`school_match.normName / looseNorm / coreCampusName`（与品牌关联/backfill 同源）",
              "生成命令：`python3 scripts/verify_official_rosters.py`", "",
              "## 汇总", "", "| 名录 | 行数 | MISSING | ONLY_HIGH |", "|---|---|---|---|"]
    for t, n, m, o in rows:
        header.append(f"| {t} | {n} | {m} | {o} |")
    open(OUT, 'w').write("\n".join(header + report) + "\n")
    print(f"已生成 {OUT}")
    for t, n, m, o in rows:
        print(f"  {t}: {n} 行 | MISSING {m} | ONLY_HIGH {o}")


if __name__ == '__main__':
    main()
