#!/usr/bin/env python3
"""特长生/自招计划矩阵——业务信息快照测试（替代字节全等"重跑 vs 入库"）。

原理（2026-09-21 用户拍板）：字节全等"重跑 vs 入库"在入库被 bug 污染时会自我一致地
通过（白云艺术中学 matchNorm 化后变 null 即现场证据）。改为把"当前正确的业务信息"
固化为独立测试基线 data/linkage/test/snapshots/special_matrix_snapshot.json，重跑生产链路后提取
同一业务快照，与基线全等对比：

- 全等 → 通过：业务信息未发生意外变化
- 有差异 → 失败并逐条列出（旧 → 新）：官方源更新 / 解析修复 / 匹配回归都会显式暴露

对比的是业务信息（名单原文→实体 school_id / 计划数 / 项目清单），不是产物字节——
产物里 updated 时间戳等噪音字段不影响判断；基线独立于产物，改动必须显式更新
（--update-snapshot），禁止直接改基线/产物掩盖 diff（数据变更是正常迭代，
先看 diff 确认是官方更新还是回归，再更新基线）。

用法：
  python3 data/linkage/test/check_special_matrix_snapshot.py                    # 对比（默认）
  python3 data/linkage/test/check_special_matrix_snapshot.py --update-snapshot  # 更新基线
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # data/linkage/test → ROOT
SNAPSHOT = os.path.join(ROOT, "data/linkage/test/snapshots/special_matrix_snapshot.json")
PROD = os.path.join(ROOT, "data/linkage/dist/special_matrix.json")
TMP = os.path.join(__import__("tempfile").gettempdir(), "special_matrix_repro.json")
PLAN_TMP = os.path.join(__import__("tempfile").gettempdir(), "plan_special_repro.json")


def replay(script, *args):
    r = subprocess.run(["python3", os.path.join(ROOT, script), *args],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(f"生产脚本重跑失败：{script}")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(1)


def extract(matrix: dict) -> dict:
    """产物 → 业务信息快照（只留"值得监控的变化"：映射、计划数、项目清单）。"""
    sp = {}
    for sid, v in matrix.get("special_plan", {}).items():
        sp[sid] = {
            "name": v.get("name"),
            "sports": v.get("sports"),
            "arts": v.get("arts"),
            "sports_projects": [p.get("project") for p in v.get("sports_projects") or []],
            "arts_projects": [p.get("project") for p in v.get("arts_projects") or []],
        }
    return {
        "high_school_ids": dict(matrix.get("high_school_ids", {})),       # 名单原文 → 实体（null=未收录，合法）
        "special_plan_summary": dict(matrix.get("special_plan_summary", {})),  # sports/arts/领军龙 总量
        "special_plan": sp,                                                # 校区 → 计划数 + 项目清单
        "autonomy_plan": dict(matrix.get("autonomy_plan", {})),            # 自招计划数
    }


def diff_dict(old: dict, new: dict, path: str, limit: int = 40) -> list:
    out = []
    for k in sorted(set(old) | set(new), key=str):
        if old.get(k) != new.get(k):
            out.append(f"    {path}.{k}: {old.get(k)!r} → {new.get(k)!r}")
            if len(out) >= limit:
                out.append(f"    …（仅显示前 {limit} 条，共差异多于此）")
                break
    return out


def run(update: bool) -> int:
    # 重跑生产链路（previous 用入库产物：backfill 生成的初中外键只存在于入库）
    replay("data/linkage/scripts/build_special_plan.py", PLAN_TMP)
    replay("data/linkage/scripts/build_special_matrix.py", TMP, PROD)
    new = extract(json.load(open(TMP, encoding="utf-8")))

    if update:
        json.dump({**new, "note": "special_matrix 业务信息快照（非产物字节）。更新：--update-snapshot。",
                   "updated": "2026-09-21"}, open(SNAPSHOT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        print(f"✓ 基线已更新：{os.path.relpath(SNAPSHOT, ROOT)}（{sum(len(v) for v in new.values() if isinstance(v, dict))} 条业务信息）")
        return 0

    if not os.path.exists(SNAPSHOT):
        print(f"基线不存在：{SNAPSHOT}。首次运行请先 --update-snapshot 固化当前正确产物。")
        return 1

    base = json.load(open(SNAPSHOT, encoding="utf-8"))
    diffs = []
    for seg in ("high_school_ids", "special_plan_summary", "special_plan", "autonomy_plan"):
        diffs += diff_dict(base.get(seg, {}), new.get(seg, {}), seg)
    if diffs:
        print("业务快照: ✗ special_matrix 业务信息与基线不一致（数据变更或匹配回归）：")
        print("\n".join(diffs[:40]))
        print("  → 先逐条确认是官方源更新/解析修复（预期变化）还是回归；确认后显式更新基线：")
        print("     python3 data/linkage/test/check_special_matrix_snapshot.py --update-snapshot")
        print("  禁止直接改基线或产物掩盖 diff。")
        return 1
    n = sum(len(v) for v in new.values() if isinstance(v, dict))
    print(f"业务快照: ✓ special_matrix 业务信息与基线全等（{n} 条：名单→实体/计划数/项目）")
    return 0


if __name__ == "__main__":
    sys.exit(run("--update-snapshot" in sys.argv))
