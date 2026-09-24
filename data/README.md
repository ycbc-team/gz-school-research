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
| `enrollment/` | 跨学段 | `raw/`（政府官方源文件，小学/小升初/初中招生共用同一份原文，2026-09-23 自 `primary/enrollment/raw` 与 `transition/raw` 归位） |
| `primary/` | 小学 | `enrollment/`（小学招生，parsed/scripts/src/docs/test 分层）、`transition/`（小升初升学路线）、`tier1_schools_all.json`（第一梯队核验）；点位见 `poi/` |
| `middle/` | 初中 | `enrollment/`（公办初中招生，parsed/src/scripts/dist/docs/test 分层，2026-09-23 迁入）、`org_sort/`（默认排序）、`tier1_schools_all.json`（初中第一梯队核验）；点位见 `poi/` |
| `high/` | 高中 | `level/src/levels.json`（学校清单/分类/指标）；`cutoff_score/`（录取分：`dist/` 历年产物 / `raw/` 官方源页面 / `src/` 手工源 / `scripts/` 解析脚本）；点位见 `poi/` |
| `civilized_campuses/` | 跨学段 | 全国/省市文明校园：`raw/` 保留全部来源，正式全国名单经 `parsed/` 和 `scripts/build_dist.py` 编译为运行时 `school_id` 索引；详见目录 README |
| `poi/` | 跨学段 | `dist/primary_poi.json`（931 所）/ `dist/middle_poi.json`（475 所）/ `dist/high_poi.json`（清洗后 126 所）；采集/补点脚本在 `poi/scripts/`，查询留痕 `poi/raw/amap_query_*.json` |
| `registry/` | 跨学段 | 三个业务子目录：`entity/`（实体表，全链 school_id 维度枢纽）、`group/`（教育集团/品牌关联）、`private/`（民办名单真源）；详见各子目录 README |

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
python3 data/primary/enrollment/scripts/build_primary_2026.py <区>   # 2026 小学招生 B 层（parsed/_transcripts→parsed/2026-<区>.json，SchoolMatcher 匹配实体表）
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

跨学段的教育集团/品牌/民办业务已按**三个业务子目录**组织，业务级 README 就近维护：

- `registry/entity/README.md` — 实体表（全链 school_id 维度枢纽，POI—Entity—Fact 三分离范式）
- `registry/group/README.md` — 教育集团/品牌关联（政府源→成员→校区解析、锚点表规则、P0–P4 任务状态）
- `registry/private/README.md` — 民办名单真源（官方源自动解析 + 7 区采集、改表须重跑 build_entities）

## 数据依赖链（2026-09-20 记录）

数据流总览：**源头（外部抓取/官方转录/人工）→ 构建脚本 → data/ 产物 → compact.mjs 编译 → Web/小程序运行时**。全链以 school_id 外键关联，`registry/entity/dist/entities.json` 是唯一维度表枢纽。

### 源头层（无上游脚本写入 = 真源）

| 类型 | 文件 |
| --- | --- |
| 外部抓取（高德 API） | `poi/dist/primary_poi.json`、`poi/dist/middle_poi.json`、`poi/dist/high_poi.json`（fetch_* 脚本直写） |
| 官方转录 | `enrollment/raw/*`（政府官方源文件，小学/小升初/初中招生共用）、`primary/enrollment/parsed/2026-*`（小学招生计划）、`primary/enrollment/parsed/_transcripts/*`（各区官方文件 A 层转录）、`middle/enrollment/parsed/_transcripts/*`（初中转录）、`linkage/raw/*`（指标/自招/录取线/招生名单转录）、`high/cutoff_score/dist/scores_{2025,2026}.json`（官方录取分） |
| 人工产物 | `primary|middle/tier1_schools_all.json`（学校信号，已判废弃待重构）、`high/level/src/levels.json`、`middle/org_sort/src/*`、`registry/group/src/brand_groups.json`、`registry/group/parsed/education_groups_2026.json`、`registry/group/parsed/_partial_*`、`registry/private/src/minban_*.md` |

### 派生层（脚本产物，勿手改；改脚本须重跑并提交）

| 产物 | 生产脚本 | 下游 |
| --- | --- | --- |
| `registry/entity/dist/entities.json` | build_entities.py | 全链 school_id 外键维度表 |
| `primary/transition/dist/xiaoshengchu_<区>.json` + `primary/transition/dist/xiaoshengchu_all.json` | build_xiaoshengchu_all.py + xs_resolver.py | 升学路线（区级/all 为中间产物，已 gitignore） |
| `primary/transition/dist/xiaoshengchu_2026.json`（facts） | upgrade_xiaoshengchu.mjs | 小学升学路线、初中生源反查（middlePrimaryFeed）、生源快照测试 |
| `middle/enrollment/dist/middle_enrollment_2026_<区>.json`（7 区，2026-09-23 自 primary/enrollments 迁入） | `middle/enrollment/scripts/build_middle_enrollment.py` | 详情页初中招生计划 |
| `linkage/quota_matrix.json` / `special_matrix.json` / `district_quota.json` / `batch2_scores.json` | rebuild_quota_matrix / build_special_* / build_district_quota / build_linkage_batch2（+ backfill_school_ids 回填 id） | 升学通道、排行榜 |
| `linkage/ranking_middle.json`（334 校） | build_ranking_middle.py | 详情页升学信号、排行榜、初中明细 |
| `registry/group/dist/education_groups.json` | merge_groups.py（合并 parsed `_partial_*` + src/brand_groups + parsed/education_groups_2026） | 品牌卡、初中明细分组 |
| `registry/group/dist/school_groups.json`（集团 → school_id[]） | build_school_groups.py（--write-brand 回写 src/brand_groups） | 品牌卡、初中明细分组（加载时反建纯 id 匹配） |
| `middle/org_sort/dist/compiled.json` | data/middle/org_sort/scripts/build_org_sort.py | 初中默认排序 |
| `primary/transition/dist/middle_feed_snapshot.json` | build_middle_feed_snapshot.py | 初中生源全量快照测试（npm run check） |

### 运行时层

- `scripts/data/compact.mjs`：data/ 全部 JSON → `apps/web/src/data/compact/*` + `apps/miniprogram/data/*`（git 忽略，构建生成）
- `packages/shared`：src → build.mjs → dist（cjs/esm），Web/小程序同构业务层（createRepository 组装 loaders）
- 前端消费：地图点位/信息卡、详情页（招生/升学/品牌卡/信号）、排行榜、初中明细

### 关键约束

- `entities.json`、`xiaoshengchu_2026.json`、`school_groups.json` 为公共枢纽，改动影响面最大
- tier1（学校信号）自 2026-09-17 判定废弃：entities 对 tier1 的别名挂载已移除，仅存 tier1→entities 反查；重构不波及其他链
- 一致性保障：`npm run check`（check_groups_drift 用 git HEAD 比对全部生产脚本重跑产物 + check_middle_feed_snapshot 全量生源快照）
