# registry/group —— 教育集团/品牌关联业务

**定位**：跨学段教育集团名录与品牌组成员清单，供详情页「品牌关联」板块、品牌卡、初中明细分组与覆盖核对使用。核心是**政府源清单 → 成员名 → 校区实体（school_id）**的解析链路，匹配规则统一走 `entity/scripts/school_match.py`（legalKey/legalCampuses）。

## 目录结构（五层）

| 层 | 内容 |
| --- | --- |
| `raw/` | `government/yuexiu_669_2026-06.html`（越秀区政府源文件，成员级对齐底表） |
| `parsed/` | `_partial_{7区}_groups.json`（政府 HTML 解析出的纯名字底稿）+ `education_groups_2026.json`（招考办 2026 集团名额分配表：43 核心校 / 118 成员） |
| `src/` | `brand_groups.json`（8 品牌组手工源，含法人关系/来源 URL）、`groups_anchors.json`（锚点表，仅承载一对多关系） |
| `scripts/` | 见下方「构建与脚本」 |
| `dist/` | `education_groups.json`（合并后集团表）、`school_groups.json`（运行时纯 id 匹配）、`coverage_result.json`（覆盖检查产物） |

## 构建与脚本

| 脚本 | 职责 |
| --- | --- |
| `parse_government_groups.py` | 政府 HTML → 7 区 `_partial_*` 纯名字底稿 |
| `merge_groups.py` | 合并 partial + 招考办表 + brand_groups + 锚点表；法人归并用统一 `legalKey/legalCampuses`（剥括号/学部后缀 + 法人核心名匹配），不再本地推导 |
| `build_school_groups.py` | 教育集团成员 → school_id（education 530 / brand 43 等），输出 `school_groups.json` |
| `check_groups_drift.py` | **铁律校验**：重跑全链路生产脚本与入库比对（含 build_entities/merge_groups/backfill 等），漂移即失败；`npm run check` 的一部分 |
| `coverage_check.py` / `generate_coverage_doc.py` | P1 集团成员覆盖比对（POI 后缀/区名前缀/校区后缀三种变体）与覆盖清单文档生成 |

## 关键规则

- **统一匹配，禁止人为补括号别名**：校区匹配一律走 `school_match.legalKey/legalCampuses`（第一层 legalKey 全等、第二层「法人核心名以校区结尾且以法人 key 开头」归并），12 个后缀式校区由此自动进入覆盖。
- **锚点表只承载「一对多」**（成员名→多个校区 POI）；单校区锚定全部下沉实体表别名（`build_entities.py` 的 `GROUP_MEMBER_ALIAS`）。产物确定性由 `test_match_poi` golden + `check_groups_drift` 保证。
- **禁手改 `dist/`**：手改会被重跑覆盖且被 drift 检查检出。更名/并入/承继等事实固化进实体别名或锚点表。
- 每次集团名单变更**必须**同步更新逐集团快照测试（`packages/shared/tests/snapshots/group_roster.json`，86 教育集团 + 8 品牌，逐集团 diff 感知）。

## 数据源

- 招考办《2026年广州市成立教育集团的示范性普通高中面向集团的直接名额分配情况》（2026-05-12）：http://gzzk.gz.gov.cn/gkmlpt/content/10/10809/post_10809470.html
- 各区教育局/区政府文件（集团化办学批复与成员名单）；越秀底表见 `raw/government/`。
- 8 品牌组经官网/招考办/区政府文件/主流媒体交叉核实（P2，2026-09-10），全部附来源 URL + 法人关系标注。

## 任务状态

- **P0（完成）**：招考办 2026 表落盘 `parsed/education_groups_2026.json`
- **P1（完成）**：161 校覆盖比对（精确命中 49 / 变体命中 45 / 7 区内真实缺失 2 / 远郊不在范围 65），文档见 `docs/coverage/`
- **P2（完成）**：8 品牌组官方来源交叉核实，写回 `src/brand_groups.json`
- **P3（未完成）**：区属非示范集团 + 小学集团全量按各区文件补录
- **P4（未完成）**：年度更新机制（每年 5 月招考办新表发布后刷新）
