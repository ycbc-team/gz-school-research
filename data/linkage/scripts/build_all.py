#!/usr/bin/env python3
"""升学通道（data/linkage）全链路构建编排。

管线（A/B/C 分层）：
  A 转录（需 raw 原件，已固化为 parsed 时自动跳过）：
      parse_batch2.py / build_special_plan.py   （PDF/DOCX → parsed JSON）
  B 清洗（parsed + src 校正源 → parsed/canonical/ 规范表）：
      rebuild_quota_matrix.py    名额分配计划（视觉三列 + 校名修正 + sz 继承）
      build_district_quota.py    区属名额（视觉校验表 + OCR 对照告警）
      build_linkage_batch2.py    第二批次分数（省市属过滤）
      build_special_matrix.py    升学通道矩阵（名单 → 高中实体外键）
  C 加工（canonical → dist 运行时产物；C 层脚本一律读 canonical，不依赖其他 C 层 dist）：
      backfill_school_ids.py     SchoolMatcher：canonical 写回 school_id/middle_school_ids；
                                 dist ids/schools 并行拆分（有 id 的键/行进 ids，仅无 id 匹配
                                 保留原文进 schools；多名同 id 冲突保底原文不覆盖丢行）
      optimize_redundancy.mjs    去冗余（sz 稀疏化、删 admitted:false 行、msi 裁剪）
      build_ranking_middle.py    初中升学信号聚合（canonical 全量含 sz 明细；dist 删 sz/元数据）
  校验（用户口径：快照只用 canonical，dist 只做轻量结构断言）：
      check_special_matrix_snapshot.py  special_matrix canonical 业务快照
      check_dist_snapshots.py           其余四产物 canonical 业务快照 + dist 结构断言

用法：
  python3 data/linkage/scripts/build_all.py             # B → C → 校验
  python3 data/linkage/scripts/build_all.py --skip-check  # 只构建不校验
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(ROOT, "data", "linkage", "scripts")
TEST = os.path.join(ROOT, "data", "linkage", "test")


def run(cmd, label):
    print(f"\n== {label} ==")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"✗ {label} 失败（exit {r.returncode}）")
        sys.exit(1)
    print(f"✓ {label} 完成")


def main():
    skip_check = "--skip-check" in sys.argv
    py = sys.executable or "python3"

    # ---------- B 层：规范表 ----------
    run([py, os.path.join(SCRIPTS, "rebuild_quota_matrix.py")], "B1 名额分配计划 → canonical")
    run([py, os.path.join(SCRIPTS, "build_district_quota.py")], "B2 区属名额 → canonical（OCR 对照告警）")
    run([py, os.path.join(SCRIPTS, "build_linkage_batch2.py")], "B3 第二批次分数 → canonical")
    run([py, os.path.join(SCRIPTS, "build_special_matrix.py")], "B4 升学通道矩阵 → canonical")

    # ---------- C 层：运行时产物 ----------
    run([py, os.path.join(SCRIPTS, "backfill_school_ids.py")], "C1 SchoolMatcher 回填 school_id")
    run(["node", os.path.join(ROOT, "scripts", "data", "optimize_redundancy.mjs")], "C2 去冗余优化")
    run([py, os.path.join(SCRIPTS, "build_ranking_middle.py")], "C3 初中升学信号聚合")

    # ---------- 校验 ----------
    if skip_check:
        print("\n已跳过校验（--skip-check）。")
        return 0
    run([py, os.path.join(TEST, "check_special_matrix_snapshot.py")], "校验 special_matrix 快照")
    run([py, os.path.join(TEST, "check_dist_snapshots.py")], "校验 dist 四产物快照")
    print("\n全链路完成：B 规范表 → C 运行时产物 → 快照全等 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
