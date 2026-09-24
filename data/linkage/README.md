# 升学通道数据（data/linkage）

高中→初中升学链路的 2026 官方数据。为模型 `Q_j = Σ_i (n_ji/m_j × H_i × α) + 自招/特长归一化` 提供输入。

## 最终数据

| 文件 | 内容 | 规模 |
|---|---|---|
| `quota_matrix.json` | 2026 名额分配完整矩阵：每所初中的名额考生数 m_j、省市属/区属名额，及 21 个省市属高中校区的指标数 n_ji | 498 所初中 × 21 校区 |
| `batch2_scores.json` | 2026 第二批次（名额分配）录取分数：每所初中被各高中校区录取的最低/末位分 | 省市属 20 校区 × 463 所初中 |
| `special_matrix.json` | 2026 第一批招生事实：①自主招生计划数（按校区，`autonomy_plan` + norm 索引）②体育/艺术特长生计划数（按校区+项目，`special_plan`/`special_plan_summary`）③名单原文→高中实体 school_id 外键（`high_school_ids`，供升学路径页跳转） | 自招 56 校区 / 特长生 72 校区 / 名单 116 高中 |

> 历史说明：第一批"资格名单计数矩阵"（每所初中升入各高中的资格人数）已废弃删除——初中第一批模块与高中第一批覆盖初中表均于 2026-09 移除，前端不再消费；`build_special_matrix.py` 不再输出 `matrix` 键，仅保留计划数与名单外键。资格名单原始计数仍可经 `build_ranking_middle.py`（初中升学信号"自招人数"列）回溯 `raw/autonomy/autonomy_qualify_2026.json`。

校验：`quota_matrix.json` 列和已强校验 0 不一致（col1 省市属名额 = Σ21 校区列）；10 所民办 `sheng_quota=None` 为不参与省市属名额分配，非缺失。特长生计划总量已硬校验=官方口径（体育 1905 不含领军龙 / 艺术 1741 / 领军龙 116）。

## 政府源文档（raw/）

| 文件 | 官方来源 |
|---|---|
| `raw/quota_detail.pdf` + `quota_detail.html` / `quota_summary.html` / `quota_result_notice.html` | 2026 名额分配结果（全市 31 页） |
| `raw/batch2_scores.pdf` | 2026 第二批次录取分数原表（304 页） |
| `raw/haizhu_quota.pdf` | 海珠区名额分配 |
| `raw/autonomy/autonomy_qualify_2026.json` | 2026 自主招生资格名单（按考生，用于初中升学信号"自招人数"计数） |
| `raw/autonomy/plan_2026.json` | 2026 自主招生计划数汇总（56 校区，`autonomy_plan` 来源） |
| `raw/special/附件1.2026年体育艺术类特长生布局项目及计划学校明细表.docx` | 2026 特长生计划官方明细（110 校，`build_special_plan.py` 输入） |
| `raw/special/plan_special_2026.json` | 特长生计划解析产物（`special_plan` 来源） |
| `raw/special/sports_2026.json` / `arts_2026.json` | 体育/艺术特长生通过专业测试名单（构建 `high_school_ids` 名单集合） |
| `raw/quota_grid_final.json`、`raw/schoolnames.json`、`raw/headers/header_ocr*.json` | 名额分配网格解析中间结果与人工确认的列序证据 |

> 已清理（2026-09）：第一批官方原始下载件（资格名单 PDF/zip、特长生测试名单 PDF/zip、申诉 docx、notice.html）无任何脚本引用，JSON 已固化，原件删除；生产脚本保留。

## 复现管线（scripts/linkage/）

```bash
# 名额分配矩阵：渲染 PDF → 列网格 OCR → 校名 → 组装
python3 scripts/linkage/parse_quota_grid5b.py    # quota_detail.pdf → quota_grid_final.json
python3 scripts/linkage/ocr_schoolnames.py        # → schoolnames.json
python3 scripts/linkage/assemble_quota.py        # grid + schoolnames → quota_matrix.json

# 第二批次上岸分数
python3 scripts/linkage/parse_batch2.py          # batch2_scores.pdf → batch2_scores_all.json
python3 scripts/linkage/build_linkage_batch2.py   # 过滤省市属 → batch2_scores.json

# 第一批招生（自招计划 / 特长生计划 / 名单外键）
python3 scripts/linkage/build_special_plan.py    # 附件1 docx → plan_special_2026.json（内置小计硬校验）
python3 scripts/linkage/build_special_matrix.py  # 名单 + 计划源 → special_matrix.json
python3 scripts/linkage/build_ranking_middle.py  # autonomy 资格名单 + quota_matrix + levels → ranking_middle.json
```

