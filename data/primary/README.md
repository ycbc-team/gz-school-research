# 小学段数据层（primary）

多端共用的小学段数据快照（web 应用、微信小程序等均从此目录读取，避免各自维护）。

> 更新：2026-09-21。小学招生与小升初已拆为两个独立业务目录；各业务级 README 为权威说明。

## 目录与文件

| 路径 | 业务 | 说明 |
| --- | --- | --- |
| `enrollment/` | **小学招生**（公办小学地段/计划） | 按 raw/parsed/scripts/src/docs 分层；A 层转录 + B 层 SchoolMatcher 匹配，详见 `enrollment/README.md` |
| `transition/` | 小升初升学路线（xiaoshengchu） | 官方源/解析产物/构建脚本/运行时产物，详见 `transition/README.md`（初中招生为下一步，暂归此处） |
| `enrollments/` | ~~公办初中招生计划 dist~~（2026-09-23 已迁 `data/middle/enrollment/`，本目录仅剩 .DS_Store） | — |
| `tier1_schools_all.json` | 口碑学校（第一梯队小学） | 网传/公开信息整理（前端 compact 消费） |

## 业务边界

- **小学招生**（`enrollment/`）：官方招生地段/计划表 → 转录 → 实体表匹配。只含公办；民办招生归 `data/registry/private/`（旧流程把番禺民办混入小学产物，已修正）。
- **小升初**（`transition/`）：小学→初中升学路线（xiaoshengchu）。初中招生已独立为 `data/middle/enrollment/`（2026-09-23 迁出）。

## check 链

- `transition/` 构建与 check 见其业务 README；check 链（`data/registry/group/scripts/check_groups_drift.py`）自动覆盖。
- `enrollment/` 的转录审计见 `enrollment/docs/`（交叉比对 + 新旧差异审计）。
