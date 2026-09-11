# 升学通道数据（data/linkage）

高中→初中升学链路的 2026 官方数据。为模型 `Q_j = Σ_i (n_ji/m_j × H_i × α) + 自招/特长归一化` 提供输入。

## 最终数据

| 文件 | 内容 | 规模 |
|---|---|---|
| `quota_matrix.json` | 2026 名额分配完整矩阵：每所初中的名额考生数 m_j、省市属/区属名额，及 21 个省市属高中校区的指标数 n_ji | 498 所初中 × 21 校区 |
| `batch2_scores.json` | 2026 第二批次（名额分配）录取分数：每所初中被各高中校区录取的最低/末位分 | 省市属 20 校区 × 463 所初中 |
| `special_matrix.json` | 2026 自招/体育/艺术特长名单：每所初中升入各高中校区的各类别人数 | 288 所初中 × 19 校区 |

校验：`quota_matrix.json` 列和已强校验 0 不一致（col1 省市属名额 = Σ21 校区列）；10 所民办 `sheng_quota=None` 为不参与省市属名额分配，非缺失。

## 政府源文档（raw/）

| 文件 | 官方来源 |
|---|---|
| `raw/quota_detail.pdf` + `quota_detail.html` / `quota_summary.html` / `quota_result_notice.html` | 2026 名额分配结果（全市 31 页） |
| `raw/batch2_scores.pdf` | 2026 第二批次录取分数原表（304 页） |
| `raw/haizhu_quota.pdf` | 海珠区名额分配 |
| `raw/autonomy/附件1.…自主招生…pdf`、`附件2.…申诉…docx`、`autonomy_qualify_2026.json`、`notice.html` | 2026 普通高中自主招生资格名单 |
| `raw/special/附件1.…体育…pdf`、`附件2.…艺术…pdf`、`附件3.…申诉…docx`、`sports_2026.json`、`arts_2026.json`、`notice.html` | 2026 体育/艺术特长生通过名单 |
| `raw/quota_grid_final.json`、`raw/schoolnames.json`、`raw/headers/header_ocr*.json` | 名额分配网格解析中间结果与人工确认的列序证据 |

## 复现管线（scripts/linkage/）

```bash
# 名额分配矩阵：渲染 PDF → 列网格 OCR → 校名 → 组装
python3 scripts/linkage/parse_quota_grid5b.py    # quota_detail.pdf → quota_grid_final.json
python3 scripts/linkage/ocr_schoolnames.py        # → schoolnames.json
python3 scripts/linkage/assemble_quota.py        # grid + schoolnames → quota_matrix.json

# 第二批次上岸分数
python3 scripts/linkage/parse_batch2.py          # batch2_scores.pdf → batch2_scores_all.json
python3 scripts/linkage/build_linkage_batch2.py   # 过滤省市属 → batch2_scores.json

# 自招/体育/艺术特长
python3 scripts/linkage/build_special_matrix.py  # autonomy/special 源 → special_matrix.json
```

历史迭代脚本（v2–v12、各 fix 轮、早期 OCR 实验）归档在 `scripts/linkage/_archive/`，仅作留痕，不再维护。

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
