# 升学通道数据（data/linkage）

高中→初中升学链路的 2026 官方数据。为模型 `Q_j = Σ_i (n_ji/m_j × H_i × α) + 自招/特长归一化` 提供输入。

## 目录分层（A/B/C 三层架构）

| 层 | 目录 | 内容 | 说明 |
|---|---|---|---|
| A 转录 | `raw/` | 政府源文件 | 官方 PDF/DOCX/HTML 原件（名额分配结果、第二批次分数、特长生计划附件等） |
| A 转录 | `parsed/` | 转录 json | 由 raw 转录/OCR 的结构化 JSON（分数全量、OCR 网格、校名、名单与计划） |
| B 清洗 | `parsed/canonical/` | 规范表 | B 层输出：清洗校正后的统一规范表（校名 + 全字段，**不含 school_id**——外键统一由 C 层生成） |
| B 校正 | `src/` | 手工校正源 | 人工视觉校验值 / 校名修正 / 匹配硬映射（JSON 化，带出处与原因，可审计） |
| C 加工 | `dist/` | 运行时产物 | C 层输出：SchoolMatcher 回填 school_id + 去冗余 + 聚合（前端唯一消费层） |
| — | `scripts/` | 脚本 | 复现管线（A→B→C 全部构建脚本 + `build_all.py` 编排） |
| — | `test/` | 测试 | 业务快照测试（产物任何变更必须显式暴露） |
| — | `docs/` | 文档 | 方案记录（OCR 踩坑与修复过程等） |
| — | `README.md` | 业务说明 | 本文件 |

**分层约定（用户口径）**：
- **A 层**：对 raw 转录（OCR/xlsx 等）→ `parsed/`
- **B 层**：对 A 清洗——统一数据格式、修复 OCR 识别错误、结合 `src/` 手工产物校正 → `parsed/canonical/`
- **C 层**：对 B 进一步加工成运行时产物——SchoolMatcher 把校名匹配成 school_id、去掉运行时不需要的字段 → `dist/`
- **dist 是纯派生产物**：任何变更必须改脚本 + 重跑 + 快照测试显式暴露，禁止直接手改 dist。

## 最终数据（dist/，C 层运行时产物）

| 文件 | 内容 | 规模 |
|---|---|---|
| `dist/quota_matrix.json` | 2026 名额分配完整矩阵：每所初中的名额考生数 m_j、省市属/区属名额，及 21 个省市属高中校区的指标数 n_ji；school_id/school_ids 由 C 层回填 | 503 所初中 × 21 校区 |
| `dist/batch2_scores.json` | 2026 第二批次（名额分配）录取分数：每所初中被各高中校区录取的最低/末位分 + middle_school_ids | 省市属 20 校区 × 463 所初中 |
| `dist/special_matrix.json` | 2026 第一批招生事实：①自招计划数（`autonomy_plan`）②特长生计划数（`special_plan`）③名单原文→高中实体外键（`high_school_ids`） | 自招 56 校区 / 特长生 72 校区 / 名单 116 高中 |
| `dist/ranking_middle.json` | 初中升学信号基础表：考生数/省市属指标/区属指标/自招数/指标到校明细（含特控率） | 334 校（7 区） |
| `dist/district_quota.json` | 区属高中名额分配到本区初中（初中名 → {区属高中名: 名额}）+ middle_school_ids | 329 所（7 区） |
| `dist/_school_id_unmatched.json` | 官方名单名未命中实体表清单（7 区内待人工桥接 / 7 区外正常不可点） | 运行时审计产物 |

> 历史清理（2026-09-24）：①第一批"资格名单计数矩阵"已废弃（前端不再消费），其遗留字段
> `special_matrix.middle_school_ids`（269 条、与 quota_matrix 同名不同 id 13 处、无任何消费方）一并移除；
> ②`ranking_middle` 应元颐和实验学校 school_id 已由重建修复（过期 `87a92ab6` → 正确 `4af73d54`，
> 历史 c7639c3 漏重跑该表）。

