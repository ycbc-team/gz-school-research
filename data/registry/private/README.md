# registry/private —— 民办学校名单业务

**定位**：民办学校名单权威表（**办学性质唯一真源**）。`entity/dist/entities.json` 的 `nature='民办'` 由此联表生产（公办不写字段，不在表中即有历史残留也会被清除）。

## 目录结构（五层）

| 层 | 内容 |
| --- | --- |
| `raw/` | `gzzk_2026_minban_high.json`（招考办民办高中源） |
| `src/` | `minban_{荔湾/越秀/海珠/天河/白云/黄埔/番禺}.json`（7 区手工采集的结构化清单，见下「src JSON 结构」） |
| `parsed/` | `pending_items.json`（待补实体/待核实操作清单，由 `extract_pending.py` 从 src JSON 提取；need_entity 57 项已全部补入实体，need_verify 23 条仍待核） |
| `scripts/` | 见下方「构建与脚本」 |
| `dist/` | `minban_schools.json`（民办名单权威表，**源表**） |

### src JSON 结构

每个 `minban_*.json` 是结构化数据源（替代早期 md 采集稿，2026-09-29 迁移）：

| 字段 | 含义 |
| --- | --- |
| `adcode` / `district` / `generated` / `data_basis` / `entity_basis` / `status` | 区与元信息 |
| `conclusions` | 核心结论（原 md「核心结论」节） |
| `sources` | 权威来源 `{name, url}` 列表 |
| `sections.mark_nature` | 确认民办且实体已存在（补标 nature=民办 的行，含 school_id/stage/source_urls/note） |
| `sections.already_marked` | 已标民办、无需重复处理（供核对） |
| `sections.need_entity` | 确认民办但实体不存在（需先补实体） |
| `sections.need_verify` | 待核实（性质/名称/存续存疑） |
| `sections.excluded` | 已排除：公办/民转公/停办/误植等「非民办」行（不参与 manual 标注） |
| `notes.verification_basis` / `summary` / `todos` / `section_prose` | 核实依据、汇总、待办及各区节内说明 |

> 排除语义由 `sections.excluded` 结构化表达（替代旧 md 的「行内关键词排除」启发式，如番禺金海岸学校公办更正行不再依赖"公办"字样过滤）。

## 构建与脚本

| 脚本 | 职责 |
| --- | --- |
| `build_minban_official.py` | 番禺民办名单官方源自动解析——**直接读 `data/enrollment/raw/panyu_2026_official.xls`**（xlrd 解析「民办招生计划」sheet，39 所），不再依赖转录中间产物；`--check` 模式供 drift 检查（禁手改） |
| `apply_minban_patch.py` | 汇总 7 区 `minban_*.json` 的 `mark_nature` + `already_marked` 节，把「实体已存在、补标 nature=民办」的 school_id 追加进 `dist/minban_schools.json`（只更新源表，不直接写 entities） |
| `annotate_minban_sources.py` | 来源标注：`manual`（JSON 各节出现的 school_id，excluded 节除外）与 `legacy`（历史遗留）分开 |
| `extract_pending.py` | 从 `src/minban_*.json` 的 `need_entity`/`need_verify` 节提取清单 → `parsed/pending_items.json`（民办扩充操作清单；need_entity 交 poi/apply_poi_patch 补 POI+实体，need_verify 人工核实） |

## 维护约束

- **改民办名单 → 只改 `src/minban_*.json` + 重跑 `apply_minban_patch.py`，然后必须重跑 `entity/scripts/build_entities.py`**（nature 由表联表生产）；禁止手改 `dist/minban_schools.json` 或直接改 entities 的 nature。
- 番禺官方源由 `build_minban_official.py` 自动解析（禁手改，直接读官方 xls），drift 检查的「民办官方源校验」对拍。
- 公办为默认性质不写字段；误标扩散（如 2026-09-18 剑桥郡小学被误标民办）由表驱动清除。

## 产物与下游

| 产物 | 下游 |
| --- | --- |
| `dist/minban_schools.json`（226 所） | `entity/scripts/build_entities.py` 联表生产 nature；快照测试（`c3ee85789c726b50`）感知变化 |
