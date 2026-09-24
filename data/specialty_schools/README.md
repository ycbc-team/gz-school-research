# 特色学校认定采集（data/specialty_schools/）

省市各级特色校认定数据（科创 / 美育 / 体育 / 心理等），具体到学校，供学校画像与
`gz_school_research` 研究使用。认定名单均为官方公开通知/附件（省教育厅、市教育局、
教育部），逐校提取，不合并去重：同一学校被多个类别/级别认定时保留多行。

## 目录分层

| 目录 | 内容 |
| --- | --- |
| `raw/` | 政府源数据留底（PDF/xls/xlsx/docx/txt 官方名单与附件）；按来源分 `gd_edu/`（省教育厅）、`moe/`（教育部）；中间渲染图（页面截图等）不保留 |
| `parsed/` | 规范 JSON（唯一真源）：对 raw 官方名单解析后的逐校记录，字段见下 |
| `scripts/` | 解析/构建脚本（`csv_to_parsed.py` 一次性迁移、`build_specialty.py` dist 编译、`export_xlsx.py` 交付导出、`build_*.py` 采集期生成脚本） |
| `dist/` | 运行时编译产物 `specialty_schools.json`（体积压缩版，2026-09-20 二版）：recognition 池 + 学校聚合，见"dist 格式" |
| `README.md` | 本文件，业务进展追踪 |

parsed 记录字段：`school / district / category / level / batch / year / project（认定项目全称）/
issuer（发文单位）/ url（官方来源）/ remark（区推断等备注）`。

## 已采集（2026-09-20 快照）

共 **538 条认定 → 397 所学校**（dist 编译：254 所已挂 school_id，143 所未匹配，见"缺口"）。

| 类别 | 级别 | 批次/年份 | 条数 | 说明 |
| --- | --- | --- | --- | --- |
| 美育/艺术教育 | 省级 | 首批(2018)/第三批(2020)/第四批(2021)/第五批(2022) | 65 | 广东省中小学艺术教育特色学校 |
| 中华优秀传统文化传承 | 省级 | 首批(2020)/第二批(2021)/第三批(2022) | 40 | 广东省中华优秀传统文化传承学校 |
| 美育/艺术教育 | 市级 | 首批（2026） | 30 | 广州市中小学学科美育教学改革试点项目校 |
| 心理健康教育 | 市级 | 第五批(2020)/第六批(2023)/第七批(2025) | 97 | 广州市中小学心理健康教育特色学校 |
| 科技创新/科学教育 | 国家级+省级 | 首批全国科学教育实验校(2024)、首批省科学教育示范/实验校(2024) | 49 | 含全国中小学科学教育实验校、广东省中小学科学教育示范区/示范校/实验校 |
| 科学特色（高中多样化试点） | 省级 | 首批（2025） | 6 | 2026 年广东省普通高中多样化特色发展改革试点·科学特色 |
| 体育 | 国家级+市级 | 冰雪体育首批(2023)、校园足球 2015/2023/2024/2025、篮球2017 | 251 | 含广州市青少年校园冰雪体育传统特色学校（49，市级）、全国青少年校园足球/篮球特色学校（202，脚本解析） |

## parsed 文件清单

| 文件 | 条数 | 类别 |
| --- | --- | --- |
| `gd_arts_tradition.json` | 105 | 省级美育/艺术教育 + 中华优秀传统文化传承 |
| `gz_mental_health.json` | 97 | 市级心理健康教育 |
| `gz_meiyu_pilot.json` | 30 | 市级学科美育教学改革试点 |
| `science_tech.json` | 49 | 国家级/省级科技创新/科学教育 |
| `gd_science_high.json` | 6 | 省级科学特色高中试点 |
| `sports.json` | 251 | 体育（冰雪49 + 足球/篮球202，足球/篮球为脚本解析） |

## 解析过程化改造（2026-09-20，三轮）

针对"脚本直接写结果、没有过程"的评审意见，把体育/PDF 来源改为**可复现的源文件解析**，
并补审计断言。三个脚本见 `scripts/`：

