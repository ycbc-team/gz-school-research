# 校名匹配规则收敛·实施报告（2026-09-16）

> 主线：用户问"项目中有多少种校名匹配规则（政府文件校名→实体表→school_id）？能收敛一份吗？"
> 实施：**先收敛 Python 侧（19 脚本 34 处 norm → 统一库）**，并确认 py 侧行政区/学段匹配覆盖；
> 同时盘点运行时（packages/shared）名称匹配场景，评估下沉数据层。

---

## 一、收敛结果（已提交 3ce9d13）

**34 处 norm/匹配函数定义 → 1 个库 `scripts/registry/school_match.py`（4 档 norm + 统一匹配服务）**

| 档位 | 规则 | 语义 | 对应原实现 |
|---|---|---|---|
| `normName` | 全角括号→半角→去「广州市」→删括号→去空白 | 严格全等 | build_entities/support.ts、backfill_school_ids、build_scores、apply_poi_patch、coverage_check、generate_coverage_doc、build_special_matrix、build_high_levels_js、match_school.normalize 等 |
| `looseNorm` | normName + 去尾部(初中部/高中部/小学部/校区/分校/学校/部) | 学部容错全等 | support.ts looseNorm、backfill_school_ids.loose、backfill_all（norm 本体） |
| `matchNorm` | 泛词保护：状态括号剥/保留校区括号、区名归一、前导区名剥（纯泛词保护）、「广州」剥（保护） | 集团成员→POI（含 substring） | match_poi.norm（最完整版） |
| `brandNorm` | 去「广州市」+「广州」+删括号 | 品牌/集团名包含 | merge_groups.norm |

**统一匹配服务 `SchoolMatcher`**：exact(normName) → alias(matchNorm+去括号 key) → 主校前缀 → 远郊拦截 → substring 双支；
收敛顺序：**同区唯一 → 同区同阶段唯一 → 主 POI → 全局唯一（显式跨区放行）→ 缺失（宁可缺失不跨区）**。
参数：`preferred_adcode`（行政区）、`preferred_stage`（学段）。

**收敛方式**：
- `match_poi.py` 变为 CLI 薄封装；`merge_groups.py` 用 brandNorm + SchoolMatcher；其余 17 个脚本删本地 norm 定义、统一 import。
- 采集侧特有清洗保留在各自脚本（**不混入共享 norm**）：番禺区/镇前缀（backfill_schools 等）、区名剥离（build_district_enrollment）、
  学部分层（build_ranking_middle py_loose2）、PDF 表解析清洗（parse_batch2）、NFKC/繁简（fold_unicode，供采集输入）。

**验证（等价性证明）**：收敛后重跑 vs 收敛前（git stash 原脚本）重跑，产物**逐字节一致**
（quota_matrix/scores/special_matrix/ranking_middle 均验证）；`npm run check` 全绿（40 测试 + 3352 数据质量 + 19 匹配器 + 产物一致性）。

---

## 二、问题 1 的答案：py 侧行政区/学段匹配现状

盘点结论：**只有 match_poi（SchoolMatcher）完整考虑了行政区与学段**，其余链路覆盖不均：

| 链路 | 行政区（adcode） | 学段（stage） | 备注 |
|---|---|---|---|
| 集团成员→POI（match_poi/SchoolMatcher） | ✅ preferred_adcode 同区收敛，宁可缺失不跨区；跨区显式放行（四中丰宁/培英鹤洞） | ✅ preferred_stage（初中计划优先初中部） | 最完整 |
| 小升初（build_middle_enrollment） | ✅ 传 adcode | ✅ 固定"初中" | 已复用匹配器 |
| 集团/品牌名（merge_groups） | ✅ 成员区名覆盖集团区 | ❌ 无学段 | 品牌名域 |
| 升学四表回填（backfill_school_ids） | ❌ 无 | ❌ 无（多实体取第一个） | **缺口**：`广州市第一中学` 配额被挂到高中部（实体 alias 歧义，入库版是初中部=人工修正正确） |
| 中考录取分（build_scores） | ❌ | ✅ 仅 high | 全等，无区收敛 |
| 初中排名（build_ranking_middle） | ❌ | ❌ | 集团归属兜底 |
| 高德采集评分（backfill_schools 等） | ✅ 区限定（city=440113） | ❌ | 评分制非确定性 |

