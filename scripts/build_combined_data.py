#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并旧地图页所需的全部数据 JS 为单个 legacy/_generated/combined.js（compact 格式）。

来源（顺序，均为 legacy/_generated 下的浏览器兼容产物）：
  primary/schools.js        -> window.GZ_SCHOOLS
  primary/tier1.js          -> window.GZ_TIER1
  primary/enrollments/*.js  -> window.GZ_ENROLL_*
  middle/schools.js         -> window.GZ_MIDDLE_SCHOOLS
  middle/tier1.js           -> window.GZ_MIDDLE_TIER1
  high/schools.js           -> window.GZ_HIGH_SCHOOLS
  high/levels.js            -> window.GZ_HIGH_LEVELS

用法: python3 scripts/build_combined_data.py
效果: 旧地图页从加载 11 个 JS 文件（约 790KB，含缩进空白）变为 1 个 compact 文件，
      减少 file:// 下的文件读取与解析开销（首次加载提速）。

数据治理约定：data/ 下 JSON 为唯一数据真源；apps/web/legacy/_generated/ 下 *.js
是仅服务旧页面（file:// 直接打开）的浏览器兼容产物，由本脚本及各 fetch/build 脚本生成，
Vue3 重构完成后随旧页面一并下线。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY_GEN = ROOT / "apps" / "web" / "legacy" / "_generated"
OUT = LEGACY_GEN / "combined.js"

SRC_FILES = [
    LEGACY_GEN / "primary" / "schools.js",
    LEGACY_GEN / "primary" / "tier1.js",
    *sorted((LEGACY_GEN / "primary" / "enrollments").glob("*.js")),
    LEGACY_GEN / "middle" / "schools.js",
    LEGACY_GEN / "middle" / "tier1.js",
    LEGACY_GEN / "high" / "schools.js",
    LEGACY_GEN / "high" / "levels.js",
]

PATTERN = re.compile(r"window\.([A-Z0-9_]+)\s*=\s*(\{.*?\});?\s*$", re.S)


def main() -> None:
    lines = ["/* 由 scripts/build_combined_data.py 生成：旧地图页单文件数据加载（compact），勿手改 */"]
    total_raw = 0
    names = []
    for f in SRC_FILES:
        if not f.exists():
            raise SystemExit(f"缺少源文件: {f}")
        src = f.read_text(encoding="utf-8")
        total_raw += len(src)
        m = PATTERN.search(src)
        if not m:
            raise SystemExit(f"无法解析 {f} 中的 window.* 变量")
        name, payload = m.group(1), json.loads(m.group(2))
        names.append(name)
        compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"window.{name}={compact};")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_size = OUT.stat().st_size
    print(f"written: {OUT}  ({out_size/1024:.0f} KB, 源合计 {total_raw/1024:.0f} KB, 压缩 {(1-out_size/total_raw)*100:.0f}%)")
    print(f"变量: {names}")


if __name__ == "__main__":
    main()
