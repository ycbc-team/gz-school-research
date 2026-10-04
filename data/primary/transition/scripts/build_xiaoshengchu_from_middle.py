#!/usr/bin/env python3
"""从初中招生转录反推小升初候选产物（不改正式 dist）。

输入仅为 data/middle/enrollment/parsed/_transcripts 下的官方初中转录；
借用 middle/enrollment 的直建 builder 将转录中的「组小学 / 对口小学」规范为实体，
再反向展开为小学→初中候选记录。

输出：
  data/primary/transition/parsed/xiaoshengchu_from_middle_<区>_2026.json
  data/primary/transition/parsed/xiaoshengchu_from_middle_compare_<区>_2026.json

默认仅处理可直接反推的五区：越秀、荔湾、白云、海珠、黄埔。
现有 dist/xiaoshengchu_<区>.json 只读，用于比较，绝不覆盖。
"""
import argparse
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
OUT = os.path.join(ROOT, "data", "primary", "transition", "parsed")
DISTRICTS = ("yuexiu", "liwan", "baiyun", "haizhu", "huangpu")
# 机制枚举输出顺序（对齐初中 MECH_ORDER：zhi_sheng → single_zone → group_paidui → single_paidui → min_zi_zhu）
XS_MECH_ORDER = ("zhi_sheng", "single_zone", "group_paidui", "single_paidui", "min_zi_zhu")

# 反推候选 → 小升初 dist records 的 group 显示名（按机制生成，含区名——
# xs_resolver.district_of_group 从 group 提取区名做跨区过滤，必须保留「XX区」前缀）。
# 反推链路不携带小升初侧「第N组」粒度（组号在初中 mechanism_note/group_id），
# 组粒度展示由机制枚举承载（前端 Badge 用 mechanisms，group 仅作 sub-note 文本）。
_GROUP_OF_MECH = {
    "zhi_sheng": "{区}小升初对口直升（不参加电脑派位）",
    "single_zone": "{区}小升初对口（单校划片）",
    "group_paidui": "{区}小升初对口（多校电脑派位）",
    "single_paidui": "{区}小升初电脑派位",
    "min_zi_zhu": "{区}小升初自主招生",
}


def to_dist_records(candidate):
    """反推候选 records → 小升初 dist records（保持 dist 契约字段）：
    name/group/mechanisms/feed_junior_highs/direct_feed(字符串)/source_url/data_gaps；
    source_note 属审计层，dist 剥离（与 build_xiaoshengchu_all.dump 同口径）。
    2026-09-30：五区小升初数据源切换为初中转录反推（用户指示），dist 五区由此转换产出。"""
    dk = candidate["district"]
    out = []
    for r in candidate["records"]:
        mech = r.get("mechanisms") or []
        # 2026-10-04（修复2）：混合机制（如海珠「对口直升 + 电脑派位」）组名不再取 mech[0]——
        # 含 group_paidui 时组名取派位模板（与前端「多校电脑派位」徽章一致，避免
        # 「多校电脑派位」徽章下挂着「不参加电脑派位」组名的自相矛盾）；
        # 纯直升/单校划片等单机制场景保持 mech[0] 模板；兜底文案不变。
        if "group_paidui" in mech:
            group = _GROUP_OF_MECH["group_paidui"].format(区=dk)
        elif mech:
            group = _GROUP_OF_MECH.get(mech[0], "{区}不参与公办派位/待核").format(区=dk)
        else:
            group = "{区}不参与公办派位/待核".format(区=dk)
        direct = r.get("direct_feed") or []
        out.append({
            "name": r["name"],
            "group": group,
            "mechanisms": mech,
            "feed_junior_highs": r["feed_junior_highs"],
            "direct_feed": direct[0] if direct else None,
            "source_url": r.get("source_url"),
            "source_note": r.get("source_note"),  # 审计层字段，dist 写入时剥离
            "data_gaps": r.get("data_gaps"),
        })
    out.sort(key=lambda r: r["name"])
    return out

sys.path.insert(0, os.path.join(ROOT, "data", "primary", "transition", "scripts"))
from xs_resolver import XsResolver  # noqa: E402


