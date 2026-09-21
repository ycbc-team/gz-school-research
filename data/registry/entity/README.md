# registry/entity —— 学校实体表业务（最基础维度）

**定位**：全链 school_id 外键的维度表枢纽。范式为 **POI 点位表 — Entity 实体表 — Fact 事实表** 三分离：
一个 POI（校区/学部）= 一个 Entity，1:1，`school_id` 即主键；集团/教育集团关系由 `group/` 业务另表承载。

## 目录结构

| 层 | 内容 |
| --- | --- |
| `scripts/` | 见下方「构建与脚本」 |
| `dist/` | `entities.json`（实体表，**禁手改**） |

> 归属说明：
> - 民办采集的待补实体/待核实清单（`pending_items.json`）与提取工具（`extract_pending.py`）归位 `private/`（民办业务，见 `data/registry/private/README.md`）。
> - POI 采集/补点全部归位 `data/poi/`：查询输入输出 `raw/amap_query_*.json`、脚本 `amap_batch_query.py` / `apply_poi_patch.py` 在 `scripts/`。
> - 历史 `src/source_name_mappings.json` 已退役（2026-09-21）：71 条官方名→id 桥接由 school_match norm 自动命中，3 条裸名歧义下沉 `linkage/build_special_matrix.py` 的 `SPECIAL_NAME_FIX` 显式归位。

## 构建与脚本

| 脚本 | 职责 | 用法 |
| --- | --- | --- |
| `build_entities.py` | 实体表构建：POI→Entity 1:1，挂官方名/校区/更名别名，民办 nature 由 `private/dist/minban_schools.json` 联表生产，回写 POI 表 school_id 并清假学校点位 | `python3 data/registry/entity/scripts/build_entities.py`（幂等；`--out-dir <dir>` 供 drift 检查重放） |
| `school_match.py` | **全项目唯一校名匹配库**：`normName/looseNorm/coreCampusName/legalKey/legalCampuses` + `SchoolMatcher`，全项目 26+ 个脚本 import | 被各业务脚本 import，不单独运行 |
| `match_school.py` | 命令行查实体工具：给定区 adcode + 校名查 entities.json | `python3 data/registry/entity/scripts/match_school.py <adcode> "<校名>" [--stage ...]` |

## 产物与下游

| 产物 | 说明 | 下游 |
| --- | --- | --- |
| `dist/entities.json` | 实体表（1554 实体，school_id 主键 + name/stage/aliases/nature） | **全链枢纽**：xiaoshengchu、配额、录取分、详情页、SchoolMatcher 等全部按 school_id 引用 |

> 历史 `dist/sites.json` + `build_sites.py` 已废弃（2026-09-21）：site id 自成一派（非 school_id）、与 POI/entities 三层冗余、无有效运行时消费；法人→多校区别名挂载已内联 `build_entities.py`（`_site_groups` 归组 + 铁英共享别名显式迁移），产物与废弃前完全等价。

## 维护约束

- **禁手改 `dist/`**：实体表/POI 只由生产脚本构建。改别名/校区归属/学段 → 固化进 `build_entities.py` 的对应别名表（`OFFICIAL_MIDDLE_ALIAS` / `GROUP_MEMBER_ALIAS` / `CAMPUS_STAGE_FIX` 等）后重跑。
- 民办性质唯一真源是 `private/dist/minban_schools.json`；改民办名单须重跑 `build_entities.py`。
- 一致性由 `check_groups_drift.py` 重放保护（重跑 build_entities → 与入库比对，不一致即失败）。
- norm 唯一真源是 `school_match.normName`；其他脚本不得自带归一实现（历史上 xs_resolver 自带前缀删实现曾与实体别名失配，已收敛）。
