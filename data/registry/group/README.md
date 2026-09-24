# registry/group —— 教育集团/品牌关联业务

**定位**：跨学段教育集团名录与品牌组成员清单，供详情页「品牌关联」板块、品牌卡、初中明细分组与覆盖核对使用。核心是**政府源清单 → 成员名 → 校区实体（school_id）**的解析链路，匹配规则统一走 `entity/scripts/school_match.py`（legalKey/legalCampuses）。

## 目录结构（五层）

| 层 | 内容 |
| --- | --- |
| `raw/` | `government/yuexiu_669_2026-06.html`（越秀区政府源文件，成员级对齐底表） |
| `parsed/` | `_partial_{7区}_groups.json`（政府 HTML 解析出的纯名字底稿）+ `education_groups_2026.json`（招考办 2026 集团名额分配表：43 核心校 / 118 成员） |
| `src/` | `brand_groups.json`（8 品牌组手工源，含法人关系/来源 URL）、`groups_anchors.json`（锚点表，仅承载一对多关系） |
| `scripts/` | 见下方「构建与脚本」 |
| `dist/` | `education_groups.json`（合并后集团表）、`school_groups.json`（集团运行时纯 id 匹配）、`non_group_multi_campuses.json`（未入集团的多校区运行时纯 id 匹配） |
| `test/` | `coverage_result.json`（覆盖检查中间结果，仅供测试与覆盖报告生成） |

## 构建与脚本

| 脚本 | 职责 |
| --- | --- |
| `parse_government_groups.py` | 政府 HTML → 7 区 `_partial_*` 纯名字底稿 |
| `merge_groups.py` | 合并 partial + 招考办表 + brand_groups + 锚点表；法人归并用统一 `legalKey/legalCampuses`（剥括号/学部后缀 + 法人核心名匹配），不再本地推导；脚本按自身路径定位仓库根目录，可在任意 worktree 重跑 |
| `build_school_groups.py` | 教育集团成员 → school_id（当前 education 546 / brand 41），输出 `school_groups.json` |
| `build_non_group_multi_campuses.py` | 实体注册表 + 集团映射 → 未入集团的同法人多校区，输出 `non_group_multi_campuses.json` |
| `check_groups_drift.py` | **铁律校验**：重跑全链路生产脚本与入库比对（含 build_entities/merge_groups/backfill 等），漂移即失败；`npm run check` 的一部分 |
| `coverage_check.py` / `generate_coverage_doc.py` | P1 集团成员覆盖比对（POI 后缀/区名前缀/校区后缀三种变体）与覆盖清单文档生成 |

## 关键规则

- **统一匹配，禁止人为补括号别名**：校区匹配一律走 `school_match.legalKey/legalCampuses`（第一层 legalKey 全等、第二层「法人核心名以校区结尾且以法人 key 开头」归并），12 个后缀式校区由此自动进入覆盖。
- **锚点表只承载「一对多」**（成员名→多个校区 POI）；单校区锚定全部下沉实体表别名（`build_entities.py` 的 `GROUP_MEMBER_ALIAS`）。产物确定性由 `test_match_poi` golden + `check_groups_drift` 保证。
- **禁手改 `dist/`**：手改会被重跑覆盖且被 drift 检查检出。更名/并入/承继等事实固化进实体别名或锚点表。
- **历史 P3 文档含生成后人工章节，重跑 `gen_p3_report.py` 会覆盖丢失**；仅重建统计时运行，先备份/合并人工章节。当前集团主产物已完成 P3 补录，文档只作过程留档。
- 每次集团名单变更**必须**同步更新逐集团快照测试（`packages/shared/tests/snapshots/group_roster.json`，86 教育集团 + 8 品牌，逐集团 diff 感知）。

## 数据源

- 招考办《2026年广州市成立教育集团的示范性普通高中面向集团的直接名额分配情况》（2026-05-12）：http://gzzk.gz.gov.cn/gkmlpt/content/10/10809/post_10809470.html
- 各区教育局/区政府文件（集团化办学批复与成员名单）；越秀底表见 `raw/government/`。
- 8 品牌组经官网/招考办/区政府文件/主流媒体交叉核实（P2，2026-09-10），全部附来源 URL + 法人关系标注。

