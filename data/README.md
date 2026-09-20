# 共享数据层

多端共用的数据快照（web 应用、微信小程序等均从此目录读取，避免各自维护）。

## 数据治理约定（重要）

- **本目录只存放 JSON，是唯一数据真源（source of truth）。** 任何端（Web / 小程序）
  都应消费这里的 JSON，不在应用内复制或二次维护数据。
- 历史教训：js/json 双份曾出现脱同步（如小学点位 js 为清洗后 915 所、json 仍为 971 所），
  已回填对齐并彻底移除 js 兼容产物；今后只改 JSON，Web / 小程序构建时按需生成产物。

按学段分子目录，小学与初中数据互不干扰：

| 目录 | 学段 | 主要文件 |
| --- | --- | --- |
| `primary/` | 小学 | `tier1_schools_all.json`（第一梯队核验）、`enrollments/`（2026 招生数据）；点位见 `poi/` |
| `middle/` | 初中 | `tier1_schools_all.json`（初中第一梯队核验）；点位见 `poi/` |
| `high/` | 高中 | `level/src/levels.json`（学校清单/分类/指标）；`cutoff_score/`（录取分：`dist/` 历年产物 / `raw/` 官方源页面 / `src/` 手工源 / `scripts/` 解析脚本）；点位见 `poi/` |
| `poi/` | 跨学段 | `dist/primary_poi.json`（931 所）/ `dist/middle_poi.json`（475 所）/ `dist/high_poi.json`（清洗后 126 所）；采集脚本在 `poi/scripts/` |
| `registry/` | 跨学段 | `education_groups_2026.json`（招考办 2026 集团名额分配表，43 核心校/118 成员）、`brand_groups.json`（8 品牌组成员清单，含法人关系/来源 URL）、`sites.json` |

## 坐标系

所有点位均为 **GCJ-02**（高德坐标系），与高德地图瓦片一致，无需转换；微信小程序内置
`<map>` 组件同样使用 GCJ-02，可直接使用。

## 数据源

高德地图 Web 服务 API（place/text 分类查询 + 翻页采集 + config/district 区边界），快照日期见各文件 `updated` 字段。

## 更新方式

```bash
# 小学
python3 data/poi/scripts/fetch_schools.py         # 小学点位采集（写 data/poi/dist/primary_poi.json）
python3 data/poi/scripts/backfill_schools.py      # 番禺招生未匹配点位回填（写 data/poi/dist/primary_poi.json + 留痕）

# 初中
python3 data/poi/scripts/fetch_middle_schools.py # 初中点位采集（写 data/poi/dist/middle_poi.json）

# 高中
python3 data/poi/scripts/fetch_high_schools.py   # 高中原始采集（写 data/poi/dist/high_poi.json）
python3 data/poi/scripts/build_high_levels_js.py # 高中清洗点位（写回 data/poi/dist/high_poi.json 真源）
python3 data/high/cutoff_score/scripts/build_scores.py # 高中录取分解析（官方页 raw/ → dist/scores_{year}.json 真源）

# 招生
python3 scripts/primary/build_district_enrollment.py   # 2026 招生（写 data/primary/enrollments/*.json 真源）
```

密钥仅存于项目根 `.env`（`AMAP_WEB_KEY`），代码与页面不出现明文凭据。

## 新校核对流程（2026-09-10 起强制）

新开办学校的完整性校验**不能只依赖高德分类抓取快照**（新校高德收录滞后、九年制/完全中学分类不稳定会导致 POI 层漏抓），必须按以下流程核对并补录：

1. **强制校验源（每年开学季先取这两个基准）**
   - 广州市政府门户年度新开办中小学校清单（如 2026-08-27《广州9月新开办中小学校(校区)24所》https://www.gz.gov.cn/zwfw/zxfw/jyfw7/content/post_10979972.html ）
   - 各区教育局/区政府新校批复与发布（如番禺区政府 https://www.panyu.gov.cn/zwgk/zfxxgkml/xxgkml/zwdt/fzxw/content/post_10250808.html ）；批复链接失效时以权威媒体转引作来源
   - 补充：南方+/广州日报/信息时报/新快报等开学季"上新"盘点
2. **逐校核对**：新校名 → 开学年份 → 学段（小学/初中/九年制/完全中学）→ 在 `primary/`、`middle/` POI 层的覆盖状态；九年制/十二年制学校按实际开办学段补入对应层（未开办学段不补，如华中师大白云学校初中部 2027 才开，2026 只补小学层）
3. **坐标与事实必须有来源**：坐标一律取高德 Web 服务 API（place/text 或 geocode/geo，GCJ-02），禁止编造；道路级/配建地块级/兴趣点级精度差异在清单中注明；高德未收录的新校不强行补点，标注"待高德收录"
4. **补录口径**：补录点位写入对应学段 `data/poi/dist/*_poi.json` 的 `schools[]`，条目加 `note: "新开办（年份）·待首届成绩"`（无成绩新校不入口碑名单，`tier1_eligible` 判定不动）
5. **留痕**：每轮核对产出 7 区清单（见 `docs/new-school-checklists/`），记录官方来源 URL/开学年份/学段/POI 状态/是否补录/品牌归属/待成绩标记

## 教育集团 Registry（registry/）

跨学段的教育集团名录与品牌组成员清单，供详情页「品牌关联」板块与覆盖核对使用。

