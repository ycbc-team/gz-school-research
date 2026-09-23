# 公办初中招生（middle/enrollment）

2026 年广州市各区公办初中招生计划（初中视角招生）。2026-09-23 由 `data/primary/enrollments/`（旧 dist 目录）与
`scripts/primary/build_middle_enrollment.py` 迁入本业务目录，按 `raw / parsed / src / scripts / dist / docs / test` 分层，
与小学招生（`data/primary/enrollment/`）完全分离。

## 目录结构

```
middle/enrollment/
├── raw/        本目录无专属官方源（2026-09-23 清空）；官方源文件统一共享 `data/enrollment/raw/`
├── parsed/
│   └── _transcripts/   初中转录 json（A 层，parse_*.py 从共享 raw/官网提取）
│       ├── baiyun_2026_juniors.json   白云 59 初中（共享 xlsx「公办初中」sheet，有班数/对口小学）
│       ├── liwan_2026_groups.json     荔湾 15 行派位分组（共享 a3.docx，无班数/范围）
│       ├── yuexiu_2026_juniors.json   越秀 11 组×10 初中（2022 官方分组表网页，无班数）
│       ├── haizhu_2026_juniors.json   海珠 10 组派位+直升+28 校班数（官网问答附件1+计划表）
│       ├── tianhe_2026_juniors.json   天河 24 公办+3 企事业+24 民办初中（PDF 附件6/7/8，有班数）
│       └── huangpu_2026_juniors.json  黄埔 7 派位组+22 直升组（PDF 附件5，无班数）
│       └── （番禺）→ 共享转录 `data/primary/enrollment/parsed/_transcripts/panyu_2026_official.json`（初中 sheet，有班数/范围）
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

> 越秀/海珠/天河/黄埔 4 区转录（`parsed/_transcripts/<区>_2026_juniors.json`）为 2026-09-23
> Read 多模态直读官网（越秀/海珠网页、天河/黄埔 PDF 扫描件）后落盘的 A 层转录，无独立 parse 脚本
> （与小学侧天河/黄埔 read_transcripts 同一方法）；数据源 URL 记在各转录 json 的 `source_url`。

## 数据源（全部为各区教育局 2026 官方文件）

| 区 | 官方源 | 本业务解析/构建路径 | 说明 |
|---|---|---|---|
| 番禺 | 《2026 招生计划、招生地段及条件》官方 xls（4 sheets） | 共享转录 `data/primary/enrollment/parsed/_transcripts/panyu_2026_official.json`「公办初中招生范围、计划」sheet | 官方 xls 小学+初中+民办共用，权威源在共享 raw `data/enrollment/raw/panyu_2026_official.xls` + 小学侧转录（单一权威源，不复制） |
| 白云 | 2026 招生计划附表2 官方 xlsx | 共享 raw `data/enrollment/raw/baiyun_2026_official.xlsx` → `parsed/_transcripts/baiyun_2026_juniors.json`（「公办初中」sheet） | xlsx 含「公办小学」sheet 归小学招生；解析脚本从共享位置读取 |
| 荔湾 | 2026 公办初中招生方案附件3（派位分组） | 共享 raw `data/enrollment/raw/liwan_2026_a3.docx` → `parsed/_transcripts/liwan_2026_groups.json` | a1–a5 全附件共享（2026-09-23 迁入 data/enrollment/raw） |
| 越秀 | 2022 官方分组表（post_8301356，2026 细则确认稳定） | `parsed/_transcripts/yuexiu_2026_juniors.json`（11 组×10 初中，2026-09-23 Read 网页直读转录） | 无班数/范围（官方分组表仅组结构）；中学简称已展开为官方全称 |
| 海珠 | 2026 初中招生问答附件1 派位组 + 正文直升（mpost_10799155）+ 公办初中计划表（mpost_10788494） | `parsed/_transcripts/haizhu_2026_juniors.json`（10 组+19 直升+28 校班数，2026-09-23 网页直读） | 班数来自计划表网页直读（此前缺失，现可直建）；范围=派位组结构 |
| 天河 | 2026 招生细则 PDF 附件6 初中划片及计划表 + 附件7 企事业办 + 附件8 民办 | `parsed/_transcripts/tianhe_2026_juniors.json`（24 公办+3 企事业+24 民办初中，2026-09-23 Read 直读） | 有班数/划片范围；22/23 号两校区合并行班数待复核 |
| 黄埔 | 2026 招生细则 PDF 附件5 小升初派位及直升分组表 | `parsed/_transcripts/huangpu_2026_juniors.json`（7 派位组+22 直升组，2026-09-23 Read 直读） | 无班数/范围（官方分组表无计划列） |

> 越秀/海珠初中源为官网网页（raw 无对应文件）；天河/黄埔初中源为共享 raw PDF 扫描件（Read 多模态直读）。
> 转录保留官方原文（如天河"广州市第18中学"阿拉伯数字、黄埔"长岭·雅居"），与脚本历史转录的
> 中文数字/半角点写法差异由构建层统一规范，非数据差异。

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

## 当前状态（2026-09-23 A 层转录补齐后）

| 区 | 转录记录 | 官方班数 | 官方范围 | 现状构建 |
|---|---|---|---|---|
| 番禺 | 62 行（sheet） | ✓ | ✓ | 官方 xls 直建 |
| 白云 | 59 | ✓ | ✓（对口小学） | 官方 xlsx 直建 |
| 荔湾 | 15 行派位组 | ✗（官方源无） | ✗（组结构） | 官方派位组直建 |
| 越秀 | 11 组×10 初中 | ✗（官方源无） | ✗（组结构） | **仍 xiaoshengchu 反推（转录已就绪，待直建）** |
| 海珠 | 10 组+19 直升+28 校班数 | ✓（计划表） | ✗（组结构） | **仍 xiaoshengchu 反推（转录已就绪，待直建）** |
| 天河 | 24 公办+3 企事业+24 民办 | ✓ | ✓（划片+对口小学） | **仍 xiaoshengchu 反推（转录已就绪，待直建）** |
| 黄埔 | 7 派位组+22 直升组 | ✗（官方源无） | ✗（组结构） | **仍 xiaoshengchu 反推（转录已就绪，待直建）** |

> 7 区转录已全部落地 `parsed/_transcripts/`（2026-09-23）。4 区（越秀/海珠/天河/黄埔）的 dist 构建
> **尚未切换为官方直建**（build_middle_enrollment.py 仍走 build_from_xiaoshengchu 反推），直建为下一步工程。
> 海珠班数（28 校）与天河班数/划片（24+3+24）为本轮新转录，直建后可补齐 plan_classes/scope。

## 各区转录字段对齐（2026-09-23）

目标 schema（dist records）：`school / school_id / plan_classes / scope / mechanism / group_members`。

| 区 | school | plan_classes | scope | mechanism | group_members |
|---|---|---|---|---|---|
| 白云 | seq/pian/jiedao/school | plan | feed（对口小学文本） | 摇号/多校推断 | 无（对口小学非组） |
| 番禺 | school | plan | scope（招生范围） | 电脑抽签/派位/单校 | 亚运城派位组成员 |
| 荔湾 | 中学列 | ✗ 无 | ✗ 无 | 派位组 | ✓（组内中学并集） |
| 越秀 | juniors（10/组） | ✗ 无 | ✗ 无 | 派位组 | ✓（组内 10 校） |
| 海珠 | groups 内中学 | ✓ 28 校（plan_classes） | ✗ 无 | 派位组+直升 | ✓（组内并集） |
| 天河 | gongban.school | ✓（含特教 4+1） | ✓ zone（划片） + primaries（对口小学） | 单校划片/直升/部分派位（附件10） | ✗（划片非组） |
| 黄埔 | paiwei/zhisheng juniors | ✗ 无 | ✗ 无 | 派位组+直升组 | ✓（组内并集） |

**对齐结论**：
1. **可统一**：`school`（校名经构建层统一规范，官方原文保留在转录层）+ `mechanism` + `group_members`（派位/直升组）。
2. **scope 语义分三档**：对口小学列表（白云/天河 primaries/黄埔/海珠组）/ 地段文本（天河 zone/番禺范围）/ 无（荔湾/越秀/黄埔）。
   构建层建议加 `scope_kind`（`primaries | zone | group | none`）区分，避免前端渲染歧义。
3. **plan_classes 非全区可得**：白云/番禺/海珠/天河有官方班数；荔湾/越秀/黄埔官方文件无班数
   （官方只给分组），直建后仍为 null——与现有荔湾口径一致，前端已兼容 null。
4. **官方原文 vs 脚本规范名**：天河"第18中学"（阿拉伯）vs 脚本"第十八中学"（中文）、黄埔"长岭·雅居"（全角点）
   等写法差异，转录层保留官方原文，构建层（SchoolMatcher）统一。

## 已知缺口与风险（重构待办）

1. **4 区直建（方向修正待办，A 层转录已就绪）**：越秀/海珠/天河/黄埔 4 区转录文件已落地
   `parsed/_transcripts/<区>_2026_juniors.json`（2026-09-23），但 `build_middle_enrollment.py`
   仍用 `build_from_xiaoshengchu` 反推。下一步：为 4 区写直建分支（读转录文件），
   替换反推路径，然后**让 xiaoshengchu 从初中招生公示反推**（正确方向，见下）。
   海珠班数（28 校）/天河班数+划片（24+3+24）直建后即可补齐 plan_classes/scope。
2. **推导方向（2026-09-23 用户确认）**：小学升学（xiaoshengchu）官方口径本就来自初中招生公示（6/7 区），
   因此正确方向是 **xiaoshengchu 基于初中招生产物/公示反推**，初中招生基于官方文件直建；现状 4 区
   middle_enrollment 由 xiaoshengchu 反推属历史遗留，待第 1 项补齐后反转。
3. **转录层已知小差异**：天河附件6 合计 288+2（特教）与逐行和有差（22/23 号两校区合并行班数待复核）；
   黄埔派位 5 组"长岭·雅居"与脚本"长岭.雅居"标点差异（转录保官方原文）；天河官方小学名用简称
   （华农附小/握河小学等），构建层需别名映射（脚本 TH_FEED 已有全称键）。
4. **group_members 并集缺失**：同一初中出现在多个派位组时，反推路径只回填首个 group 的成员
   （荔湾官方路径 build_liwan 处理了并集，反推路径没有）。
5. **共享源不复制**：官方源文件统一在 `data/enrollment/raw/`（小学/小升初/初中共用），番禺/白云转录
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
