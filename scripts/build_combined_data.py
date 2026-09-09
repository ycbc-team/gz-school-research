#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并地图页所需的全部数据 JS 为单个 data/combined.js（compact 格式）。

来源（顺序）：
  data/primary/schools.js        -> window.GZ_SCHOOLS
  data/primary/tier1.js          -> window.GZ_TIER1
  data/primary/enrollments/*.js  -> window.GZ_ENROLL_*
  data/middle/schools.js         -> window.GZ_MIDDLE_SCHOOLS
  data/middle/tier1.js           -> window.GZ_MIDDLE_TIER1
  data/high/schools.js           -> window.GZ_HIGH_SCHOOLS
  data/high/levels.js            -> window.GZ_HIGH_LEVELS

用法: python3 scripts/build_combined_data.py
效果: 地图页从加载 11 个 JS 文件（约 790KB，含缩进空白）变为 1 个 compact 文件，
      减少 file:// 下的文件读取与解析开销（首次加载提速）。
各源文件保持不变（多端共用不受影响）。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "combined.js"

SRC_FILES = [
    DATA / "primary" / "schools.js",
    DATA / "primary" / "tier1.js",
    *sorted((DATA / "primary" / "enrollments").glob("*.js")),
    DATA / "middle" / "schools.js",
    DATA / "middle" / "tier1.js",
    DATA / "high" / "schools.js",
    DATA / "high" / "levels.js",
]

PATTERN = re.compile(r"window\.([A-Z0-9_]+)\s*=\s*(\{.*?\});?\s*$", re.S)


def main() -> None:
    lines = ["/* 由 scripts/build_combined_data.py 生成：地图页单文件数据加载（compact），勿手改 */"]
    total_raw = 0
    for f in SRC_FILES:
        if not f.exists():
            raise SystemExit(f"缺少源文件: {f}")
        src = f.read_text(encoding="utf-8")
        total_raw += len(src)
        m = PATTERN.search(src)
        if not m:
            raise SystemExit(f"无法解析 {f} 中的 window.* 变量")
        name, payload = m.group(1), json.loads(m.group(2))
        compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"window.{name}={compact};")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_size = OUT.stat().st_size
    print(f"written: {OUT}  ({out_size/1024:.0f} KB, 源合计 {total_raw/1024:.0f} KB, 压缩 {(1-out_size/total_raw)*100:.0f}%)")
    print(f"变量: {[m.group(1) for m in [PATTERN.search(Path(f).read_text(encoding='utf-8')) for f in SRC_FILES]]}")


if __name__ == "__main__":
    main()