历史迭代脚本（v2–v12、各 fix 轮、早期 OCR 实验）归档在 `scripts/linkage/_archive/`，仅作留痕，不再维护。

## 名额分配矩阵 OCR 方案记录（2026-09-15 重建）

#### 名额分配矩阵 OCR 方案记录（2026-09-15 重建）
真源 `data/linkage/raw/quota_detail.pdf`（官方 31 页，无文本层，带灰色水印）。以下为踩坑与最终方案记录，避免重蹈覆辙。

**最终采用（成功）方案**：整页 200 dpi 渲染（`/tmp/qpage/p*.png`）+ 视觉识读（Read 整页图），逐格/逐列裁剪复核疑点（600–900 dpi）。权威三列值落盘为 `scripts/linkage/quota_vision_values.py`（P[页码][行]=[考生,省市,区属]，含番禺两条缺行），由 `scripts/linkage/rebuild_quota_matrix.py` 重建 `data/linkage/quota_matrix.json`（503 校，11 区）。已校验：10/11 区级合计与官方区头精确一致；天河省市行和 554 vs 区头 555 差 1，四路独立复核一致，判定为官方原表口径差。

**已弃用（失败）方案与原因**（脚本已删除，仅留此记录）：
1. tesseract 5.5.3（白名单数字 + psm 6/7/8 × 阈值 × 放大）——裁剪小图全部空读；
2. Swift Vision 整行 600 dpi——相邻格数字被合并成单个文本块，列归属失败；
3. Swift Vision 逐格裁剪（v6/v6fix）——部分页 grid 列坐标偏移致逐格错位（荔广省市"8"空读、番中实验"27"读成"391"），多数省市窄格空读；6↔9 混淆在区级合计中互相抵消，"区级对齐即定稿"的裁决贪心不可靠（adjudicate_quota.py 已否决）；
4. 阈值二值化去水印——打丢淡色数字（真光区属 335）；
5. 整行 OCR 对区属列系统性 6↔9 误读（荔广 249、培正矿泉 128 根因）。

**保留/删除说明**：`data/linkage/raw/quota_grid_final.json`（整行 OCR 网格）仅保留其 sz 高中分额列供补行使用，三列（考生/省市/区属）作废；`schoolnames.json` 为校名源保留；其余 OCR 中间产物（v6/v6fix/adjudicated/_ocr/headers）与失败脚本已删除。

**已知残差**：番禺补行"广东第二师范学院广州南站附属学校 / 番禺附属初级中学"的 sz 高中分额明细暂缺（sz_sum=0，见 quota_matrix.json note）。

**2026-09-15 复核修复**：
1. **番禺铁一校名错位**：官方 p18 序号 49「广州铁一中学（番禺校区）」(266/14/73) 曾被 schoolnames 读残缺为"广州市铁"（榜单显示"铁"）；序号 50「广州大学附属中学（番禺校区）」(557/29/154) 被 NAME_FIX 误改名为"广州市铁一中学（番禺校区）"，造成铁一/铁英"重复"假象。已修正 NAME_FIX：`(18,9)='广州铁一中学（番禺校区）'`、移除 `(18,10)` 误改；school_id 对应 entities 番禺铁一(97e0acaa) 与广大附中大学城(8f5e4721)。
2. **school_id 修正（SID_FIX）**：7 所 quota 行此前为 md5 生成/误配的假 id，导致民办 Badge 漏标（华立/海龙博雅/爱莎文华/同仁实验/东风）与详情页 stage 错乱。已按 entities 名/别名核对修正：华立→gz-440105-8371ce9c、海龙博雅→gz-440103-957da59e、爱莎文华→gz-440103-5143f5a1、同仁实验→gz-440106-77787b4a、东风→gz-440106-24ff78f9、黄埔铁英→gz-440112-c80ac6ac、番禺丽江→gz-440113-2264148c。民办 Badge 99→104。
3. **详情页学部覆盖核查（334 校模拟 buildDetailModel）**：含初中部（middle）315 所；仅小学部 8 所（海龙博雅/知用/天河华实/培智/东风/省教院黄埔实验/祈福新邨/番禺金华）；仅高中部 6 所（爱莎文华/为明/奥林匹克/华美/开元/苏元）；无任何点位 5 所（华立/江高二中/三元里/南悦/二师南站附属）——后两类属 POI/实体数据缺口，未修。
4. **详情页跳转/自招数据修复（2026-09-15 第二轮）**：
   - 榜单链接统一加 `stage=middle`：从初中明细跳详情页默认打开初中部（修复祈福新邨/新英豪等 93 所九年制学校默认落小学部）。
   - 祈福新邨 school_id 修正：`1963cc5e`（小学实体）→ `8ef59a4c`（初中实体/初中 POI），详情页从"祈福新村小学"改为初中部（自招 185 人正常显示）。
   - 详情页自招补充：tier1（口碑校 54 所）未覆盖的初中，从 `rankingMiddle`（2026 官方自招资格名单）补充"自主招生"行（`官方资格名单`标注）。共修复 180 所（清单 `outputs/detail_autonomy_gap_20260915.csv`）；另有 10 所 aut>0 但详情页无初中 tab（POI 点位缺口，未修复）。
