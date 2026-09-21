# registry/private —— 民办学校名单业务

**定位**：民办学校名单权威表（**办学性质唯一真源**）。`entity/dist/entities.json` 的 `nature='民办'` 由此联表生产（公办不写字段，不在表中即有历史残留也会被清除）。

## 目录结构（五层）

| 层 | 内容 |
| --- | --- |
| `raw/` | `gzzk_2026_minban_high.json`（招考办民办高中源） |
| `src/` | `minban_{荔湾/越秀/海珠/天河/白云/黄埔/番禺}.md`（7 区手工采集：第一节实体已存在补标、第二节需补实体、第三节待核实） |
| `parsed/` | `pending_items.json`（待补实体/待核实操作清单，由 `extract_pending.py` 从 src md 提取；need_entity 57 项已全部补入实体，need_verify 16 条仍待核） |
| `scripts/` | 见下方「构建与脚本」 |
| `dist/` | `minban_schools.json`（民办名单权威表，**源表**） |

## 构建与脚本

| 脚本 | 职责 |
| --- | --- |
| `build_minban_official.py` | 番禺民办名单官方源自动解析（`data/primary/enrollments/_raw/panyu_2026_official.json` 的「民办招生计划」sheet，39 所）；`--check` 模式供 drift 检查（禁手改） |
| `apply_minban_patch.py` | 汇总 7 区 `minban_*.md` 采集，把「实体已存在、补标 nature=民办」的 school_id 追加进 `dist/minban_schools.json`（只更新源表，不直接写 entities） |
| `annotate_minban_sources.py` | 来源标注：`manual`（md 采集，排除"公办/勿混淆/非同一所/排除/转公"段）与 `legacy`（历史遗留）分开 |
| `extract_pending.py` | 从 `src/minban_*.md` 提取"需补实体/待核实"清单 → `parsed/pending_items.json`（民办扩充操作清单；need_entity 交 poi/apply_poi_patch 补 POI+实体，need_verify 人工核实） |

## 维护约束

- **改民办名单 → 只改 `src/minban_*.md` + 重跑 `apply_minban_patch.py`，然后必须重跑 `entity/scripts/build_entities.py`**（nature 由表联表生产）；禁止手改 `dist/minban_schools.json` 或直接改 entities 的 nature。
- 番禺官方源由 `build_minban_official.py` 自动解析（禁手改），drift 检查的「民办官方源校验」对拍。
- 公办为默认性质不写字段；误标扩散（如 2026-09-18 剑桥郡小学被误标民办）由表驱动清除。

## 产物与下游

| 产物 | 下游 |
| --- | --- |
| `dist/minban_schools.json`（226 所） | `entity/scripts/build_entities.py` 联表生产 nature；快照测试（`c3ee85789c726b50`）感知变化 |