## 教育集团数据流与产物纪律（2026-09 品牌关联修复后强制）

数据流（禁止绕过）：

```
data/registry/group/parsed/_partial_{区}_groups.json   ← 7 区采集底稿（纯源，人工维护，含 school_id 锚点）
data/registry/group/parsed/education_groups_2026.json ← 招考办名额分配表（纯源）
data/registry/group/src/brand_groups.json          ← 8 重点品牌（纯源，unit.school_ids 外键锚点）
        │
        ▼  python3 scripts/merge_groups.py   （本地脚本，无联网）
data/registry/group/dist/education_groups.json      ← ★ 教育集团唯一生成产物，禁止手改 ★
data/registry/group/dist/non_group_multi_campuses.json ← 同区同法人、未入集团的多校区派生产物
        │
        ▼  node scripts/data/compact.mjs  +  npm run build:shared
apps/web/src/data/compact/**  与  @gz/shared 构建产物（Web/小程序实际消费）
```

纪律：

1. **产物禁止手改**：`education_groups.json` 只能由 `merge_groups.py` 生成。需要调整归属时改三处源
   （partial / brand_groups / entities），然后重跑生产脚本。历史 94 处漂移即因 9 次提交直接手改产物造成。
2. **先跑生产脚本**：`npm run check` 已内置 `check_groups_drift.py`——重跑 `merge_groups.py` 到临时文件
   并与入库产物对比，不一致即失败（丢失/错配/新增逐条列出）。改源后必须重跑
   `python3 scripts/merge_groups.py` 使产物同步，否则 check 红。
3. **匹配器**：`scripts/match_poi.py` 的改动由 `scripts/test_match_poi.py`（14 回归用例）与
   `data_quality_test.py`（3307 项含全量 POI 自我匹配）守护；改匹配器必须全量重跑 `npm run check`。
4. **宁可缺失、不跨区错配**：匹配器对无法收敛到唯一同区候选的成员返回缺失，由调用方以显式
   school_id 锚点（partial/brand_groups 的 school_ids 字段）补救，不允许跨区吸附。
5. **新增/调整学校归属标准流程**：改源 → 重跑 `python3 scripts/merge_groups.py` → `npm run check`
   （含产物一致性）→ 确认缺失清单（若为真实缺失，在 partial 标记 `7区内真实缺失` 并同步产物）→ 提交源+产物。

## 非集团多校区审计（2026-09-24）

“同一学校有多个校区”不等于“教育集团成员”，不得写入 `education_groups.json` 或
`school_groups.json` 冒充集团归属。当前可用实体层 `legalKey` 按**同一物理区**聚合，去重
`school_id` 后排除所有已命中 `school_groups.json` 的校区，得到：**64 个候选法人、139 个
distinct school_id**。其中小学为主，也混有九年制/完中学校的跨学段实体；这是一份“多校区、未入
集团”的审计候选，而不是官方集团名单。

已落盘为 `dist/non_group_multi_campuses.json`，包含 `legal_key`、`district_adcode`、
`school_ids`、各实体名称/学段和 `derivation: entity_legal_key`。运行时仅用于“校区规模”
展示/筛选，不能用于品牌或集团关联；详情页始终教育集团优先、多校区兜底。它仍是实体层推导结果，
不应被表述为官方集团事实。

## 任务状态

- **P0（完成）**：招考办 2026 表落盘 `parsed/education_groups_2026.json`
- **P1（完成，历史范围）**：招考办 2026 表 161 校覆盖比对（精确命中 49 / 变体命中 45 / 7 区内真实缺失 2 / 远郊不在范围 65），文档见 `docs/coverage/`
- **P2（完成）**：8 品牌组官方来源交叉核实，写回 `src/brand_groups.json`
- **P3（完成，2026-09-14）**：区属非示范集团 + 小学集团已按各区文件补录；当前合并产物为 86 个教育集团、344 个成员，集团 `school_id` 映射为 587 条（education 546 / brand 41）。
- **P4（未完成）**：年度更新机制（每年 5 月招考办新表发布后刷新）