### `education_groups_2026.json`
- 来源：广州市招考办《2026年广州市成立教育集团的示范性普通高中面向集团的直接名额分配情况》（2026-05-12，http://gzzk.gz.gov.cn/gkmlpt/content/10/10809/post_10809470.html ）
- 内容：43 个集团核心校（省市属 7 + 区属 36）、118 条集团内初中成员关系
- 局限：仅含「示范性高中 + 集团内初中」口径；小学段成员与区属非示范集团不在表内

### `brand_groups.json`
- 用途：详情页「品牌关联」板块数据源，列出 8 个重点品牌组（清华附中湾区/广铁一中/省实/广雅/执信/二中/广大附/华附）的校区与独立法人成员校
- 字段：`units[].name`（规范校名）、`role`（角色说明）、`legal`（same=同法人 / independent=独立法人 / entrusted=托管共建）、`poi_names`（POI 名别名，用于全等匹配）、`source_url`（官方来源 URL）
- P2 核实（2026-09-10）：8 品牌组经官网/招考办/区政府文件/主流媒体交叉核实，新增 25 个成员单位，全部附来源 URL + 法人关系标注

### 教育集团齐全化任务状态
- **P0（已完成）**：招考办 2026 表落盘 `education_groups_2026.json`
- **P1（已完成）**：161 校覆盖比对，产出 `docs/education-groups-coverage/集团成员覆盖清单_P1.md`（精确命中 49 / 变体命中 45 / 7 区内真实缺失 2 / 远郊不在范围 65）
- **P2（已完成）**：8 品牌组官方来源交叉核实，写回 `brand_groups.json`（新增 25 成员，单测 12/12 通过）
- **P3（未完成）**：区属非示范集团 + 小学集团全量按各区文件补录
- **P4（未完成）**：年度更新机制（每年 5 月招考办新表发布后刷新）

## 数据依赖链（2026-09-20 记录）

数据流总览：**源头（外部抓取/官方转录/人工）→ 构建脚本 → data/ 产物 → compact.mjs 编译 → Web/小程序运行时**。全链以 school_id 外键关联，`registry/entities.json` 是唯一维度表枢纽。

### 源头层（无上游脚本写入 = 真源）

| 类型 | 文件 |
| --- | --- |
| 外部抓取（高德 API） | `poi/dist/primary_poi.json`、`poi/dist/middle_poi.json`、`poi/dist/high_poi.json`（fetch_* 脚本直写） |
| 官方转录 | `primary/enrollments/2026-*`（小学招生计划）、`linkage/raw/*` + `primary/enrollments/_raw/*`（指标/自招/录取线/招生名单转录）、`high/cutoff_score/dist/scores_{2025,2026}.json`（官方录取分） |
| 人工产物 | `primary|middle/tier1_schools_all.json`（学校信号，已判废弃待重构）、`high/level/src/levels.json`、`middle/org_sort/src/*`、`registry/brand_groups.json`、`registry/education_groups_2026.json`、`registry/_partial_*`、`registry/source_name_mappings.json`、`registry/minban_schools.json` |

### 派生层（脚本产物，勿手改；改脚本须重跑并提交）

| 产物 | 生产脚本 | 下游 |
| --- | --- | --- |
| `registry/entities.json` | build_entities.mjs | 全链 school_id 外键维度表 |
| `registry/sites.json` | build_sites.py | 高中点位/实体 |
| `primary/enrollments/xiaoshengchu_<区>.json` + `primary/xiaoshengchu_all.json` | build_xiaoshengchu_all.py + xs_resolver.py | 升学路线 |
| `primary/xiaoshengchu_2026.json`（facts） | upgrade_xiaoshengchu.mjs | 小学升学路线、初中生源反查（middlePrimaryFeed）、生源快照测试 |
| `primary/enrollments/middle_enrollment_2026_<区>.json` | build_middle_enrollment.py | 详情页初中招生计划 |
| `linkage/quota_matrix.json` / `special_matrix.json` / `district_quota.json` / `batch2_scores.json` | rebuild_quota_matrix / build_special_* / build_district_quota / build_linkage_batch2（+ backfill_school_ids 回填 id） | 升学通道、排行榜 |
| `linkage/ranking_middle.json`（334 校） | build_ranking_middle.py | 详情页升学信号、排行榜、初中明细 |
| `registry/education_groups.json` | merge_groups.py（合并 `_partial_*` + brand + education_groups_2026） | 品牌卡、初中明细分组 |
| `registry/school_groups.json`（纯 id） | build_school_groups.py（--write-brand 回写 brand_groups） | 品牌卡、初中明细分组（运行时纯 id 匹配） |
| `middle/org_sort/dist/compiled.json` | data/middle/org_sort/scripts/build_org_sort.py | 初中默认排序 |
| `primary/middle_feed_snapshot.json` | build_middle_feed_snapshot.py | 初中生源全量快照测试（npm run check） |

### 运行时层

- `scripts/data/compact.mjs`：data/ 全部 JSON → `apps/web/src/data/compact/*` + `apps/miniprogram/data/*`（git 忽略，构建生成）
- `packages/shared`：src → build.mjs → dist（cjs/esm），Web/小程序同构业务层（createRepository 组装 loaders）
- 前端消费：地图点位/信息卡、详情页（招生/升学/品牌卡/信号）、排行榜、初中明细

### 关键约束

- `entities.json`、`xiaoshengchu_2026.json`、`school_groups.json` 为公共枢纽，改动影响面最大
- tier1（学校信号）自 2026-09-17 判定废弃：entities 对 tier1 的别名挂载已移除，仅存 tier1→entities 反查；重构不波及其他链
- 一致性保障：`npm run check`（check_groups_drift 用 git HEAD 比对全部生产脚本重跑产物 + check_middle_feed_snapshot 全量生源快照）
