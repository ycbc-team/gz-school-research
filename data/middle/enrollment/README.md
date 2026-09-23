# 公办初中招生（middle/enrollment）

2026 年广州市各区公办初中招生计划（初中视角招生）。2026-09-23 由 `data/primary/enrollments/`（旧 dist 目录）与
`scripts/primary/build_middle_enrollment.py` 迁入本业务目录，按 `raw / parsed / src / scripts / dist / docs / test` 分层，
与小学招生（`data/primary/enrollment/`）完全分离。

## 目录结构

```
middle/enrollment/
├── raw/        本目录无专属官方源（2026-09-23 清空）；官方源文件统一共享 `data/enrollment/raw/`
├── parsed/
│   └── _transcripts/   初中转录 json（A 层，parse_*.py 从共享 raw 提取）
│       ├── baiyun_2026_juniors.json  白云 59 初中（共享 xlsx「公办初中」sheet）
│       └── liwan_2026_groups.json    荔湾 15 行派位分组（共享 a3.docx）
├── src/        手工源文件（业务确认口径）
│   └── middle_enroll_notes.json  初中录取备注（如执信水荫：仅初三就读）
├── scripts/    生产脚本
│   ├── parse_baiyun_juniors.py    白云初中转录（共享 raw→parsed，openpyxl）
│   ├── parse_liwan_groups.py      荔湾派位组转录（共享 raw→parsed，docx）
│   └── build_middle_enrollment.py 构建 dist（B 层，SchoolMatcher 匹配实体表）
├── dist/       B 层最终运行时产物 middle_enrollment_2026_<区>.json（7 区）
├── docs/       业务文档（本 README 为权威说明）
└── test/       快照测试（check_middle_snapshot.py + snapshots/ 基线，npm run check 链）
```

## 构建链路（raw → parsed → dist，可重跑）

```
共享官方源（data/enrollment/raw/）──parse_baiyun_juniors.py / parse_liwan_groups.py──▶ parsed/_transcripts/*.json
parsed/_transcripts/*.json ──build_middle_enrollment.py──▶ dist/middle_enrollment_2026_<区>.json
```

复现命令：

```bash
python3 data/middle/enrollment/scripts/parse_baiyun_juniors.py      # 白云 59 初中（读共享官方 xlsx）
python3 data/middle/enrollment/scripts/parse_liwan_groups.py       # 荔湾派位组 15 行（读共享 raw/liwan_2026_a3.docx）
python3 data/middle/enrollment/scripts/build_middle_enrollment.py  # 7 区 dist
```

## 数据源（全部为各区教育局 2026 官方文件）

| 区 | 官方源 | 本业务解析/构建路径 | 说明 |
|---|---|---|---|
| 番禺 | 《2026 招生计划、招生地段及条件》官方 xls（4 sheets） | 共享转录 `data/primary/enrollment/parsed/_transcripts/panyu_2026_official.json`「公办初中招生范围、计划」sheet | 官方 xls 小学+初中+民办共用，权威源在共享 raw `data/enrollment/raw/panyu_2026_official.xls` + 小学侧转录（单一权威源，不复制） |
| 白云 | 2026 招生计划附表2 官方 xlsx | 共享 raw `data/enrollment/raw/baiyun_2026_official.xlsx` → `parsed/_transcripts/baiyun_2026_juniors.json`（「公办初中」sheet） | xlsx 含「公办小学」sheet 归小学招生；解析脚本从共享位置读取 |
| 荔湾 | 2026 公办初中招生方案附件3（派位分组） | 共享 raw `data/enrollment/raw/liwan_2026_a3.docx` → `parsed/_transcripts/liwan_2026_groups.json` | a1–a5 全附件共享（2026-09-23 迁入 data/enrollment/raw） |
| 越秀/海珠/天河/黄埔 | 各区 2026 招生细则/初中计划表（doc/png/pdf 扫描件，共享 `data/enrollment/raw/`） | **由 `data/primary/transition/dist/xiaoshengchu_<区>.json` 反推**（`build_from_xiaoshengchu`） | **方向反了（2026-09-23 修正）**：应初中招生从官方初中文件直建、xiaoshengchu 从初中招生公示反推；现 4 区反推仅过渡，`plan_classes/scope` 留空（source 标注「待补」） |