| 脚本 | 作用 | 结果 |
| --- | --- | --- |
| `parse_moe_sports.py` | 解析教育部 5 份名单文件（2015 xls / 2023 xlsx / 2024·2025 txt / 2017 docx）为广州学校；`--apply` 落库 sports.json，remark 带源文件 | 202 条脚本化；**发现硬编码漏掉"广东番禺中学"（2017 篮球名单序号 1213）**，已补入；2015 批 79 所"待核对·无法确定市"以实体表交叉确认省属校（省实/华师附中/广大附中）归穗 |
| `parse_gd_edu_pdf.py` | 解析省厅 3 份 PDF：p1/p2 文本型用 `pdftotext -layout` 提取；p3 为 21 页扫描件，用 pymupdf 渲染 + `tesseract chi_sim` OCR（psm=4）。输出 `scripts/out/gd_edu_pdf_parsed.json` 并与 parsed 对比（OCR 错字经"主体一致/1字错字/2字错字"三级模糊校对） | 5 批次（首批艺术 10/第二批传承 22/第三批传承 12/第四批艺术 26/第五批艺术 9）全部与 parsed 一致；OCR 批次暴露的错字均被校对解释 |
| `audit_specialty.py` | 五类断言：批次数量（19 项）、字段完整性、URL 域名与签发机构、PDF 源一致性、dist 覆盖 parsed | 全部通过；9 项媒体/官网转载 URL 记 WARN |

**处理方式的说明**：子代理第一轮采集时把 PDF 渲染成图片后**纯视觉读图**（无 OCR 脚本），只沉淀结果、
不留过程。本轮改为 pdftotext/OCR 脚本化提取 + 模糊校对 + 断言，任何一步可重跑、差异可见。

**审计实际发现并修复的问题**：
1. 体育 2017 篮球名单**漏校"广东番禺中学"**（硬编码遗漏，脚本解析纠正）；
2. 冰雪体育批次 issuer 错标"广东省教育厅"（实际为广州市教育局公布，URL 为 jyj.gz.gov.cn）→ 已修正 49 条；
3. OCR 扫描件局限：第二批/第四批错字（番禺→番遇/秋遇/竺遇、槎龙→楼龙、邝维煜→闻维爆 等）经模糊校对全部解释；
   **越秀区铁一小学** OCR 未检出，已视觉核验确在官方名单（第四批艺术序号 22），parsed 保留；
4. 9 个 URL 为媒体转载/官网转载（南方网、大洋网、中新网、华师附中官网、越秀区政府网、广东教育 cnts.gov.cn），
   非一手官网域名，记 WARN 并在下方"来源"中标注（science_tech 与 gd_science_high 尤其依赖媒体源，建议后续补官网一手链接）。

## 来源（raw/ 对应文件与官方入口）

