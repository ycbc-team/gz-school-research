#!/usr/bin/env python3
"""全量初中生源小学快照对比（npm run check 链）。

重算 data/primary/middle_feed_snapshot.json 的运行时视图（同 build_middle_feed_snapshot.py），
与入库基线逐初中 diff。任何小学名单变更（新增/移除/消失）都会报错并列出差异，
避免「某初中详情页生源小学名单不见了」静默发生（南武岭南画派教训）。

数据变更后需同步更新基线：python3 scripts/build_middle_feed_snapshot.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(ROOT, "data/primary/middle_feed_snapshot.json")

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("build_middle_feed_snapshot",
                                              os.path.join(ROOT, "scripts/build_middle_feed_snapshot.py"))
build_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_mod)


def recompute():
    xs = build_mod.load("data/primary/xiaoshengchu_2026.json")
    entities = build_mod.load("data/registry/entities.json")
    middle = build_mod.load("data/poi/dist/middle_poi.json")
    entity_by_id = {e["school_id"]: e["name"] for e in entities["entities"]}
    group_by_id = {g["id"]: g["name"] for g in xs["groups"]}
    feeds = {}
    for r in xs["records"]:
        feed_ids = r.get("feed_school_ids") or []
        mid = r.get("direct_feed_school_id")
        if not feed_ids and not mid:
            continue
        primary_name = entity_by_id.get(r.get("school_id"), "(未知)")
        group_name = group_by_id.get(r.get("group_id"))
        for sid in feed_ids:
            feeds.setdefault(sid, []).append({
                "primary": primary_name,
                "group": group_name,
                "direct_feed": None,
            })
        if mid:
            feeds.setdefault(mid, []).append({
                "primary": primary_name,
                "group": group_name,
                "direct_feed": entity_by_id.get(mid, "(未知)"),
            })
    return {p["school_id"]: feeds.get(p["school_id"], []) for p in middle["schools"] if p.get("school_id")}


def main():
    if not os.path.exists(SNAPSHOT):
        print(f"初中生源小学快照: ✗ 基线缺失 {SNAPSHOT}（先运行 python3 scripts/build_middle_feed_snapshot.py）")
        sys.exit(1)
    base = json.load(open(SNAPSHOT, encoding="utf-8"))["schools"]
    cur = recompute()
    if base.keys() != cur.keys():
        missing = sorted(set(base) - set(cur))
        extra = sorted(set(cur) - set(base))
        print(f"初中生源小学快照: ✗ 初中 POI 集合变化（缺失 {len(missing)}，新增 {len(extra)}）")
        if missing:
            print("  移除:", missing[:10])
        if extra:
            print("  新增:", extra[:10])
        sys.exit(1)
    changed = []
    for sid in cur:
        if base[sid] != cur[sid]:
            changed.append(sid)
    if changed:
        print(f"初中生源小学快照: ✗ {len(changed)} 个初中生源小学变化（列表见下；")
        print("  合法变更请重跑 python3 scripts/build_middle_feed_snapshot.py 更新基线）")
        for sid in changed[:10]:
            b = base[sid]
            c = cur[sid]
            print(f"  {sid} 基线{len(b)}条 → 现{len(c)}条")
            for row in b:
                if row not in c:
                    print(f"    - {row['primary']} ({row['group']})")
            for row in c:
                if row not in b:
                    print(f"    + {row['primary']} ({row['group']})")
        sys.exit(1)
    total = sum(1 for v in cur.values() if v)
    print(f"初中生源小学快照: ✓ {len(cur)} 个初中 POI 与基线一致（有生源小学 {total} 个）")


if __name__ == "__main__":
    main()
