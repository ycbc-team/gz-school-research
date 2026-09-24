#!/usr/bin/env python3
"""升学通道 dist 四产物——业务信息快照测试（quota_matrix / district_quota / batch2_scores / ranking_middle）。

原理（与 check_special_matrix_snapshot.py 同思想）：重跑完整生产链路（B 层清洗 → C 层
SchoolMatcher/裁剪/聚合），提取每个产物的"业务快照"（数据区 + school_id/middle_school_ids 外键），
与固化基线 test/snapshots/dist_*.json 全等对比：

- 全等 → 通过：产物可由脚本完全重建，未发生意外变化
- 有差异 → 失败并逐条列出（旧 → 新）：官方源更新 / 解析修复 / 匹配回归都会显式暴露

本测试在真实 canonical/dist 上重放（dist 是派生产物，必须能由脚本重建；任何"直接改 dist
未更新脚本"的漂移都会被重放覆盖并以 diff 形式暴露）。产物里 updated 等噪音字段不入快照；
基线独立于产物，改动必须显式更新（--update-snapshot）。

覆盖链路（顺序即生产管线）：
  B 层（parsed/canonical/）：rebuild_quota_matrix → build_district_quota → build_linkage_batch2
  C 层（dist/）：backfill_school_ids → optimize_redundancy → build_ranking_middle
（special_matrix 由 check_special_matrix_snapshot.py 单独覆盖）

用法：
  python3 data/linkage/test/check_dist_snapshots.py                    # 对比（默认）
  python3 data/linkage/test/check_dist_snapshots.py --update-snapshot  # 更新基线
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DIST = os.path.join(ROOT, "data/linkage/dist")
SNAP_DIR = os.path.join(ROOT, "data/linkage/test/snapshots")


def replay(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(f"生产脚本重跑失败：{cmd}")
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        sys.exit(1)


def extract_quota(m):
    """quota_matrix 快照：每校业务字段 + sz 高中明细 + school_id/school_ids 外键。"""
    out = []
    for s in m.get("schools", []):
        out.append({
            "school": s.get("school"),
            "district": s.get("district"),
            "kaosheng": s.get("kaosheng"),
            "sheng_quota": s.get("sheng_quota"),
            "qu_quota": s.get("qu_quota"),
            "sz_sum": s.get("sz_sum"),
            "sz": dict(s.get("sz") or {}),
            "school_id": s.get("school_id"),
            "school_ids": s.get("school_ids"),
        })
    return sorted(out, key=lambda x: (x["district"] or "", x["school"] or ""))


def extract_district(m):
    return {
        "data": {k: dict(v) for k, v in (m.get("data") or {}).items()},
        "middle_school_ids": dict(m.get("middle_school_ids") or {}),
    }


def extract_batch2(m):
    return {
        "data": {k: {kk: dict(vv) for kk, vv in v.items()} for k, v in (m.get("data") or {}).items()},
        "middle_school_ids": dict(m.get("middle_school_ids") or {}),
    }


def extract_ranking(m):
    out = []
    for s in m.get("schools", []):
        out.append({
            "name": s.get("name"),
            "school_id": s.get("school_id"),
            "school_ids": s.get("school_ids"),
            "district": s.get("district"),
            "minban": s.get("minban"),
            "group": s.get("group"),
            "kaosheng": s.get("kaosheng"),
            "sheng_quota": s.get("sheng_quota"),
            "qu_quota": s.get("qu_quota"),
            "autonomy_count": s.get("autonomy_count"),
            "sz": s.get("sz"),
            "tekong_quota_rate": s.get("tekong_quota_rate"),
        })
    return sorted(out, key=lambda x: (x["district"] or "", x["name"] or ""))


PRODUCTS = [
    ("quota_matrix", "dist_quota_matrix_snapshot.json", extract_quota),
    ("district_quota", "dist_district_quota_snapshot.json", extract_district),
    ("batch2_scores", "dist_batch2_scores_snapshot.json", extract_batch2),
    ("ranking_middle", "dist_ranking_middle_snapshot.json", extract_ranking),
]


def run(update: bool) -> int:
    print("重放生产链路（B → C）…")
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/rebuild_quota_matrix.py")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/build_district_quota.py")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/build_linkage_batch2.py")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/backfill_school_ids.py")])
    replay(["node", os.path.join(ROOT, "scripts/data/optimize_redundancy.mjs")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/build_ranking_middle.py")])

    os.makedirs(SNAP_DIR, exist_ok=True)
    all_ok = True
    for tag, snap_name, extractor in PRODUCTS:
        prod = json.load(open(os.path.join(DIST, f"{tag}.json"), encoding="utf-8"))
        new = extractor(prod)
        path = os.path.join(SNAP_DIR, snap_name)
        if update:
            json.dump({"note": f"{tag} 业务快照（非产物字节，dist 必须由脚本重建）。更新：--update-snapshot。",
                       "updated": "2026-09-24", "snapshot": new},
                      open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
            print(f"  ✓ 基线已更新：{snap_name}")
            continue
        if not os.path.exists(path):
            print(f"  ✗ 基线不存在：{snap_name}。首次运行请先 --update-snapshot。")
            all_ok = False
            continue
        base = json.load(open(path, encoding="utf-8"))["snapshot"]
        if base == new:
            print(f"  ✓ {tag} 与基线全等")
        else:
            all_ok = False
            print(f"  ✗ {tag} 与基线不一致（产物漂移或数据变更）——diff 前 {min(25, _count_diff(base, new))} 条：")
            for line in diff(base, new, tag, limit=25):
                print("   " + line)
            print("    → 确认是官方源更新/解析修复（预期变化）后显式更新基线：--update-snapshot；")
            print("      禁止直接改基线或产物掩盖 diff。")

    if update:
        print("基线已更新完毕。")
        return 0
    return 0 if all_ok else 1


def _count_diff(a, b):
    n = [0]

    def walk(x, y):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                if k in x and k in y:
                    walk(x[k], y[k])
                else:
                    n[0] += 1
        elif isinstance(x, list) and isinstance(y, list):
            for i in range(min(len(x), len(y))):
                walk(x[i], y[i])
            n[0] += abs(len(x) - len(y))
        elif x != y:
            n[0] += 1
    walk(a, b)
    return n[0]


def diff(old, new, tag, limit=40):
    """列表化 diff（按行输出，便于人工审查；仅列差异路径与旧→新值）"""
    lines = []

    def walk(x, y, path):
        if len(lines) >= limit:
            return
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y), key=str):
                if k in x and k in y:
                    walk(x[k], y[k], f"{path}.{k}")
                else:
                    lines.append(f"{path}.{k}: {'<缺失>' if k not in y else '<新增>'} "
                                 f"旧={x.get(k)!r} 新={y.get(k)!r}")
        elif isinstance(x, list) and isinstance(y, list):
            for i in range(max(len(x), len(y))):
                if i >= len(x) or i >= len(y):
                    lines.append(f"{path}[{i}]: {'<缺失>' if i >= len(y) else '<新增>'}")
                else:
                    walk(x[i], y[i], f"{path}[{i}]")
        elif x != y:
            lines.append(f"{path}: 旧={x!r} 新={y!r}")

    walk(old, new, tag)
    return lines[:limit]


if __name__ == "__main__":
    sys.exit(run("--update-snapshot" in sys.argv))
