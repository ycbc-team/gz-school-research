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
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
OUT = os.path.join(ROOT, "data", "primary", "transition", "parsed")
DISTRICTS = ("yuexiu", "liwan", "baiyun", "haizhu", "huangpu")
# 机制枚举输出顺序（对齐初中 MECH_ORDER：zhi_sheng → single_zone → group_paidui → single_paidui → min_zi_zhu）
XS_MECH_ORDER = ("zhi_sheng", "single_zone", "group_paidui", "single_paidui", "min_zi_zhu")

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
            is_direct = district in {"yuexiu", "haizhu", "huangpu"} and r.get("mechanism") == "single_zone"
            for mid in mids:
                mid_name = entity_names.get(mid, r.get("school") or mid)
                if mid_name not in row["feed_junior_highs"]:
                    row["feed_junior_highs"].append(mid_name)
                if mid not in row["feed_school_ids_from_middle"]:
                    row["feed_school_ids_from_middle"].append(mid)
                if is_direct and mid_name not in row["direct_feed"]:
                    row["direct_feed"].append(mid_name)
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
    path = os.path.join(ROOT, "data", "primary", "transition", "dist", f"xiaoshengchu_{district}.json")
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
    for district in targets:
        candidate = reverse_district(district, entity_names)
        report = comparison(district, candidate, entity_names)
        base = os.path.join(args.out_dir, f"xiaoshengchu_from_middle_{district}_2026.json")
        diff = os.path.join(args.out_dir, f"xiaoshengchu_from_middle_compare_{district}_2026.json")
        dump(base, candidate)
        dump(diff, report)
        s = report["summary"]
        print(f"{district}: reverse {s['reverse_pairs']} / current {s['current_pairs']}; "
              f"only reverse {s['only_reverse']}, only current {s['only_current']} -> {base}")


if __name__ == "__main__":
    MIDDLE = load_middle_builder()
    main()
