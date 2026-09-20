#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载广州市招考办官方中考录取分数页面 → data/high/cutoff_score/raw/（政府源文件）。

与 build_scores.py 分拆（2026-09-20）：
- fetch_scores.py：下载官方 HTML 到 raw/。**仅每年录取批次公布时手动跑一次**，不进入 check。
- build_scores.py：解析 raw/ HTML → 匹配实体 → dist/scores_{year}.json。
  每次 `npm run check` 由 check_groups_drift 重跑并与入库产物比对（分数清单变化即失败）。

用法: python3 data/high/cutoff_score/scripts/fetch_scores.py
依赖: 网络（curl 下载 gzzk.gz.gov.cn 官方页）；raw/ 已 gitignore（可随时重下）。
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
RAW = ROOT / "data" / "high" / "cutoff_score" / "raw"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# year -> [(batch, 页面文件, 官方标题, 官方URL)]（build_scores.py 从本模块 import，单一来源）
PAGES = {
    2025: [
        (1, "scores_2025_batch1.html",
         "2025年广州市高中阶段学校招生录取分数（第一批次招生学校）",
         "https://gzzk.gz.gov.cn/gkmlpt/content/10/10363/post_10363521.html"),
        (3, "scores_2025_batch3.html",
         "2025年广州市高中阶段学校招生录取分数（第三批次招生学校）",
         "http://gzzk.gz.gov.cn/zwgk/zwdt/content/post_10365139.html"),
        (4, "scores_2025_batch4.html",
         "2025年广州市高中阶段学校招生录取分数（第四批次普通高中和综合高中）",
         "http://gzzk.gz.gov.cn/gkmlpt/content/10/10365/mpost_10365556.html"),
    ],
    2026: [
        (1, "scores_2026_batch1.html",
         "2026年广州市高中阶段学校招生录取分数（第一批次招生学校）",
         "http://gzzk.gz.gov.cn/zkzz/zkxx/lnfs/content/post_10908006.html"),
        (3, "scores_2026_batch3.html",
         "2026年广州市高中阶段学校招生录取分数（第三批次招生学校）",
         "http://gzzk.gz.gov.cn/zwgk/zkyw/content/post_10909610.html"),
        (4, "scores_2026_batch4.html",
         "2026年广州市高中阶段学校招生录取分数（第四批次高中）",
         "http://gzzk.gz.gov.cn/gkmlpt/content/10/10910/post_10910162.html"),
    ],
}


def fetch_pages():
    RAW.mkdir(parents=True, exist_ok=True)
    for year, pages in PAGES.items():
        for batch, fname, _title, url in pages:
            dst = RAW / fname
            subprocess.run(
                ["curl", "-sL", "-A", UA, "-o", str(dst), url], check=True)
            print(f"fetched {fname} ({dst.stat().st_size} bytes)")


if __name__ == "__main__":
    fetch_pages()