def load_middle_builder():
    path = os.path.join(ROOT, "data", "middle", "enrollment", "scripts", "build_middle_enrollment.py")
    spec = importlib.util.spec_from_file_location("middle_enrollment_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_entities():
    rows = json.load(open(os.path.join(ROOT, "data", "registry", "entity", "dist", "entities.json"), encoding="utf-8"))["entities"]
    return {r["school_id"]: r["name"] for r in rows}


def middle_ids(record):
    return ([record["school_id"]] if record.get("school_id") else []) + list(record.get("school_ids") or [])


def primary_ids(record, district):
    """直建中间记录携带两种官方小学来源：派位组或单校对口范围。"""
    if record.get("_group_primaries"):
        # build_middle_enrollment._primary_ids 直接基于官方小学名和实体表解析。
        return [(name, sid) for name in record["_group_primaries"]
                for sid in MIDDLE._primary_ids(name, MIDDLE._DK_ADCODE[district])]
    return [(name, sid) for name, ids in (record.get("scope_school_ids") or {}).items() for sid in ids]


def campus_assign(record, mids, entity_names):
    """多校区聚合记录：scope 原文分行「XX校区：小学、…」→ {校区实体id: [行内小学名]}。

    2026-09-30（修复1）：官方中学「一名多校区」聚合记录（如「广州市第六十五中学（明德校区、
    同德校区）」一行、feed 分行「明德校区：…」/「同德校区：…」）——每所小学只对口其所在
    校区，不得全组合挂到全部校区。行标签↔校区实体按「实体名包含标签」匹配（不依赖 school_ids
    顺序）；解析不出标签的行不归属（调用方兜底全组合，不丢数据）。
    """
    scope = record.get("scope") or ""
    out = {}
    # 法人主体实体（实体名无校区标识，如「广州市白云区竹料第一中学」）：官方「南校区：…」
    # 分行中「南校区/本部/校本部/总校区」等主体语义标签即指该法人实体（无独立南校区实体），
    # 标签匹配不到任何校区实体名时兜底归属法人主体（65中 两校区实体均带校区标识 → 不受影响）。
    _CAMPUS_IDENT = ("校区", "分校", "教学点", "分教点", "分部", "本部")
    legal_mids = [m for m in mids
                  if not any(k in (entity_names.get(m) or "") for k in _CAMPUS_IDENT)]
    for ln in [x.strip() for x in scope.split("\n") if x.strip()]:
        m = re.match(r"^(.+?)[：:](.+)$", ln)
        if not m:
            continue
        tag, rest = m.group(1).strip(), m.group(2).strip()
        if "校区" not in tag:
            continue
        names = [s.strip() for s in MIDDLE._SCOPE_SPLIT.split(rest) if s.strip()]
        hit = None
        for mid in mids:
            nm = (entity_names.get(mid) or "").replace("（", "").replace("）", "").replace("(", "").replace(")", "")
            if tag in nm:
                hit = mid
                break
        if not hit and tag in ("南校区", "本部", "校本部", "总校区", "主校区", "正校") and legal_mids:
            hit = legal_mids[0]
        if hit:
            out.setdefault(hit, []).extend(names)
    return out


def _same_school(a, b):
    """行内小学名（清洗后）与 scope_school_ids 键比较：剥括号后全等，或双向包含兜底。"""
    na = a.replace("（", "(").replace("）", ")").replace("(", "").replace(")", "")
    nb = b.replace("（", "(").replace("）", ")").replace("(", "").replace(")", "")
    return na == nb or na in nb or nb in na


def reverse_district(district, entity_names):
    # 2026-09-30：与 middle/enrollment 主流程一致，先应用 src/inferred_feed_schools.json
    # 推断回填（协和学校小学部直升、黄埔军校纪念中学北校区等官方未逐校列名场景），
    # 否则反推链拿到的 scope_school_ids 缺这些手工标注生源小学。
    source = MIDDLE.apply_inferred_feeds(MIDDLE.BUILDERS[district]())
    by_primary = {}
    unresolved_primary_names = set()
    for r in source["records"]:
        mids = middle_ids(r)
        primaries = primary_ids(r, district)
        if not mids:
            continue
        if r.get("_group_primaries") and not primaries:
            unresolved_primary_names.update(r["_group_primaries"])
        # 修复1（2026-09-30）：多校区聚合记录（如 65中明德+同德）按 scope 分行标签
        # 「XX校区：小学、…」归属各校区实体；行内小学名清洗后与 scope_school_ids 键
        # 比较（行名可能是「65附小分校区（地段生）」→ 键「65附小分校区」）。单校区
        # 记录/无标签行兜底全组合（不丢数据）。
        campus_map = campus_assign(r, mids, entity_names) if len(mids) > 1 else {}
        for official_primary, primary_id in primaries:
            row = by_primary.setdefault(primary_id, {
                "name": entity_names.get(primary_id, official_primary),
                "school_id": primary_id,
                "official_primary_names": [],
                "mechanisms": [],
                "feed_junior_highs": [],
                "feed_school_ids_from_middle": [],
                "direct_feed": [],
                "source_url": source.get("source_url"),
                "source_note": source.get("source"),
                "data_gaps": None,
            })
            if official_primary not in row["official_primary_names"]:
                row["official_primary_names"].append(official_primary)
            # 机制直接取自初中转录 mechanism 枚举（与初中枚举对齐，raw 同源）；
            # 不再取 mechanism_note（那是备注文本，不是机制）。
            if r.get("mechanism") not in row["mechanisms"]:
                row["mechanisms"].append(r["mechanism"])
            # 2026-10-04（修复2）：直升判定补齐 zhi_sheng 机制——此前仅认 single_zone，
            # 海珠/越秀等区 zhi_sheng 直升初中（如五中附属初级中学）被漏判、混入派位 feed、
            # direct_feed 全空（昌岗中路小学页「直升 + 电脑派位」矛盾根因）。
            is_direct = district in {"yuexiu", "haizhu", "huangpu"} and r.get("mechanism") in ("single_zone", "zhi_sheng")
            if campus_map:
                effective = [mid for mid, names in campus_map.items()
                             if any(_same_school(nm, official_primary) for nm in names)]
                mids_for_pair = effective or mids  # 无标签归属行兜底全组合
            else:
                mids_for_pair = mids
            for mid in mids_for_pair:
                mid_name = entity_names.get(mid, r.get("school") or mid)
                # 直升初中只进 direct_feed，不进派位 feed（feed 保持纯派位组列表）
                if is_direct:
                    if mid_name not in row["direct_feed"]:
                        row["direct_feed"].append(mid_name)
                else:
                    if mid_name not in row["feed_junior_highs"]:
                        row["feed_junior_highs"].append(mid_name)
                    if mid not in row["feed_school_ids_from_middle"]:
                        row["feed_school_ids_from_middle"].append(mid)
    records = sorted(by_primary.values(), key=lambda r: (r["name"], r["school_id"]))
    for r in records:
        r["mechanisms"] = [m for m in XS_MECH_ORDER if m in r["mechanisms"]]
    return {
        "year": 2026,
        "district": source["district"],
        "kind": "candidate_from_middle_enrollment_transcripts",
        "source": source.get("source"),
        "source_url": source.get("source_url"),
        "records": records,
        "unresolved_official_primary_names": sorted(unresolved_primary_names),
    }


def pairs_from_reverse(candidate):
    return {(r["school_id"], mid)
            for r in candidate["records"] for mid in r["feed_school_ids_from_middle"]}


def pairs_from_current(district):
    # 2026-09-30 数据源切换后：dist 五区 = 反推转换版，线上对账基线固定为切换前存档
    # （parsed/xiaoshengchu_<区>_legacy_2026.json，git 跟踪、不可变），持续对账「反推 vs 旧线上」；
    # 缺档时（如新克隆未含 legacy）回退读 dist 当前文件。
    legacy = os.path.join(ROOT, "data", "primary", "transition", "parsed",
                          f"xiaoshengchu_{district}_legacy_2026.json")
    path = legacy if os.path.exists(legacy) else os.path.join(
        ROOT, "data", "primary", "transition", "dist", f"xiaoshengchu_{district}.json")
    rows = json.load(open(path, encoding="utf-8"))["records"]
    resolver = XsResolver()
    resolved = [resolver.resolve_record(row) for row in rows]
    return {(r["school_id"], mid)
            for r in resolved if r.get("school_id")
            for mid in r.get("feed_school_ids") or []}


def comparison(district, candidate, entity_names):
    reverse = pairs_from_reverse(candidate)
    current = pairs_from_current(district)

    def render(pairs):
        return [{"primary_school_id": p, "primary": entity_names.get(p, p),
                 "middle_school_id": m, "middle": entity_names.get(m, m)}
                for p, m in sorted(pairs, key=lambda x: (entity_names.get(x[0], x[0]), entity_names.get(x[1], x[1])))]
    return {
        "year": 2026,
        "district": candidate["district"],
        "basis": "official middle-enrollment transcripts vs existing xiaoshengchu district dist; entity IDs are compared after each chain's current resolver.",
        "summary": {
            "reverse_pairs": len(reverse), "current_pairs": len(current),
            "only_reverse": len(reverse - current), "only_current": len(current - reverse),
            "equal": reverse == current,
        },
        "only_reverse": render(reverse - current),
        "only_current": render(current - reverse),
    }


def dump(path, data):
    # 产物确定性排序（2026-09-29）：records 按 school_id 稳定排序 + sort_keys 统一键序
    # （compare_* 对账产物无 records 键，仅统一键序）
    if "records" in data:
        data["records"].sort(key=lambda r: (r.get("school_id") or "", r.get("name") or ""))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("district", nargs="*", metavar="district")
    parser.add_argument("--out-dir", default=OUT)
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    entity_names = load_entities()
    targets = args.district or DISTRICTS
    invalid = sorted(set(targets) - set(DISTRICTS))
    if invalid:
        parser.error(f"仅支持：{', '.join(DISTRICTS)}；收到：{', '.join(invalid)}")
    dist_dir = os.path.join(ROOT, "data", "primary", "transition", "dist")
    for district in targets:
        candidate = reverse_district(district, entity_names)
        report = comparison(district, candidate, entity_names)
        base = os.path.join(args.out_dir, f"xiaoshengchu_from_middle_{district}_2026.json")
        diff = os.path.join(args.out_dir, f"xiaoshengchu_from_middle_compare_{district}_2026.json")
        dump(base, candidate)
        dump(diff, report)
        # 2026-09-30（用户指示）：五区小升初数据源切换为初中转录反推——dist 运行时层与
        # parsed 审计层（xiaoshengchu_<区>_2026.json）均由反推候选转换产出，
        # build_xiaoshengchu_all.py 不再构建五区（仅 panyu/tianhe + 汇总）。
        dist_path = os.path.join(args.out_dir if args.out_dir != OUT else dist_dir,
                                 f"xiaoshengchu_{district}.json")
        audit_path = os.path.join(args.out_dir, f"xiaoshengchu_{district}_2026.json")
        os.makedirs(os.path.dirname(dist_path), exist_ok=True)
        dist_records = to_dist_records(candidate)
        # 2026-09-30：反推仅覆盖官方初中转录出现的生源小学；无对口公办初中的
        # 民办/特教/新开学校（切换前 legacy 的 data_gaps 兜底记录）并入 dist，
        # 避免这些公办小学变孤儿（data_quality 孤儿清单 +14 处漂移触发）。
        # 仅并「无 feed 且有 data_gaps 说明」的记录；反推已覆盖的同名小学不重复。
        legacy_path = os.path.join(ROOT, "data", "primary", "transition", "parsed",
                                   f"xiaoshengchu_{district}_legacy_2026.json")
        if os.path.exists(legacy_path):
            have = {r["name"] for r in dist_records}
            for r in json.load(open(legacy_path, encoding="utf-8"))["records"]:
                if (r.get("feed_junior_highs") or []) or not r.get("data_gaps"):
                    continue
                if r["name"] in have:
                    continue
                dist_records.append({
                    "name": r["name"],
                    "group": r.get("group") or f"{candidate['district']}不参与公办派位/待核",
                    "mechanisms": [],
                    "feed_junior_highs": [],
                    "direct_feed": None,
                    "source_url": r.get("source_url"),
                    "source_note": r.get("source_note"),
                    "data_gaps": r.get("data_gaps"),
                })
            dist_records.sort(key=lambda r: r["name"])
        runtime = [{k: v for k, v in r.items() if k != "source_note"} for r in dist_records]
        json.dump({"year": 2026, "district": candidate["district"], "records": runtime},
                  open(dist_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
        json.dump({"year": 2026, "district": candidate["district"], "records": dist_records},
                  open(audit_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
        s = report["summary"]
        print(f"{district}: reverse {s['reverse_pairs']} / current {s['current_pairs']}; "
              f"only reverse {s['only_reverse']}, only current {s['only_current']} -> {base}")
        print(f"  dist {len(dist_records)} 条 -> {dist_path}（五区 dist 由反推产出）")


if __name__ == "__main__":
    MIDDLE = load_middle_builder()
    main()
