#!/usr/bin/env python3
"""实体表/POI 关联业务快照测试（2026-09-21 由 special_matrix 快照模式推广）。

替代字节全等"重跑 vs 入库"（入库被 bug 污染时自我一致通过）；快照锁定实体
核心业务信息（school_id → name/stage/aliases + POI school_id → 名称集合），
重跑 build_entities 后与独立基线全等对比：

- 全等 → 通过：实体/别名/POI 关联未发生意外变化
- 有差异 → 失败并逐条列出（旧 → 新）：别名增删 / 实体名改 / POI 关联漂移显式暴露

基线独立于产物，改动须显式 --update-snapshot（数据变更=正常迭代，先看 diff
确认是有意变更还是回归，禁止改产物掩盖）。坐标/时间戳等噪音字段不入快照。

用法：
  python3 data/registry/entity/scripts/check_entities_snapshot.py                    # 对比
  python3 data/registry/entity/scripts/check_entities_snapshot.py --update-snapshot  # 更新基线
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
SNAPSHOT = os.path.join(ROOT, "data/registry/entity/test/snapshots/entities_snapshot.json")
BUILD = os.path.join(ROOT, "data/registry/entity/scripts/build_entities.py")
TMP = os.path.join(__import__("tempfile").gettempdir(), "entities_snapshot_repro")
POI_STAGES = ("primary", "middle", "high")


def extract() -> dict:
    """重跑 build_entities --out-dir → 实体核心 + POI school_id 关联。"""
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    r = subprocess.run(["python3", BUILD, "--out-dir", TMP], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print("生产脚本重跑失败：build_entities.py")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(1)
    ents = json.load(open(os.path.join(TMP, "data/registry/entity/dist/entities.json"),
                          encoding="utf-8"))["entities"]
    # key 用 school_id#stage：一贯制学校同 id 双 stage 实体（小学部/初中部）是不同实体，
    # 仅按 school_id 会互相覆盖（曾致 1554 实体快照只剩 1363）
    entities = {}
    for e in ents:
        entities[f"{e['school_id']}#{e.get('stage')}"] = {
            "name": e["name"],
            "stage": e.get("stage"),
            "aliases": sorted(e.get("aliases") or []),
        }
    poi = {}
    for st in POI_STAGES:
        p = os.path.join(TMP, "data/poi/dist", f"{st}_poi.json")
        j = json.load(open(p, encoding="utf-8"))
        m = {}
        for s in (j.get("schools") if isinstance(j, dict) else j):
            sid = s.get("school_id")
            if sid:
                m.setdefault(sid, set()).add(s.get("name") or "")
        poi[st] = {k: sorted(v) for k, v in m.items()}
    return {"entity_count": len(entities), "entities": entities, "poi": poi}


def diff_dict(old: dict, new: dict, path: str, limit: int = 40) -> list:
    out = []
    for k in sorted(set(old) | set(new), key=str):
        if old.get(k) != new.get(k):
            out.append(f"    {path}.{k}: {json.dumps(old.get(k), ensure_ascii=False)[:80]!r} → "
                       f"{json.dumps(new.get(k), ensure_ascii=False)[:80]!r}")
            if len(out) >= limit:
                out.append(f"    …（仅显示前 {limit} 条，共差异多于此）")
                break
    return out


def run(update: bool) -> int:
    new = extract()
    if update:
        json.dump({**new, "note": "实体/POI 关联业务快照（非产物字节，坐标不入快照）。更新：--update-snapshot。",
                   "updated": "2026-09-21"}, open(SNAPSHOT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        print(f"✓ 基线已更新：{os.path.relpath(SNAPSHOT, ROOT)}（{new['entity_count']} 实体 + 3 表 POI 关联）")
        return 0
    if not os.path.exists(SNAPSHOT):
        print(f"基线不存在：{SNAPSHOT}。首次运行请先 --update-snapshot 固化当前正确产物。")
        return 1
    base = json.load(open(SNAPSHOT, encoding="utf-8"))
    diffs = []
    if base.get("entity_count") != new.get("entity_count"):
        diffs.append(f"    entity_count: {base.get('entity_count')} → {new.get('entity_count')}")
    diffs += diff_dict(base.get("entities", {}), new.get("entities", {}), "entities")
    for st in POI_STAGES:
        diffs += diff_dict(base.get("poi", {}).get(st, {}), new.get("poi", {}).get(st, {}), f"poi.{st}")
    if diffs:
        print("业务快照: ✗ 实体/POI 关联与基线不一致（实体/别名/关联变更或回归）：")
        print("\n".join(diffs[:40]))
        print("  → 先逐条确认是有意变更（源表更新/别名瘦身）还是回归；确认后显式更新基线：")
        print("     python3 data/registry/entity/scripts/check_entities_snapshot.py --update-snapshot")
        print("  禁止直接改基线或产物掩盖 diff。")
        return 1
    print(f"业务快照: ✓ 实体/POI 关联与基线全等（{new['entity_count']} 实体 + 3 表 POI，独立基线）")
    return 0


if __name__ == "__main__":
    sys.exit(run("--update-snapshot" in sys.argv))
