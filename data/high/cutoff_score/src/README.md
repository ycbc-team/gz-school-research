# cutoff_score/src — 手工源数据

手工录入/人工整理的高中录取分源数据放在本目录（如人工转录、待复核修正、非官方渠道补录）。

当前无手工源数据：2025/2026 两年录取分完全由 `../scripts/build_scores.py` 从官方招考办页面（`../raw/` 原始 HTML）解析生成，产物为 `../dist/scores_{year}.json`。

约定：本目录内容属源数据，**不打包进 web/小程序产物**（compact 编译排除 `src` 路径段，仅 `dist` 产物打包）。
