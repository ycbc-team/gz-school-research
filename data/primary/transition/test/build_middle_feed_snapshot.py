#!/usr/bin/env python3
"""生成「全部初中 → 生源小学」快照基线（data/primary/middle_feed_snapshot.json）。

快照 = 详情页招生计划「生源小学」区块的运行时视图（@gz/shared quota.ts middlePrimaryFeed 的
Python 复刻：xiaoshengchu 事实表反查 + entities 小学名校名解析），逐初中 POI 固化，
供 check_middle_feed_snapshot.py 做全量变化感知——任何小学名单变更（新增/移除/消失）
都会在 npm run check 时被检出，避免「某校区小学名单不见了」静默发生（南武岭南画派教训）。

用法：python3 scripts/build_middle_feed_snapshot.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def main():
    xs = load("data/primary/transition/dist/xiaoshengchu_2026.json")
    entities = load("data/registry/entity/dist/entities.json")
    middle = load("data/poi/dist/middle_poi.json")

    entity_by_id = {e["school_id"]: e["name"] for e in entities["entities"]}
    group_by_id = {g["id"]: g["name"] for g in xs["groups"]}

    # 与 @gz/shared quota.ts middlePrimaryFeed 同逻辑：records 顺序遍历，
    # feed_school_ids 含目标 或 direct_feed_school_id == 目标 → 该记录的小学
    feeds: dict[str, list[dict]] = {}
    for r in xs["records"]:
        mid = r.get("direct_feed_school_id")
        feed_ids = r.get("feed_school_ids") or []
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

    snapshot = {
        "note": "全部初中 POI → 生源小学（详情页招生计划视图基线；由 build_middle_feed_snapshot.py 生成，勿手改）",
        "schools": {p["school_id"]: feeds.get(p["school_id"], []) for p in middle["schools"] if p.get("school_id")},
    }
    out = os.path.join(ROOT, "data/primary/transition/test/snapshots/middle_feed_snapshot.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, sort_keys=True)
    n = sum(1 for v in snapshot["schools"].values() if v)
    print(f"[快照] 初中 POI {len(snapshot['schools'])} 个（有生源小学 {n} 个）→ {out}")


if __name__ == "__main__":
    main()
