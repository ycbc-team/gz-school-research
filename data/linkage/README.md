# 升学通道数据（data/linkage）

高中→初中升学链路的 2026 官方数据。为模型 `Q_j = Σ_i (n_ji/m_j × H_i × α) + 自招/特长归一化` 提供输入。

## 目录分层

| 层 | 内容 | 说明 |
|---|---|---|
| `raw/` | 政府源文件 | 官方 PDF/DOCX/HTML 原件（名额分配结果、第二批次分数、海珠区名额、特长生计划附件） |
| `parsed/` | 转录 json | 由 raw 原件转录/OCR 的结构化 JSON（分数全量、OCR 网格、校名、自招/特长生名单与计划） |
| `dist/` | 运行时产物 | 构建脚本产出的最终数据（quota/special/batch2/district/ranking + 未命中清单） |
| `src/` | 手工源文件 | 人工采集的官方名录（`official_rosters/`，区级全量校验基线） |
| `scripts/` | 脚本 | 复现管线（从 raw → parsed → dist 的全部构建脚本） |
| `test/` | 测试 | 快照/漂移校验（如 `check_special_matrix_snapshot.py`） |
| `docs/` | 文档 | 方案记录（OCR 踩坑与修复过程等） |
| `README.md` | 业务说明 | 本文件 |

## 最终数据（dist/）

| 文件 | 内容 | 规模 |
|---|---|---|
| `dist/quota_matrix.json` | 2026 名额分配完整矩阵：每所初中的名额考生数 m_j、省市属/区属名额，及 21 个省市属高中校区的指标数 n_ji | 498 所初中 × 21 校区 |
| `dist/batch2_scores.json` | 2026 第二批次（名额分配）录取分数：每所初中被各高中校区录取的最低/末位分 | 省市属 20 校区 × 463 所初中 |
| `dist/special_matrix.json` | 2026 第一批招生事实：①自主招生计划数（按校区，`autonomy_plan` + norm 索引）②体育/艺术特长生计划数（按校区+项目，`special_plan`/`special_plan_summary`）③名单原文→高中实体 school_id 外键（`high_school_ids`，供升学路径页跳转） | 自招 56 校区 / 特长生 72 校区 / 名单 116 高中 |
| `dist/ranking_middle.json` | 初中升学信号基础表：每所初中考生数/省市属指标/区属指标/自招数/指标到校高中明细（含特控率） | 334 校（7 区） |
| `dist/district_quota.json` | 区属高中名额分配到本区初中（初中名 → {区属高中名: 名额}） | 7 区 |
| `dist/_school_id_unmatched.json` | 官方名单名未命中实体表清单（7 区内待人工桥接 / 7 区外正常不可点） | 运行时审计产物 |

> 历史说明：第一批"资格名单计数矩阵"（每所初中升入各高中的资格人数）已废弃删除——初中第一批模块与高中第一批覆盖初中表均于 2026-09 移除，前端不再消费；`build_special_matrix.py` 不再输出 `matrix` 键，仅保留计划数与名单外键。资格名单原始计数仍可经 `build_ranking_middle.py`（初中升学信号"自招人数"列）回溯 `parsed/autonomy/autonomy_qualify_2026.json`。

校验：`quota_matrix.json` 列和已强校验 0 不一致（col1 省市属名额 = Σ21 校区列）；10 所民办 `sheng_quota=None` 为不参与省市属名额分配，非缺失。特长生计划总量已硬校验=官方口径（体育 1905 不含领军龙 / 艺术 1741 / 领军龙 116）。

## 政府源文件（raw/）

| 文件 | 官方来源 |
|---|---|
| `raw/quota_detail.pdf` + `quota_detail.html` / `quota_summary.html` / `quota_result_notice.html` | 2026 名额分配结果（全市 31 页） |
| `raw/batch2_scores.pdf` | 2026 第二批次录取分数原表（304 页） |
| `raw/haizhu_quota.pdf` | 海珠区名额分配 |
| `raw/special/附件1.2026年体育艺术类特长生布局项目及计划学校明细表.docx` | 2026 特长生计划官方明细（110 校，`build_special_plan.py` 输入） |

> 已清理（2026-09）：第一批官方原始下载件（资格名单 PDF/zip、特长生测试名单 PDF/zip、申诉 docx、notice.html）无任何脚本引用，JSON 已固化于 `parsed/`，原件删除；生产脚本保留。

