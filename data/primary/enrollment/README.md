# 小学招生（enrollment）

2026 年广州市各区公办小学招生地段/计划的解析与匹配产物。与小升初/初中招生（`data/primary/transition/`）**完全分离**：本目录只做小学招生。

## 目录结构

```
enrollment/
├── raw/        政府源文件（原文件只读归档：xls/xlsx/pdf/png/doc/docx）
├── parsed/     解析层（可审计可重跑）
│   ├── _transcripts/   A 层：parse_*.py 从 raw 提取的结构化 JSON（含 OCR 缓存 ocr/）
│   └── dist/           B 层：build_primary_2026.py 输出 2026-<区>.json
│                      （匹配产物，保留 school/poi_name/lng/lat 等调试字段）
├── src/        手工源文件（业务确认口径，如 leftover_notes.json 招生区域承接说明表）
├── dist/       C 层最终运行时产物（build_enrollment_all.py 合并输出）
│   └── 2026-all.json   records/minban 瘦身（无 school 名，按 school_id 联查实体表/POI 表）
├── scripts/    生产脚本
│   ├── parse_*.py         A 层：raw → parsed/_transcripts（openpyxl/docx/OCR）
│   ├── build_primary_2026.py  B 层：_transcripts → dist/2026-<区>.json（SchoolMatcher 匹配实体表）
│   ├── build_read_transcripts.py  天河/黄埔 Read 直读转录复现（read_transcripts/*.py 数据）
│   ├── read_transcripts/  天河/黄埔转录数据文件（人工核对转写，权威源）
│   └── ocr/               扫描件 OCR（vision_ocr.py）
├── test/       快照测试（check_enrollment_snapshot.py + snapshots/ 基线，npm run check 链）
├── docs/       业务文档（数据源调研、转录判定结论等）
└── README.md
```

## 流水线（ABC 三层，2026-09-22）

```
raw/ 政府源文件
  │  A 层（parse_*.py / build_read_transcripts.py，可复现转录）
  ▼
parsed/_transcripts/*.json
  │  B 层（build_primary_2026.py，纯 SchoolMatcher 匹配 data/registry/entity）
  ▼
parsed/dist/2026-<区>.json   ← B 层匹配产物（保留 school/poi_name/lng/lat 调试字段）
  │  C 层（build_enrollment_all.py 合并瘦身）
  ▼
dist/2026-all.json           ← 最终运行时产物（无 school 名，按 school_id 联查）
```

## 数据源（官方 2026-04-28 前后发布）

| 区 | raw 原文件 | 关键内容 | 解析脚本 |
|---|---|---|---|
| 越秀 | `yuexiu_2026_official.doc`（招生简章附件5） | 51 所小学按行政街+路段列登记范围，块尾含班数 | `parse_yuexiu_diduan.py`（textutil 转文本） |
| 荔湾 | `liwan_2026_primary_a1.docx` / `a4.docx`（细则附件1/附件4） | 附件1 计划班数 60 所；附件4 服务地段（街道/社区/路街巷） | `parse_liwan_primary.py`（docx 解析） |
| 海珠 | `haizhu_2026_official.png`（地段表）＋ `haizhu_2026_gongban_plan.png`（计划表）＋ `haizhu_2026_minban_plan.png`（民办计划） | 78 条学校+服务地段（街道+社区①…，无班数，班数另表） | `parse_haizhu_diduan.py` / `parse_haizhu_plan.py` / `parse_haizhu_minban.py`（Vision OCR） |
| 天河 | `tianhe_2026_official.pdf`（细则附件5，66 页扫描件，地段表在第 35-42 页） | 76 所小学：招生报名地段范围/班数/电话/备注 | `build_read_transcripts.py`（Read 直读转写） |
| 番禺 | `panyu_2026_official.xls`（4 sheet） | 公办小学地段+计划 150 所 / 民办招生计划（班数+人数） | `parse_panyu_official.py`（xlrd） |
| 白云 | `baiyun_2026_official.xlsx`（sheet「公办小学」） | 138 所：学校/地段/计划 | `parse_baiyun_primary.py`（openpyxl） |
| 黄埔 | `huangpu_2026_official.pdf`（细则附件4 地段 95 校 + 附件6 计划 94 条） | 招生地段范围（门牌/楼盘级） | `build_read_transcripts.py`（Read 直读转写） |

完整采集方案/政策口径/字段设计见 `docs/数据源调研.md`（2026-09-08 调研存档）。

## A 层（转录）