校验：`quota_matrix.json` 列和已强校验（col1 省市属名额 = Σ21 校区列；天河区 1 人残差为官方印刷口径，
HEAD 产物即如此）；10 所民办 `sheng_quota=None` 为不参与省市属名额分配，非缺失。特长生计划总量已硬校验
=官方口径（体育 1905 不含领军龙 / 艺术 1741 / 领军龙 116）。

## 政府源文件（raw/，A 层）

| 文件 | 官方来源 |
|---|---|
| `raw/quota_detail.pdf` + `quota_detail.html` / `quota_summary.html` / `quota_result_notice.html` | 2026 名额分配结果（全市 31 页） |
| `raw/batch2_scores.pdf` | 2026 第二批次录取分数原表（304 页） |
| `raw/haizhu_quota.pdf` | 海珠区名额分配 |
| `raw/special/附件1.2026年体育艺术类特长生布局项目及计划学校明细表.docx` | 2026 特长生计划官方明细（110 校，`build_special_plan.py` 输入） |

> 已清理（2026-09）：第一批官方原始下载件（资格名单 PDF/zip、特长生测试名单 PDF/zip 等）无脚本引用，
> JSON 已固化于 `parsed/`，原件删除。

## 转录 json（parsed/，A 层产物）

| 文件 | 来源 |
|---|---|
| `parsed/batch2_scores_all.json` | `parse_batch2.py` 从 `raw/batch2_scores.pdf` 转录的全量行 |
| `parsed/quota_grid_final.json` | 名额分配网格 OCR 中间结果（**仅作 B 层对照/行结构**，三列与区属列视觉值不采信，见 docs/OCR方案记录.md） |
| `parsed/schoolnames.json` | 名额分配校名 OCR 结果（校名源） |
| `parsed/autonomy/autonomy_qualify_2026.json` | 2026 自主招生资格名单（按考生，初中升学信号"自招人数"计数源） |
| `parsed/autonomy/plan_2026.json` | 2026 自主招生计划数汇总（56 校区） |
| `parsed/special/plan_special_2026.json` | 特长生计划解析产物 |
| `parsed/special/sports_2026.json` / `arts_2026.json` | 体育/艺术特长生通过专业测试名单（`high_school_ids` 名单集合源） |
| `parsed/canonical/` | **B 层规范表**（quota_matrix / district_quota / batch2_scores / special_matrix，见下） |

## 手工校正源（src/，B 层校正）

| 文件 | 内容 |
|---|---|
| `src/district_quota_vision.json` | 区属名额**视觉校验权威表**（329 所，逐区目视读取；替代 OCR 区属列。出处：fd72c57 视觉校验 297→330、a6c37a9 行错位修正） |
| `src/quota_vision_values.json` | 名额三列（考生/省市/区属）视觉权威值 `{页 → {行 → [考生,省市,区属]}}` + P16_INSERT 补行（31 页） |
| `src/name_fix.json` | quota_matrix 校名人工修正（页,行 → 官方原文名） |
| `src/special_name_fix.json` | special_matrix 高中名人工修正（名单截断补全 / 裸名歧义归位） |
| `src/backfill_overrides.json` | backfill 人工核对硬映射（官方名 → school_id，含逐条原因） |
| `src/official_rosters/` | 区级官方全量名录（人工采集，实体表校验基线，`scripts/verify_official_rosters.py` 消费） |

## 复现管线（scripts/，A → B → C）

一键编排：`python3 data/linkage/scripts/build_all.py`（B → C → 快照校验；`--skip-check` 跳过校验）。