## 产物结构

```json
{
  "year": 2026, "district": "海珠区",
  "source": "由 xiaoshengchu_haizhu.json 反推（班数/范围 raw 未抽，待补）",
  "source_url": null,
  "mechanisms": {"single_zone": {...}, "group_paidui": {...}, "single_lottery": {...}},
  "records": [
    {"school": "广州市第五中学", "school_id": "gz-440105-...", "plan_classes": null,
     "scope": null, "mechanism": "group_paidui", "mechanism_note": "海珠区…电脑派位", "group_members": [...]}
  ]
}
```

`mechanism` 区级枚举（UI 据此渲染 label/lose_text）：`single_zone` 单校划片 / `group_paidui` 多校电脑派位 /
`single_lottery` 单校电脑抽签（未中签回原学区）。

## 当前状态（2026-09-23 迁移后）

| 区 | 记录数 | plan_classes | scope | 构建方式 |
|---|---|---|---|---|
| 番禺 | 52 | ✓ 全部有 | ✓ 全部有 | 官方 xls 直建 |
| 白云 | 59 | ✓ 全部有 | ✓ 全部有 | 官方 xlsx 直建 |
| 荔湾 | 31 | ✗ 全部空 | ✗ 全部空 | 官方派位组（官方源无班数/范围） |
| 越秀 | 26 | ✗ 全部空 | ✗ 全部空 | xiaoshengchu 反推 |
| 海珠 | 26 | ✗ 全部空 | ✗ 全部空 | xiaoshengchu 反推 |
| 天河 | 25 | ✗ 全部空 | ✗ 全部空 | xiaoshengchu 反推 |
| 黄埔 | 36 | ✗ 全部空 | ✗ 全部空 | xiaoshengchu 反推 |

合计 255 条，其中 144 条（56%）缺班数/范围（荔湾 31 + 反推 4 区 113）。

## 已知缺口与风险（重构待办）

1. **4 区反推（方向修正待办）**：越秀/海珠/天河/黄埔初中侧 raw→转录未抽，班数/范围全空。官方初中文件都在
   共享 `data/enrollment/raw/`（越秀 doc/海珠 png/天河 pdf/黄埔 pdf 含对应初中附件），补齐解析即可
   **改为官方直建，并让 xiaoshengchu 从初中招生公示反推**（正确方向，见下）。
2. **推导方向（2026-09-23 用户确认）**：小学升学（xiaoshengchu）官方口径本就来自初中招生公示（6/7 区），
   因此正确方向是 **xiaoshengchu 基于初中招生产物/公示反推**，初中招生基于官方文件直建；现状 4 区
   middle_enrollment 由 xiaoshengchu 反推属历史遗留，待第 1 项补齐后反转。
2. **反推机制判定是启发式**：`build_from_xiaoshengchu` 从小学侧 group 名推断机制，`single_lottery` 在反推路径
   永远不会出现（推断分支未写）。
3. **group_members 并集缺失**：同一初中出现在多个派位组时，反推路径只回填首个 group 的成员
   （荔湾官方路径 build_liwan 处理了并集，反推路径没有）。
4. **共享源不复制**：官方源文件统一在 `data/enrollment/raw/`（小学/小升初/初中共用），番禺/白云转录
   权威源在 `data/primary/enrollment/parsed/_transcripts/`；本业务只读引用，改动须同时考虑小学链。

## 测试

`test/check_middle_snapshot.py`：重跑 `build_middle_enrollment.py --out-dir` 到临时目录（不碰 dist），
提取 records 结构化快照与独立基线全等对比；改动须 `--update-snapshot` 显式更新。
已接入 `npm run check`。`data/registry/group/test/check_groups_drift.py` 另有「重跑=入库」全等比对。

## 下游消费

- Web 端：`apps/web/src/data/index.ts` 经 compact.mjs 编译加载（`middle/enrollment/dist/*.js`），组装 `middleEnrollments` loader；
- 小程序主包不消费本产物（详情页分包经 Web 同构）；
- 数据质量回归：`scripts/data_quality_test.py`（school_id 存在性/区一致性/民办 0 容忍/孤儿判定）；
- 详情页初中招生视图：`middle_enroll_notes.json`（src/）录取备注 + 本产物招生计划。
