# registry/entity —— 学校实体表业务（最基础维度）

**定位**：全链 school_id 外键的维度表枢纽。范式为 **POI 点位表 — Entity 实体表 — Fact 事实表** 三分离：
一个 POI（校区/学部）= 一个 Entity，1:1，`school_id` 即主键；集团/教育集团关系由 `group/` 业务另表承载。

## 目录结构（五层）

| 层 | 内容 |
| --- | --- |
| `raw/` | `amap_query_input.json` / `amap_query_results.json`（高德 Web 服务 API 点位查询的原始输入与返回） |
| `parsed/` | `pending_items.json`（待补实体/待核实清单，由 `extract_pending.py` 从民办采集 md 提取） |
| `scripts/` | 见下方「构建与脚本」 |
| `dist/` | `entities.json`（实体表，**禁手改**）、`sites.json`（高中/完中站点表，31 所） |

> 历史 `src/source_name_mappings.json` 已退役（2026-09-21）：71 条官方名→id 桥接由 school_match norm 自动命中，3 条裸名歧义下沉 `linkage/build_special_matrix.py` 的 `SPECIAL_NAME_FIX` 显式归位。

## 构建与脚本

| 脚本 | 职责 | 用法 |
| --- | --- | --- |
| `build_entities.py` | 实体表构建：POI→Entity 1:1，挂官方名/校区/更名别名，民办 nature 由 `private/dist/minban_schools.json` 联表生产，回写 POI 表 school_id 并清假学校点位 | `python3 data/registry/entity/scripts/build_entities.py`（幂等；`--out-dir <dir>` 供 drift 检查重放） |
| `build_sites.py` | 站点表构建：高中/完中 POI 按 base 名归组成法人 → 多 site | `python3 data/registry/entity/scripts/build_sites.py` |
| `school_match.py` | **全项目唯一校名匹配库**：`normName/looseNorm/coreCampusName/legalKey/legalCampuses` + `SchoolMatcher`，全项目 26+ 个脚本 import | 被各业务脚本 import，不单独运行 |
| `match_school.py` | 命令行查实体工具：给定区 adcode + 校名查 entities.json | `python3 data/registry/entity/scripts/match_school.py <adcode> "<校名>" [--stage ...]` |
| `extract_pending.py` | 从 `private/src/minban_*.md` 提取"需补实体/待核实"清单 → `parsed/pending_items.json` | `python3 data/registry/entity/scripts/extract_pending.py` |

## 产物与下游

| 产物 | 说明 | 下游 |
| --- | --- | --- |
| `dist/entities.json` | 实体表（1554 实体，school_id 主键 + name/stage/aliases/nature） | **全链枢纽**：xiaoshengchu、配额、录取分、详情页、SchoolMatcher 等全部按 school_id 引用 |
| `dist/sites.json` | 高中/完中站点表（31 所，法人粒度） | 高中点位、搜索站点列表 |

## 维护约束

- **禁手改 `dist/`**：实体表/POI 只由生产脚本构建。改别名/校区归属/学段 → 固化进 `build_entities.py` 的对应别名表（`OFFICIAL_MIDDLE_ALIAS` / `GROUP_MEMBER_ALIAS` / `CAMPUS_STAGE_FIX` 等）后重跑。
- 民办性质唯一真源是 `private/dist/minban_schools.json`；改民办名单须重跑 `build_entities.py`。
- 一致性由 `check_groups_drift.py` 重放保护（重跑 build_entities → 与入库比对，不一致即失败）。
- norm 唯一真源是 `school_match.normName`；其他脚本不得自带归一实现（历史上 xs_resolver 自带前缀删实现曾与实体别名失配，已收敛）。
