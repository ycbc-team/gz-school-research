# level/src — 高中层级/学校清单源数据

`levels.json`：人工调研产物（学校清单/分类/指标，含特控率喜报/网传口径），是高中业务共享的人工源数据。

**消费方：**
- `data/poi/scripts/build_high_levels_js.py` —— 高中点位清洗依据（学校清单+分类+指标）
- `scripts/linkage/build_ranking_middle.py` —— 初中升学通道（特控率 indicators.tekong_*）
- 前端高中明细/排行榜（`apps/web` import + 小程序主包 require，经 compact 打包）

**打包约定（与 org_sort/cutoff_score 的 src 不同）：**
levels.json 没有独立 dist 构建，是"人工源即前端消费数据"，故 compact 对其 src 路径开例外——
WEB 端 `compact/high/level/src/levels.js` 与小程序主包均直接打包本文件；
其余 src 目录（如 `org_sort/src/`、`cutoff_score/src/`）仍遵循"src 不打包、仅 dist 产物打包"。

更新：人工修订后需重跑 `npm run check`（build_high_levels / build_ranking_middle 一致性防线校验漂移）。