**发现的历史遗留漂移（非收敛引入，已用 git stash 原脚本验证）**：
- `quota_matrix`/`scores_2025/2026`/`special_matrix`/`ranking_middle` 的入库产物与脚本当前状态不一致
  （重跑产生 199 个 school_id 变化、scores 5.5k 行变化等）。其中 quota_matrix 入库版本比脚本更准
  （初中配额挂初中部），说明入库经过人工/历史版本修正。**建议后续单独一轮处理**：backfill_school_ids
  补 stage 过滤 + 全量审阅 199 处变化 + 必要时补实体 alias，消除该漂移。

---

## 三、问题 2 的答案：运行时名称匹配场景盘点

`packages/shared`（用户可见详情页/数据 API）中所有"名称→id"解析点：

| # | 调用点 | 用途 | 能否下沉数据层 |
|---|---|---|---|
| 1 | `scores.ts resolveSchoolId(campus)` | 高中录取分：levels 校区名 → school_id | ✅ **可下沉**：`levels.json` 的 `campuses` 是纯名字符串数组，构建期（build_high_levels_js）补 `campuses[].school_id`，运行时按 id 直查 `by_school_id` |
| 2 | `quota.ts resolveSchoolIdOf(poiName)` + norm/包含兜底 | 初中配额：详情页 POI 名 → quota 行 | ✅ **可下沉**：quota_matrix 已回填 school_id，详情页有 `poi.school_id`，运行时传 id 直查；名称兜底仅孤儿 POI |
| 3 | `registry.ts resolveSchoolIdOf(name)`（groupOfSchool 无 school_id 分支） | 品牌关联反查 | ✅ **基本可去**：model.ts 已传 school_id，按名分支仅孤儿触发 |
| 4 | `model.ts resolvePoiName(n)` | feed 名单（小学→初中）POI 名解析 | ✅ **可下沉**：构建期预解析名单 school_id/poiName |
| 5 | `support.ts buildAliasTable/matchTier1ByPoiName` | tier1 口碑/地图点 | ✅ **可下沉**：tier1 记录已带 `school_ids` 外键，构建期做 `poi.school_id → tier1` 关联；名称匹配仅孤儿兜底 |

**结论**：运行时名称匹配可以大幅压缩为"仅孤儿 POI 兜底"。前提是**数据层（Python 构建期）把 school_id 写全**：
levels campuses 补 id、feed 名单预解析、tier1 按 school_id 关联。这一步与 Python 收敛衔接
（统一 SchoolMatcher 正是数据层预解析的工具）。建议作为下一步实施，涉及 shared 侧 `scores.ts`/`quota.ts`/
`model.ts` 的签名改造（名称→id 数组/直查）+ 对应数据文件补 id。

---

## 四、变更清单（提交 3ce9d13，20 files，+515/-405）

- **新增** `scripts/registry/school_match.py`：4 档 norm + SchoolMatcher + CLI（`python3 scripts/registry/school_match.py "<校名>" [--adcode XXXX] [--stage 初中]`）
- **收敛**（删本地 norm 定义，import 共享库）：match_poi、merge_groups、data_quality_test、test_match_poi、build_middle_enrollment、backfill_school_ids、build_special_matrix、build_ranking_middle、build_scores、build_high_levels_js、backfill_all、backfill_schools、backfill_xiaoshengchu_missing、build_district_enrollment、apply_poi_patch、coverage_check、generate_coverage_doc、amap_batch_query、match_school（共 19 个）
- **保留**（非校名匹配域）：parse_batch2（PDF 表解析清洗）、upgrade_xiaoshengchu.mjs（TS 侧，与 build_entities 同一 normName，属 shared 收敛范围）
