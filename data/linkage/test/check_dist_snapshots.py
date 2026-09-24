#!/usr/bin/env python3
"""升学通道 canonical 业务快照测试 + dist 轻量结构断言（quota_matrix / district_quota /
batch2_scores / ranking_middle；special_matrix 由 check_special_matrix_snapshot.py 覆盖）。

用户口径（2026-09-24 拍板）：
  1) 测试快照只用 canonical（既有 school_id 又有 name 的规范表），不再维护 dist 精简快照；
  2) dist 运行时产物只保留有前端引用的最精简字段，其余调试字段只进 canonical（由快照覆盖）；
  3) dist 以轻量结构断言校验（ids/schools 并行结构、行数守恒、字段白名单、无调试字段泄漏）。

原理（与旧版同思想）：重跑完整生产链路（B 层清洗 → C 层 SchoolMatcher/裁剪/聚合），
提取每个 canonical 产物的"业务快照"，与固化基线 test/snapshots/canon_*.json 全等对比：
  - 全等 → 通过：canonical 可由脚本完全重建，未发生意外变化
  - 有差异 → 失败并逐条列出：官方源更新 / 解析修复 / 匹配回归都会显式暴露
基线独立于产物，改动必须显式更新（--update-snapshot）。

覆盖链路（顺序即生产管线）：
  B 层（parsed/canonical/）：rebuild_quota_matrix → build_district_quota →
      build_linkage_batch2 → build_special_matrix
  C 层：backfill_school_ids（canonical 写回 school_id/middle_school_ids + dist ids/schools
      拆分）→ optimize_redundancy → build_ranking_middle（canonical 全量 + dist 精简）

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
CANON = os.path.join(ROOT, "data/linkage/parsed/canonical")
SNAP_DIR = os.path.join(ROOT, "data/linkage/test/snapshots")


def replay(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(f"生产脚本重跑失败：{cmd}")
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        sys.exit(1)


# ---------------- canonical 业务快照抽取 ----------------
def extract_quota(m):
    """quota_matrix：每校业务字段 + sz 高中明细 + school_id/school_ids 外键（既有 id 又有 name）。"""
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
    ("quota_matrix", "canon_quota_matrix_snapshot.json", extract_quota, CANON),
    ("district_quota", "canon_district_quota_snapshot.json", extract_district, CANON),
    ("batch2_scores", "canon_batch2_scores_snapshot.json", extract_batch2, CANON),
    ("ranking_middle", "canon_ranking_middle_snapshot.json", extract_ranking, CANON),
    # special_matrix 的 canonical 业务快照由 check_special_matrix_snapshot.py 单独覆盖
    # （重放 B 层 build_special_plan/build_special_matrix，基线 special_matrix_snapshot.json）
]


# ---------------- dist 轻量结构断言（无基线，硬编码约束） ----------------
def assert_dist_structure() -> list:
    """dist 运行时产物结构/字段白名单断言。返回错误清单（空 = 通过）。"""
    errs = []

    # quota_matrix：ids/schools 并行数组 + name_index（官方名单名 → 法人行 school_id）
    q = json.load(open(os.path.join(DIST, "quota_matrix.json"), encoding="utf-8"))
    qc = json.load(open(os.path.join(CANON, "quota_matrix.json"), encoding="utf-8"))
    if set(q) != {"ids", "schools", "name_index"}:
        errs.append("quota_matrix 顶层键必须仅 ids/schools/name_index")
    if not isinstance(q.get("name_index"), dict):
        errs.append("quota_matrix.name_index 必须为对象")
    else:
        id_sids = {r.get("school_id") for r in q.get("ids", [])}
        canon_schools = {s.get("school") for s in qc.get("schools", []) if s.get("school_id")}
        if set(q["name_index"].keys()) != canon_schools:
            errs.append("quota name_index 键必须 = canonical 中有 school_id 的官方名单名全集")
        bad_val = {k for k, v in q["name_index"].items() if v not in id_sids}
        if bad_val:
            errs.append(f"quota name_index 值不在 ids school_id 集合: {sorted(bad_val)[:3]}")
    allowed = {"district", "kaosheng", "sheng_quota", "qu_quota", "sz", "school_id", "school_ids"}
    for r in q.get("ids", []):
        bad = set(r) - allowed
        if bad:
            errs.append(f"quota ids 行含未引用字段: {sorted(bad)}（行 {r.get('school_id')}）")
        if "school" in r:
            errs.append("quota ids 行不得含 school 名（应 join 实体表）")
        if "school_id" not in r:
            errs.append(f"quota ids 行缺 school_id: {r}")
    for r in q.get("schools", []):
        if "school" not in r or "school_id" in r:
            errs.append(f"quota schools 行必须只有 school 原文（无 id）: {r}")
        bad = set(r) - (allowed | {"school"})
        if bad:
            errs.append(f"quota schools 行含未引用字段: {sorted(bad)}")
    if len(q.get("ids", [])) + len(q.get("schools", [])) != len(qc.get("schools", [])):
        errs.append(f"quota ids+schools 行数 {len(q.get('ids', []))}+{len(q.get('schools', []))} ≠ canonical {len(qc.get('schools', []))}")

    # district_quota / batch2_scores：外层/内层递归 ids/schools，值单元格守恒
    for tag in ("district_quota", "batch2_scores"):
        d = json.load(open(os.path.join(DIST, f"{tag}.json"), encoding="utf-8"))
        dc = json.load(open(os.path.join(CANON, f"{tag}.json"), encoding="utf-8"))
        if set(d) != {"ids", "schools"}:
            errs.append(f"{tag} 顶层键必须仅 ids/schools")
        canon_cells = sum(len(v) for v in dc["data"].values())
        dist_cells = 0
        for outer in [*d.get("ids", {}).values(), *d.get("schools", {}).values()]:
            if not isinstance(outer, dict) or set(outer) - {"ids", "schools"}:
                errs.append(f"{tag} 内层结构必须为 {{ids, schools}}")
            dist_cells += len(outer.get("ids", {})) + len(outer.get("schools", {}))
        if dist_cells != canon_cells:
            errs.append(f"{tag} 值单元格 {dist_cells} ≠ canonical {canon_cells}")
        if "middle_school_ids" in d:
            errs.append(f"{tag} 顶层不得含 middle_school_ids（键已 id 化）")

    # ranking_middle：canonical 全量 / dist 删 sz 与元数据
    rk = json.load(open(os.path.join(DIST, "ranking_middle.json"), encoding="utf-8"))
    for k in ("title", "updated", "note", "source"):
        if k in rk:
            errs.append(f"ranking dist 顶层不得含 {k}（调试元数据只进 canonical）")
    for s in rk.get("schools", []):
        if "sz" in s:
            errs.append("ranking dist 行不得含 sz 明细（无前端消费，canonical 快照覆盖）")
    rkc = json.load(open(os.path.join(CANON, "ranking_middle.json"), encoding="utf-8"))
    if len(rk.get("schools", [])) != len(rkc.get("schools", [])):
        errs.append(f"ranking dist 行数 {len(rk.get('schools', []))} ≠ canonical {len(rkc.get('schools', []))}")

    # special_matrix：死字段不得出现；special_plan 值内 name 已删
    sp = json.load(open(os.path.join(DIST, "special_matrix.json"), encoding="utf-8"))
    for k in ("high_entities", "high_schools", "note", "scope", "updated", "title",
              "autonomy_plan_source", "special_plan_source", "special_plan_summary"):
        if k in sp:
            errs.append(f"special dist 不得含 {k}")
    for v in (sp.get("special_plan") or {}).values():
        if "name" in v:
            errs.append("special_plan 值内不得含 name（实体名由实体表 join）")

    return errs


def run(update: bool) -> int:
    print("重放生产链路（B → C）…")
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/rebuild_quota_matrix.py")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/build_district_quota.py")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/build_linkage_batch2.py")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/build_special_matrix.py")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/backfill_school_ids.py")])
    replay(["node", os.path.join(ROOT, "scripts/data/optimize_redundancy.mjs")])
    replay(["python3", os.path.join(ROOT, "data/linkage/scripts/build_ranking_middle.py")])

    os.makedirs(SNAP_DIR, exist_ok=True)
    all_ok = True
    for tag, snap_name, extractor, src_dir in PRODUCTS:
        prod = json.load(open(os.path.join(src_dir, f"{tag}.json"), encoding="utf-8"))
        new = extractor(prod)
        path = os.path.join(SNAP_DIR, snap_name)
        if update:
            json.dump({"note": f"{tag} canonical 业务快照（既有 id 又有 name；canonical 必须由脚本重建）。"
                                 "更新：--update-snapshot。dist 只做轻量结构断言，不再存精简快照。",
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
            print(f"  ✓ {tag} canonical 与基线全等")
        else:
            all_ok = False
            print(f"  ✗ {tag} canonical 与基线不一致（产物漂移或数据变更）——diff 前 {min(25, _count_diff(base, new))} 条：")
            for line in diff(base, new, tag, limit=25):
                print("   " + line)
            print("    → 确认是官方源更新/解析修复（预期变化）后显式更新基线：--update-snapshot；")
            print("      禁止直接改基线或产物掩盖 diff。")

    # dist 结构断言（无基线）
    print("dist 轻量结构断言…")
    dist_errs = assert_dist_structure()
    if dist_errs:
        all_ok = False
        for e in dist_errs:
            print("  ✗ " + e)
    else:
        print("  ✓ quota/district/batch2/ranking/special 结构、行数守恒、字段白名单全部通过")

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