每个 parse_*.py 从 `raw/` 原文件读取，输出 `parsed/_transcripts/<区>_2026.json`。扫描件（海珠 png、天河/黄埔 PDF）走 `scripts/ocr/vision_ocr.py` 或 Read 直读。

> **2026-09-22 官方核验整改**：zone 文本以官方原文为准（多引擎 OCR 交叉 + 真实地名/社区名录 + 官方历年表判定），
> 判定结论固化在两处权威源，重跑 A 层即可复现当前转录：
> - 海珠 zone：以 `parsed/_transcripts/haizhu_zone_reference.json` 为判定基准（parse_haizhu_diduan.py 融合覆盖）。
>   **教训**：该基准曾按 Vision OCR 行归属误改凤江/大江苑/第三实验段落归属，用户抽查官方原图实锤后回退原版
>   （OCR 行归属不可靠，无强证据一律维持原版）；仅保留有区划代码强证据的绿翠=江丽社区（440105001124）。
> - 黄埔 zone：`scripts/read_transcripts/huangpu_2026_zone.py` 数据文件已按官方 PDF 原图修正
>   （新岸街/机关村/榕景苑/香雪公馆/香雪华府/凤湖花园/宏康和苑/铁铮括号位置/怡园北无前缀等），
>   修正均有官方 PDF 文字索引/媒体/历年表多源佐证。
>
> 复现命令（raw → parsed → dist 全链路）：
> ```
> python3 data/primary/enrollment/scripts/parse_yuexiu_diduan.py      # 越秀
> python3 data/primary/enrollment/scripts/parse_liwan_primary.py     # 荔湾
> python3 data/primary/enrollment/scripts/parse_baiyun_primary.py    # 白云
> python3 data/primary/enrollment/scripts/parse_panyu_official.py    # 番禺
> python3 data/primary/enrollment/scripts/parse_haizhu_diduan.py     # 海珠（含 zone 判定基准融合）
> python3 data/primary/enrollment/scripts/parse_haizhu_plan.py       # 海珠计划表（班数）
> python3 data/primary/enrollment/scripts/parse_haizhu_minban.py     # 海珠民办计划
> python3 data/primary/enrollment/scripts/build_read_transcripts.py  # 天河/黄埔 read_transcripts → 转录 json
> python3 data/primary/enrollment/scripts/build_primary_2026.py      # B 层：转录 → dist/2026-<区>.json
> npm run check                                                      # 全量检查
> ```
>
> 注意：天河/黄埔转录的唯一权威源是 `read_transcripts/*.py`（人工核对转写）——历史 OCR 方案
> `parse_tianhe.py` 已删除，避免误跑覆盖权威转录。

## B 层匹配

`build_primary_2026.py` 以转录为源，逐个学校名调 `SchoolMatcher.resolve / resolve_all`：

- **带校区名**的记录 → `resolve` 单校区匹配；
- **无校区名的法人多校区**（官方未列校区）→ `resolve_all` 展开为全部校区记录；
- **不读任何手工锚点表**（`_anchors.json` 已废弃删除）。名字映射全部下沉到实体表别名层（`data/registry/entity/scripts/build_entities.py` 的 `OFFICIAL_PRIMARY_ALIAS` / `PRIMARY_CAMPUS_ALIAS`）。

## 海珠班数挂载（公办计划表）

海珠地段表只有「学校/服务地段」两列（无班数），班数来自官方另发的《2026年海珠区公办小学招生计划表》
（`raw/haizhu_2026_gongban_plan.png`，学校+班数双列 80 条）。`parse_haizhu_plan.py` 转录到
`parsed/_transcripts/haizhu_2026_plan.json`，B 层匹配后按以下顺序挂 `plan_classes`：

1. 官方原文名精确（与计划表同源，如「第二实验小学（南校区）」）；
2. poi 校区名精确/前缀（如「南武小学(北校区)」→4、「宝玉直实验小学(南边路校区)」↔计划表「南边校区」→3）；
3. poi 名精确；
4. 官方名整校合计（本部记录如「南武小学」=南5+北4=9）；
5. poi 校区 + 官方整校单条（如「龙潭小学(龙潭立交)」↔整校 2、万松园两校区各挂官方整校 4）。

转录细节（双列重建/行聚类容差/校正表）见 `scripts/parse_haizhu_plan.py` 头注。

## minban（民办小学招生计划）

官方文件「民办招生计划」只有**计划班数/人数、无招生地段**（民办不划地段，报名超计划摇号），
故不进公办 records，作为独立 `minban` 段输出（当前番禺官方 xls 与海珠官方计划表公布民办计划）：