- 广东省教育厅（edu.gd.gov.cn）：
  - 首批艺术教育特色学校名单（`raw/gd_edu/p1_art_first.pdf`）
  - 第三批中华优秀文化传承+第五批艺术教育特色学校（`raw/gd_edu/p2_trad_art5.pdf`）
  - 第二批中华优秀文化传承+第四批艺术教育特色学校（`raw/gd_edu/p3_trad2_art4.pdf`）
  - 2026 高中多样化特色试点公示（广州日报转载 [链接](http://news.dayoo.com/gzrbrmt/202511/14/170639_54894231.htm)）
  - 首批广东省中小学科学教育示范区/示范校/实验校公示（2024-10）
- 广州市教育局（jyj.gz.gov.cn）：
  - 第七批心理健康特色校 [通知](https://jyj.gz.gov.cn/gk/zfxxgkml/bmwj/qtwj/content/post_10196843.html)（2025-04）
  - 第六批心理健康特色校 [通知](https://jyj.gz.gov.cn/yw/tzgg/content/post_8938203.html)（2023-04）
  - 首批学科美育试点项目校 [通知](https://jyj.gz.gov.cn/gkmlpt/content/10/10807/mpost_10807656.html)（2026-05）
  - 冰雪体育传统特色学校名单（[PDF](https://jyj.gz.gov.cn/attachment/7/7517/7517371/9357006.pdf)）
- 教育部（moe.gov.cn，经官方名单文件落盘 `raw/moe/`）：校园足球特色学校 2015/2023/2024/2025 各批次、篮球特色校 2017 批次、首批全国中小学科学教育实验校（2024）。

## dist 格式（二版，体积压缩）

- `recognition[]`：唯一认定池（category/level/batch/year/project/issuer/url 去重），537 条认定 → 26 条，学校仅存索引复用文本；
- `schools[]`：每校一条 `{ school, ids[], stage[], rec[池索引], notes?[] }`；`stage` 来自 POI 分层（小学/初中/高中，多学段全挂），`ids` 为空 = 未匹配，`notes` 按认定索引保留逐条备注（`g`=未匹配原因，`t`=源备注）；
- 消费端展开：`recognition[rec[i]]` 即该认定全字段。

## 匹配规则（dist 编译）

- 学校名统一走项目 `SchoolMatcher`（`scripts/registry/school_match.py`），不维护局部字符串规则。
- 名单带区属 → `preferred_adcode` 收窄（school_id adcode 与官方区属一致）；不带则全学段/全区匹配。
- 特色校名单不分学段 → 不传 `preferred_stage`，小学/初中/高中 POI 全匹配，多校区/多学段 school_id 全挂。
- 非学校（少年宫/青少年宫等）在采集期已排除。

## 匹配修复记录（2026-09-20，二轮）

别名一律通过生产脚本 `scripts/registry/build_entities.py` 的 `AWARD_SOURCE_ALIAS`
常量配置后重跑生成（`entities.json` 为构建产物，直接改会被覆盖）；`parsed` 区属与
实体实际区属不符时修正 parsed 并留备注。

| 学校 | 问题 | 修复方式 |
| --- | --- | --- |
| 广州市八十六中学 | 官方名单写法缺"第"字 | `AWARD_SOURCE_ALIAS` 加 `middle`、`high` 两学段别名「广州市八十六中学」 → 广州市第八十六中学（gz-440112-0cb5a402） |
| 广州市协和中学 | 区属错标白云区（实际荔湾区） | parsed 区属修正为荔湾区 + `AWARD_SOURCE_ALIAS` 别名 → 广州协和学校中学实体（gz-440103-e281e7d0） |
| 广州市协和小学 | 第一轮错挂到中学实体（gz-440103-e281e7d0） | `AWARD_SOURCE_ALIAS` 别名改挂小学部实体 广州市协和学校（小学部）（gz-440103-33b32c4c） |
| 广州市启明学校 | 第一轮错配到白云民办启明小学（gz-440111-2abc753d） | 撤销匹配：启明学校为公办特教盲校（主校区天河区天平架），POI 层未收录，保持未匹配并在 parsed 备注说明 |
| 广州协和学校（校园足球） | 区属错标白云区（实际荔湾区） | parsed 区属修正为荔湾区 |

修复后匹配率 254/397（64.0%），未匹配 143 所。dist 二版（recognition 池化）后 309KB → 123KB，compact 后约 40KB。

## 缺口与待办

1. **未匹配 143 所**（`dist` 中 `ids` 为空的学校，原因见各条 `notes[].g`），原因分类：
   - **远郊区POI覆盖缺口（约123所）**：花都/南沙/增城/从化的小学POI为0所、初中各仅1所、高中南沙仅1所，是未匹配主因；
   - **职业/师范学校（约10所）**：城市建设职校、财经商贸职校、交通运输职校、轻工职业学校、信息技术职业学校、白云行知职校、从化职校、幼儿师范学校等，POI层仅覆盖中小学；
   - **中心区POI遗漏（约5所）**：美术中学、第四十四中学、工业大道中小学等；
   - **民办/新办学校（约4所）**：广外附设外语学校、湖南师大黄埔实验学校等；
   - **特殊教育/体校（约2所）**：启聪学校、净慧体校。
   以上未匹配学校已在 parsed 备注中标注"未匹配registry（原因）"。
2. **来源一手性缺口**：science_tech（全国科学教育实验校等）与 gd_science_high（高中多样化试点）的
   9 个 URL 为媒体转载（南方网/中新网/大洋网/华师附中官网等），名单内容来自官方公示但非官网一手链接，
   建议后续到 moe.gov.cn / edu.gd.gov.cn 补官网附件。
3. **待补充批次**：
   - 省级艺术教育第二批（2018年11月，官方PDF未获取）；
   - 市级心理健康第一至四批（约2015-2019，官网历史归档不可查）；
   - 国家级校园足球2016-2022批次（广州累计371所，本次覆盖约47%）；
   - 国家级体育传统特色学校（广州435所，完整名单未找到）；
   - 省级/市级体育传统项目学校（完整名单附件未找到）；
   - 市级科学教育特色学校（计划100所，首批名单尚未公示）；
   - 劳动教育特色学校、全国中小学心理健康教育特色学校等。
4. 后续新增数据：政府源文件放 `raw/`，解析结果直接写 `parsed/*.json`（或先写 CSV 再跑
   `scripts/csv_to_parsed.py` 迁移），最后 `python3 data/specialty_schools/scripts/build_specialty.py`
   重新编译 dist，并 `python3 data/specialty_schools/scripts/audit_specialty.py` 跑审计。

## 专项示范/历史层级称号调研与采集路线（2026-09-23）

### 与项目已有数据的边界

“省重点/市重点/省市一级学校”属于历史办学层级信息；项目目前仅在
`data/primary|middle/tier1_schools_all.json` 中为部分学校保留，且 tier1 已判定待重构，
**不是**全量、独立的称号数据集。`specialty_schools` 中的科创、美育、体育、心理等为
专项认定，两者不应混同。

“国家级示范性普通高中 / 广州市示范性普通高中 / 省一级普通高中”也不能简单视作被专项
称号取代：它们仍是广州现行高中招生政策使用的类别（2026 年名额分配与自主招生均按此分类），
但只适用于**高中**，不应被用作小学、初中的通用强弱指标。完整名单由市教育局公开：
[广东省国家级、广州市示范性普通高中名单](https://jyj.gz.gov.cn/yw2/jyfw/gzjy/content/post_9644154.html)；
当前招生口径见[2026 年名额分配招生问答](https://gzzk.gz.gov.cn/gkmlpt/content/10/10787/mpost_10787238.html)。

因此后续按以下边界落库：

- **专项称号**（劳动、国防、体育、心理、科学等）继续写入本目录；同校多个项目或级别保留多条，
  不做跨项目去重。
- **高中层级称号**另建 `data/school_titles/`（建议），以 `school_id + 校区 + stage=high` 建模；
  迁移/替代 tier1 中零散的 `historical_titles` 与 `demonstration_high`，避免在本目录重复存放。
- 历史“重点/一级”仅标注为 `historical`，不得与现行专项认定或招生资格混算。

### 专项项目 backlog（按价值与可采集性排序）

| 优先级 | 项目与范围 | 与当前数据关系 | 官方入口 / 采集提示 |
| --- | --- | --- | --- |
| P0 | 广东省中小学劳动教育特色学校（首至三批）；广州市中小学劳动教育特色学校 | **完全缺失** | 省第三批正式名单见[省厅附件](https://edu.gd.gov.cn/attachment/0/568/568320/4637868.pdf)；市 2021 年公告有特色校 67 所、试点校 52 所、基地校 15 所，附件 ZIP 见[市教育局公告](https://jyj.gz.gov.cn/yw/wsgs/content/post_7813653.html)。先采“特色学校”，试点/基地另存状态。 |
| P0 | 全国中小学国防教育示范学校、广东省国防教育特色学校 | **完全缺失** | 教育部 2017 年全国名单见[正式通知](https://www.moe.gov.cn/srcsite/A17/moe_1061/s3289/201802/t20180201_326312.html)；省级项目的广州推荐流程与条件见[市教育局通知](https://jyj.gz.gov.cn/gkmlpt/content/7/7800/post_7800693.html)，需继续追溯省厅最终认定名单。 |
| P0 | 国家级体育传统特色学校、校园足球 2016–2022 批次及篮球/排球/冰雪历史批次 | **同项目补全，非重复** | 当前体育仅覆盖足球 2015、2023–2025 和篮球 2017；市教育局披露 2015–2025 广州累计 371 所足球特色学校，说明仍有明显缺口（[统计](https://jyj.gz.gov.cn/gkmlpt/content/10/10761/post_10761294.html)）。教育部 2020 批同时发布篮球、排球、冰雪名单（[通知](https://www.moe.gov.cn/srcsite/A17/moe_938/s3273/202011/t20201118_500605.html)）。 |
| P1 | 全国中小学心理健康教育特色学校 | 与现有**市级**心理特色校不同级别，**不重复** | 教育部保留首、二批正式名单入口（[名单页](https://www.moe.gov.cn/jyb_xxgk/xxgk/neirong/fenlei/sxml_jcjy/jcjy_dyyxwjy/dyyxwjy_tsxxmd/)）；按批次下载附件并筛广州。 |
| P1 | 广州市科学教育特色学校、科技高中 | 与已采集的国家/省级科学教育认定不同，**不重复** | 市行动方案规划创建 100 所并实行动态调整、每 3 年复评（[行动方案](https://jyj.gz.gov.cn/gkmlpt/content/9/9591/post_9591730.html?jump=true)）。在找到“公布/认定”正式名单前，仅登记为待监测，不把计划或申报学校当作已认定。 |
| P2 | 广东省绿色学校 | **完全缺失**，但区分度低 | 广州已认定 1218 所（[市教育局挂牌通知](https://jyj.gz.gov.cn/gkmlpt/content/8/8127/post_8127809.html)）。如采集，只作“环保/校园治理”弱标签，不纳入特色强度排序。 |

### 统一采集与数据质量规则

1. **以最终认定为准**：来源优先级为教育部、省教育厅、市教育局的正式“公布/命名/认定”页和附件；
   公示、申报、推荐、试点、基地必须保留相应状态，不能写成正式认定。区教育局和学校官网只作补证，
   不作为唯一名单源。
2. **原件与字段**：原件按签发机构存 `raw/<issuer>/`；逐校写 `parsed/*.json`。新增记录至少具备
   `school / district / stage / category / level / batch / year / project / issuer / url / status`；建议再加
   `source_type`（正式公布/公示/申报）与 `validity`（长期、待复评、已退出、未知）。
3. **名称与校区**：仍统一走 `SchoolMatcher`；名单明确校区、学段时必须传入，九年制、完全中学不可
   仅凭校名把称号无差别挂到全部学段。无法确定适用校区时保留未匹配及原因，不猜测。
4. **构建前核验**：每完成一个项目，先审查“广州筛选数 = 官方附件广州行数”、字段完整性、正式来源
   URL、与既有 `project + batch + school` 的重复；随后运行本 README 的审计、构建和导出命令。

## 更新方式

```bash
# ① 体育名单（教育部 xls/xlsx/docx/txt）→ sports.json（--apply 落库，先不带参数看对比）
python3 data/specialty_schools/scripts/parse_moe_sports.py [--apply]

# ② 省厅艺术/传承 PDF → scripts/out/gd_edu_pdf_parsed.json + 与 parsed 对比（含 OCR，较慢）
python3 data/specialty_schools/scripts/parse_gd_edu_pdf.py

# ③ 审计断言（数量/字段/URL/PDF源/dist，失败退出码 1）
python3 data/specialty_schools/scripts/audit_specialty.py

# ④ 迁移采集期 CSV → parsed（新数据同样走此流程）
python3 data/specialty_schools/scripts/csv_to_parsed.py

# ⑤ 编译 dist（parsed → school_id 聚合）
python3 data/specialty_schools/scripts/build_specialty.py

# ⑥ 导出交付 xlsx（outputs/广州特色校认定汇总_YYYYMMDD.xlsx）
python3 data/specialty_schools/scripts/export_xlsx.py
```