```bash
# ── A 转录（需 raw 原件；已固化为 parsed 时跳过）──────────────
python3 data/linkage/scripts/parse_batch2.py            # raw/batch2_scores.pdf → parsed/batch2_scores_all.json
python3 data/linkage/scripts/build_special_plan.py      # raw/special 附件1 docx → parsed/special/plan_special_2026.json

# ── B 清洗（parsed + src → parsed/canonical/ 规范表）────────
python3 data/linkage/scripts/rebuild_quota_matrix.py    # src/quota_vision_values + src/name_fix + grid/schoolnames → canonical/quota_matrix.json（sz 继承，school_id 不生成）
python3 data/linkage/scripts/build_district_quota.py    # src/district_quota_vision → canonical/district_quota.json + OCR 对照告警（不覆盖）
python3 data/linkage/scripts/build_linkage_batch2.py    # parsed 全量过滤省市属 → canonical/batch2_scores.json
python3 data/linkage/scripts/build_special_matrix.py    # 名单 + 计划源 + src/special_name_fix → canonical/special_matrix.json（high_school_ids）

# ── C 加工（canonical → dist 运行时产物）───────────────────
python3 data/linkage/scripts/backfill_school_ids.py     # SchoolMatcher：canonical 四表 → dist 四表 school_id/middle_school_ids + _school_id_unmatched.json
node scripts/data/optimize_redundancy.mjs               # dist 去冗余（sz 稀疏化 / 删 admitted:false 行 / msi 裁剪）
python3 data/linkage/scripts/build_ranking_middle.py    # autonomy + dist/quota_matrix + district_quota + levels → dist/ranking_middle.json

# ── 校验（产物任何变更必须显式暴露）─────────────────────────
python3 data/linkage/test/check_special_matrix_snapshot.py   # special_matrix 业务快照（247 条）
python3 data/linkage/test/check_dist_snapshots.py            # quota/district/batch2/ranking 业务快照（重放链路 → 与基线全等）
```

历史迭代脚本（v2–v12、各 fix 轮、早期 OCR 实验）已删除，仅留方案记录于 `docs/OCR方案记录.md`。

## 数据流与职责（防止"直接改 dist"）

1. **A 转录**：raw 原件 → parsed JSON（转录脚本带内置硬校验，如特长生计划小计）。
2. **B 清洗**：parsed + src 校正源 → canonical 规范表。OCR 网格是**校验参照**不是数据源——区属列
   与三列的权威值在 `src/`（视觉目视读取，历史 fd72c57/a6c37a9 曾直接改 dist 未写脚本，现已固化为
   src 校正源并文档化）。
3. **C 加工**：canonical → dist。school_id/middle_school_ids 唯一真源是 `backfill_school_ids.py`
   （`src/backfill_overrides.json` 硬映射优先）；任何"实体表变更 → 外键变化"都经此层暴露。
4. **快照测试**：`test/check_dist_snapshots.py` 重放 B→C 全链路并与基线全等对比；`--update-snapshot`
   显式更新基线。dist 若被手改，下一次重放即覆盖并以 diff 暴露。
5. **sz 明细继承**：quota_matrix 的 sz（21 校区分额）为历史 OCR 产物，无独立 raw 源可重建，
   持久层为 canonical（首次从 dist 引导），重放不丢。

## 年度刷新流程

每年 4–7 月官方发布新一年文件后：
1. 将新一年 PDF/DOCX/HTML 原件放入 `raw/`（沿用现有文件名，或加年份区分）。
2. 按上述管线重跑（`build_all.py`）；名额分配 PDF 若为 CID 字体无文本层，沿用"300dpi 渲染 →
   列线检测 → 逐格 OCR → col1=Σ21 强校验"，不一致行用视觉 OCR 读真值后写回 `src/` 校正源。
3. 更新本 README 的年度与数据规模；跨年对比只新增当年文件，不覆盖历史年。

## 数据约束规则（适用于 xiaoshengchu 小学升学路线）

1. **预警名单禁作派位/对口数据源**：官方《学位供给紧张信息预告》只用于学位预警展示，严禁写入 `feed_junior_highs`。
2. **只认年度正式文件**：以当年官方《招生计划、招生地段及条件》或区教育局公布的初中招生计划/分组表/对口直升表为准；`source_url` 必须指向具体官方文件页。
3. **配建校/特殊通道单独标注**：小区配建公办初中招生范围仅限小区业主子女，不得混入普通学区派位池；自愿报名/电脑抽签通道在 `source_note` 注明。
4. **数据缺口显式化**：无法确认对口时 `feed_junior_highs` 置 `[]` 并在 `data_gaps`/`source_note` 记原因，禁止把"（待查）"占位文本写入 feed。
5. **年度刷新**：每年官方发布新表后重核；派位/地段调整的学校只改目标字段，其他保留。