5. **数据治理（2026-09-15 第三轮，按用户 5 条批评重构）**：
   - **school_id 解析重构（废除 SID_FIX）**：`rebuild_quota_matrix.py` 内置通用匹配器 `SidResolver`（区 + 名字/别名，norm 全等 3 → pynorm 2 → core 1 → 前缀 0.5，学部分层 middle→primary→high，歧义同区消歧，有效旧 id 沿用保护），实体表变更后重跑脚本自动联动，不再点对点打补丁。
   - **实体表治理（数据源修复，联动生效）**：删海珠知用 `934833e1`、越秀协和 `1b1d2659` 两条错区重复记录；补录三元里中学（在办未收录 → `gz-440111-a20eb9b6`，旧 md5 占位自动升级为实体）、协和 middle、海龙博雅/爱莎文华/知用 middle 学部记录；奥中本部初中实体（黄村西路校区）补别名；祈福实体/POI 名"祈福新邨"→"祈福新邨学校"。由此自动修复：西关培英（原误挂四中丰宁 `3b870a8e`→`d78c848a`）、协和（→`e281e7d0`）、奥中（→`d40d0dbe`）、三元里（→`a20eb9b6`）、天健/开元/省教院黄埔实验/金华等错区或错学部 id。匹配器另加"中学↔小学 core 交叉防护"与"九年一贯"学段。复核：7 区 334 所 quota 校 school_id 全部命中实体且含初中 stage（仅二师南站附属保持 md5 占位，POI 缺口）。
   - **祈福地图点位修正（问题 2）**：middle POI `8ef59a4c` 原为住宅片区名"祈福新邨"、坐标 (113.329043, 22.961537)，改为"祈福新邨学校"、坐标 (113.322074, 22.962704)（与小学 POI 同址，学校建筑真实位置）。
   - **升学信号源纠正（问题 3）**：tier1 只做学校信号（`formatMiddleSignals` 移除"自主招生"行）；详情页"自主招生"行一律取 `linkage/ranking_middle.json`（官方自招资格名单），标注"官方资格名单"。
   - **铁一番禺自招=0（问题 4）**：quota 名"广州铁一中学（番禺校区）"与官方名单"广州市铁一中学（番禺校区）"差"市"字，norm 去括号撞多校区返回 0；`AUT_ALIAS` 归一 → 109。
   - **广大附两校区"65"（问题 5，数据澄清）**：初中自招按校区正确（番禺 131 / 越秀 80，官方资格名单）；"65"为大学城初中"中考-第一批"升入广大附高中自招资格 65 人 + 广大附高中部 2026 自招计划 65 人（官方法人统一计划，两校区高中页面共用同一份第一批/第二批招生表），已在该表头加注"高中部招生计划按法人单位统一公布，多校区共用同一计划"消除误导。
   - **广大附"65"复核修正（2026-09-15 第四轮，按用户查证）**：上轮"高中自招计划 65"表述有误，更正如下——
     1. **官方招生单位不分校区，但办学地点在大学城**：官方 2026 高中招生（招生总计划 812、自招计划 **102**、名额分配 406、第三批录取线 732/738、自招资格名单 461 人）全部以法人"广州大学附属中学"一个单位发布（gzzk 官方汇总表/录取表原文）。黄华路校区自 2017 年起为**纯初中部**（高中部全在大学城校区，官方多来源佐证），故"65"与高中招生无关。
     2. **65 的真实口径**：番禺校区（大学城）初中升入广大附中高中的**自招资格人数**（官方资格名单：番禺 65 / 越秀 24），是"中考-第一批"表的数据，不是高中招生计划。
     3. **数据根修正（非点对点）**：黄华路高中 POI（data/poi/dist/high_poi.json）删除；实体 b22c4eca 撤销 high 学部、移除法人名别名（法人名"广州大学附属中学"改挂大学城实体 8f5e4721，官方分数 scores 2025/2026 改挂 8f5e4721）；levels 广大附中 district 越秀→番禺。由此高中明细只剩"广州大学附属中学(大学城校区)"一行（番禺区），黄华路详情页只剩初中 tab，任何官方名单名跳转均落大学城高中。上轮临时加的 findExactLoose / resolvePoiName 多校区规则 / 高中行归并三处复杂逻辑已全部回退，保持代码简单。

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
