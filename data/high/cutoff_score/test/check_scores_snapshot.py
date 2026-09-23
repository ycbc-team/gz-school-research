#!/usr/bin/env python3
"""录取分数线业务快照测试（2026-09-21 由 special_matrix 快照模式推广）。

替代字节全等"重跑 vs 入库"（入库被 bug 污染时自我一致通过）；快照锁定各校
[学校: 分数线/批次] 业务信息，重跑 build_scores 后与独立基线全等对比：

- 全等 → 通过：分数/批次未发生意外变化
- 有差异 → 失败并逐条列出（旧 → 新）：官方源更新 / 解析修复 / 分数线回归显式暴露

基线独立于产物，改动须显式 --update-snapshot（数据变更=正常迭代，先看 diff
确认是官方更新还是回归，禁止改产物掩盖）。

用法：
  python3 data/high/cutoff_score/scripts/check_scores_snapshot.py                    # 对比
  python3 data/high/cutoff_score/scripts/check_scores_snapshot.py --update-snapshot  # 更新基线
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DIST = os.path.join(ROOT, "data/high/cutoff_score/dist")
SNAPSHOT = os.path.join(ROOT, "data/high/cutoff_score/test/snapshots/scores_snapshot.json")
BUILD = os.path.join(ROOT, "data/high/cutoff_score/scripts/build_scores.py")
TMP = os.path.join(__import__("tempfile").gettempdir(), "scores_snapshot_repro")
YEARS = ("2025", "2026")


def extract() -> dict:
    """重跑 build_scores → {year: {school_id: [批次: 分数线/性质/批次]}}。"""
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    r = subprocess.run(["python3", BUILD, "--out-dir", TMP], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print("生产脚本重跑失败：build_scores.py")
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(1)
    out = {}
    for y in YEARS:
        p = os.path.join(TMP, f"scores_{y}.json")
        if not os.path.exists(p):
            print(f"缺产物：{p}")
            sys.exit(1)
        out[y] = json.load(open(p, encoding="utf-8"))["by_school_id"]
    return out


def diff_dict(old: dict, new: dict, path: str, limit: int = 40) -> list:
    out = []
    for k in sorted(set(old) | set(new), key=str):
        if old.get(k) != new.get(k):
            out.append(f"    {path}.{k}: {json.dumps(old.get(k), ensure_ascii=False)[:100]!r} → "
                       f"{json.dumps(new.get(k), ensure_ascii=False)[:100]!r}")
            if len(out) >= limit:
                out.append(f"    …（仅显示前 {limit} 条，共差异多于此）")
                break
    return out


def run(update: bool) -> int:
    new = extract()
    if update:
        json.dump({**new, "note": "录取分数线业务快照（非产物字节）。更新：--update-snapshot。",
                   "updated": "2026-09-21"}, open(SNAPSHOT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        n = sum(len(v) for v in new.values())
        print(f"✓ 基线已更新：{os.path.relpath(SNAPSHOT, ROOT)}（{n} 校×批次分数线）")
        return 0
    if not os.path.exists(SNAPSHOT):
        print(f"基线不存在：{SNAPSHOT}。首次运行请先 --update-snapshot 固化当前正确产物。")
        return 1
    base = json.load(open(SNAPSHOT, encoding="utf-8"))
    diffs = []
    for y in YEARS:
        diffs += diff_dict(base.get(y, {}), new.get(y, {}), f"scores_{y}")
    if diffs:
        print("业务快照: ✗ 录取分数线与基线不一致（分数线/批次变更或回归）：")
        print("\n".join(diffs[:40]))
        print("  → 先逐条确认是官方源更新/解析修复（预期变化）还是回归；确认后显式更新基线：")
        print("     python3 data/high/cutoff_score/scripts/check_scores_snapshot.py --update-snapshot")
        print("  禁止直接改基线或产物掩盖 diff。")
        return 1
    n = sum(len(v) for v in new.values())
    print(f"业务快照: ✓ 录取分数线与基线全等（{n} 校×批次，独立基线）")
    return 0


if __name__ == "__main__":
    sys.exit(run("--update-snapshot" in sys.argv))