## 转录 json（parsed/）

| 文件 | 来源 |
|---|---|
| `parsed/batch2_scores_all.json` | `parse_batch2.py` 从 `raw/batch2_scores.pdf` 转录的全量行 |
| `parsed/quota_grid_final.json` | 名额分配网格 OCR 中间结果（仅保留 sz 高中分额列供补行，三列作废，见 docs/OCR方案记录.md） |
| `parsed/schoolnames.json` | 名额分配校名 OCR 结果（校名源） |
| `parsed/autonomy/autonomy_qualify_2026.json` | 2026 自主招生资格名单（按考生，用于初中升学信号"自招人数"计数） |
| `parsed/autonomy/plan_2026.json` | 2026 自主招生计划数汇总（56 校区，`autonomy_plan` 来源） |
| `parsed/special/plan_special_2026.json` | 特长生计划解析产物（`special_plan` 来源） |
| `parsed/special/sports_2026.json` / `arts_2026.json` | 体育/艺术特长生通过专业测试名单（构建 `high_school_ids` 名单集合） |

## 手工源文件（src/）

| 文件 | 内容 |
|---|---|
| `src/official_rosters/` | 区级官方全量名录（人工采集自政府/教育局公开页面，带 source_url），作为实体表全量校验基线（`scripts/verify_official_rosters.py` 消费） |

## 复现管线（scripts/）

```bash
# 名额分配矩阵：目视 OCR 权威值 → 重建（含 school_id 通用匹配）
python3 data/linkage/scripts/rebuild_quota_matrix.py    # parsed/schoolnames+quota_grid_final + quota_vision_values → dist/quota_matrix.json
python3 data/linkage/scripts/build_district_quota.py    # grid 区属列 → dist/district_quota.json

# 第二批次上岸分数
python3 data/linkage/scripts/parse_batch2.py            # raw/batch2_scores.pdf → parsed/batch2_scores_all.json
python3 data/linkage/scripts/build_linkage_batch2.py    # 过滤省市属 → dist/batch2_scores.json

# 第一批招生（自招计划 / 特长生计划 / 名单外键）
python3 data/linkage/scripts/build_special_plan.py      # raw/special 附件1 docx → parsed/special/plan_special_2026.json（内置小计硬校验）
python3 data/linkage/scripts/build_special_matrix.py    # 名单 + 计划源 → dist/special_matrix.json
python3 data/linkage/scripts/build_ranking_middle.py    # autonomy 资格名单 + quota_matrix + levels → dist/ranking_middle.json

# 外键回填（dist 四表 school_id / middle_school_ids + 未命中清单）
python3 data/linkage/scripts/backfill_school_ids.py     # → dist/_school_id_unmatched.json
```

历史迭代脚本（v2–v12、各 fix 轮、早期 OCR 实验）已删除，仅留方案记录于 `docs/OCR方案记录.md`。

## 年度刷新流程

每年 4–7 月官方发布新一年文件后：
1. 将新一年 PDF/DOCX/HTML 原件放入 `raw/`（沿用现有文件名，或加年份区分）。
2. 按上述管线重跑脚本；名额分配 PDF 若为 CID 字体无文本层，沿用"300dpi 渲染 → 列线检测 → 逐格 OCR → col1=Σ21 强校验"，不一致行用视觉 OCR 读真值后回写。
3. 更新本 README 的年度与数据规模；跨年对比只新增当年文件，不覆盖历史年。

## 数据约束规则（适用于 xiaoshengchu 小学升学路线）

1. **预警名单禁作派位/对口数据源**：官方《学位供给紧张信息预告》只用于学位预警展示，严禁写入 `feed_junior_highs`。
2. **只认年度正式文件**：以当年官方《招生计划、招生地段及条件》或区教育局公布的初中招生计划/分组表/对口直升表为准；`source_url` 必须指向具体官方文件页。
3. **配建校/特殊通道单独标注**：小区配建公办初中招生范围仅限小区业主子女，不得混入普通学区派位池；自愿报名/电脑抽签通道在 `source_note` 注明。
4. **数据缺口显式化**：无法确认对口时 `feed_junior_highs` 置 `[]` 并在 `data_gaps`/`source_note` 记原因，禁止把"（待查）"占位文本写入 feed。
5. **年度刷新**：每年官方发布新表后重核；派位/地段调整的学校只改目标字段，其他保留。