- 字段：`school / district / plan_classes / plan_count / school_id / poi_name / lng / lat`
- 小学一年级计划为 `/`/缺省 的民办（2026 不招小学一年级，如祈福英语实验学校、康乐中学/海珠中学仅初中）不纳入
- 匹配同样走 SchoolMatcher（实体表），未命中宁缺

## 产物结构

```json
{
  "year": 2026,
  "district": "海珠区",
  "source": "海珠区教育局2026",
  "source_url": "https://www.haizhu.gov.cn/...",
  "records": [
    {"school": "赤岗小学", "district": "海珠区", "plan_classes": 4, "zone": "赤岗街：①竹园社区；...",
     "note": "", "phone": "", "source": "海珠区教育局2026", "school_id": "gz-440105-24c1be5c",
     "poi_name": "赤岗小学", "lng": 113.33072, "lat": 23.090504}
  ],
  "unmatched": [],
  "ambiguous": [],
  "poi_leftover": [],
  "map_fail": [],
  "minban": []
}
```

## 当前状态（2026-09-22，全链路重跑验证）

| 区 | 官方记录 | 匹配（含校区展开） | 未匹配 | 歧义 |
|---|---|---|---|---|
| 越秀 | 51 | 63 | 0 | 0 |
| 荔湾 | 60 | 61 | 0 | 0 |
| 海珠 | 78 | 94 | 0 | 0 |
| 天河 | 76 | 93 | 0 | 0 |
| 番禺 | 150 | 151 | 0 | 0 |
| 白云 | 138 | 161 | 0 | 0 |
| 黄埔 | 95 | 97 | 0 | 0 |

未匹配/歧义均为 0；`poi_leftover` 为实体表有、官方未招生记录的 POI（正常，非错误）。

### records 字段口径（2026-09-22 C 层）

C 层 `dist/2026-all.json` 的 records 只存 `school_id` + 招生特有字段
（`plan_classes/zone/note/phone/source`）+ `district`（区标识，番禺为片区名，另有 `adcode` 分组，
compact 还原后删除）+ 无 `school/poi_name/lng/lat`——名称/坐标按 school_id 从实体表/POI 表联查
（实体表 `data/registry/entity/dist/entities.json`、POI `data/poi/dist/primary_poi.json`）。
**调试看 B 层** `parsed/dist/2026-<区>.json`（含 school/poi_name/lng/lat 全字段）。
官方招生名（如「黄埔区CPPQ-A4-2地块…暂定名」）留底在 `parsed/_transcripts/<区>_2026.json`（A 层转录）。

> TODO（官方名统一展示）：理论上对用户展示用官方名比 POI 名更准确，但官方名不带校区
> 不能直接用（如「九龙第二小学」官方 3 行对应 3 个校区），统一展示方案待定。

### 招生区域承接说明（src/leftover_notes.json）

原校 2026 官方无招生计划但保留遗留学生升学（如东区小学/禾丰小学）：src 表维护
`原校 school_id → 承接说明`，B 层为原校生成一条 `plan_classes=null`、`zone=承接说明` 的
记录（详情页招生区域直接展示「2026 年起招生区域已改由X承接招生」），原校同时从
`poi_leftover` 移除；孤儿判定豁免同表（原校非孤儿）。

## 测试

`test/check_enrollment_snapshot.py`：重跑 B 层到临时目录，与独立基线 `test/snapshots/enrollment_snapshot.json`
全等对比，diff 逐条暴露增(+)/删(-)/改(~)。基线更新：`python3 data/primary/enrollment/test/check_enrollment_snapshot.py --update-snapshot`
（先看 diff 确认是有意变更，禁止改产物掩盖）。已接入 `npm run check`。

## 重跑

```bash
# 全部：A 层（转录）+ B 层（匹配）+ C 层（合并瘦身）
# A 层命令见上（parse_*.py + build_read_transcripts.py）
python3 data/primary/enrollment/scripts/build_primary_2026.py all   # B 层 → parsed/dist/2026-<区>.json
python3 data/primary/enrollment/scripts/build_enrollment_all.py     # C 层 → dist/2026-all.json
# 单区 B 层（转录已存在时）
python3 data/primary/enrollment/scripts/build_primary_2026.py yuexiu
```

B 层依赖 `data/registry/entity/dist/entities.json` 与 `data/poi/dist/*_poi.json`，先跑 `data/registry/entity/scripts/build_entities.py` 保证实体表最新。
