# 小学段数据层（primary）

多端共用的小学段数据快照（web 应用、微信小程序等均从此目录读取，避免各自维护）。

> 更新：2026-09-21。小升初（xiaoshengchu）业务已归位 `transition/`（raw/parsed/src/scripts/dist/docs），
> 本 README 只讲 data/primary 下其余内容；各业务级 README 为权威说明。

## 目录与文件

| 路径 | 业务 | 说明 |
| --- | --- | --- |
| `transition/` | 小升初升学路线（xiaoshengchu） | 官方源/解析产物/构建脚本/运行时产物，详见 `transition/README.md` |
| `enrollments/` | 公办初中招生计划 | `middle_enrollment_2026_<区>.json`（7 区），构建脚本 `scripts/primary/build_middle_enrollment.py` |
| `tier1_schools_all.json` | 口碑学校（第一梯队小学） | 网传/公开信息整理；实体分类见 `scripts/primary/build_entity_classification.py` |
| `middle_enroll_notes.json` | 初中录取备注 | 按 school_id 的录取规则补充说明（如"初三才在本校区就读"），小程序主包 compact 消费 |

## 说明

- `transition/` 的构建与 check 见其业务 README；check 链（`data/registry/group/scripts/check_groups_drift.py`）自动覆盖。
- `enrollments/` 原 `_raw/`（官方源）与 `2026-<区>.json`（解析产物）已随小升初业务迁入
  `transition/raw`、`transition/parsed`；`build_middle_enrollment.py` 消费这些路径。
- `middle_enroll_notes.json` 被小程序主包 compact 消费（详情页招生计划视图），勿手改格式。
