# 小学招生（enrollment）

2026 年广州市各区公办小学招生地段/计划的解析与匹配产物。与小升初/初中招生（`data/primary/transition/`）**完全分离**：本目录只做小学招生。

## 目录结构

```
enrollment/
├── raw/        政府源文件（原文件只读归档，含 xls/xlsx/pdf/png/doc/docx）
├── parsed/     解析层（A 层转录产物，可审计可重跑）
│   └── _transcripts/   parse_*.py 从 raw 提取的结构化 JSON
├── dist/       最终运行时产物（B 层，build_primary_2026.py 输出）
│   └── 2026-<区>.json   含 records（公办）/ minban（民办小学招生计划）/ unmatched / ambiguous
├── scripts/    生产脚本
│   ├── parse_*.py         A 层：raw → parsed/_transcripts（openpyxl/docx/OCR）
│   ├── build_primary_2026.py  B 层：_transcripts → dist/2026-<区>.json（SchoolMatcher 匹配实体表）
│   ├── audit_*.py         转录抽查（与 WebFetch/pdftotext 交叉比对）
│   ├── read_transcripts/  各区转录复现/核查脚本
│   └── ocr/               扫描件 OCR（vision_ocr.py）
├── src/        手工源文件（_anchors.json：历史手工锚点表，已废弃仅存档，不再参与匹配）
├── docs/       业务文档（转录差异、新旧产物差异审计等）
└── README.md
```

## 流水线

```
raw/ 政府源文件
  │  A 层（parse_*.py，可复现转录）
  ▼
parsed/_transcripts/*.json
  │  B 层（build_primary_2026.py，纯 SchoolMatcher 匹配 data/registry/entity）
  ▼
dist/2026-<区>.json   ← 消费产物（最终运行时产物层）
```

### A 层（转录）

> 2026-09-22 官方核验整改：zone 文本以官方原文为准（多引擎 OCR 交叉 + 真实地名/社区名录 + 官方历年表判定），
> 判定结论固化在两处权威源，重跑 A 层即可复现当前转录：
> - 海珠 zone：以 `parsed/_transcripts/haizhu_zone_reference.json` 为判定基准（parse_haizhu_diduan.py 融合覆盖）。
>   **2026-09-22 教训**：该基准曾按 Vision OCR 行归属误改凤江/大江苑/第三实验段落归属，
>   用户抽查官方原图实锤后回退原版（OCR 行归属不可靠，无强证据一律维持原版）；
>   仅保留有区划代码强证据的绿翠=江丽社区（440105001124）。
> - 黄埔 zone：`scripts/read_transcripts/huangpu_2026_zone.py` 数据文件已按官方 PDF 原图修正
>   （新岸街/机关村/榕景苑/香雪公馆/香雪华府/凤湖花园/宏康和苑/铁铮括号位置/怡园北无前缀等）。
> 逐条判定依据见 `docs/haizhu_zone_diff_20260921.md`、`docs/huangpu_zone_diff_20260921.md`。
>
> 复现命令（raw → parsed → dist 全链路）：
> ```
> python3 data/primary/enrollment/scripts/parse_haizhu_diduan.py      # 海珠 raw PNG → haizhu_2026.json（含 zone 判定基准融合）
> python3 data/primary/enrollment/scripts/build_read_transcripts.py  # 天河/黄埔 read_transcripts 数据 → 转录 json
> python3 data/primary/enrollment/scripts/build_primary_2026.py      # B 层：转录 → dist/2026-<区>.json
> npm run check                                                      # 全量检查
> ```

### A 层（转录）
每个 parse_*.py 从 `raw/` 原文件读取，输出 `parsed/_transcripts/<区>_2026.json`。扫描件（海珠 png、天河/黄埔 PDF）走 `scripts/ocr/vision_ocr.py`，产出后用 `audit_*.py` 与 WebFetch/pdftotext 等交叉比对。

### B 层（匹配）
### minban（民办小学招生计划）

官方文件「民办招生计划」只有**计划班数/人数、无招生地段**（民办不划地段，报名超计划摇号），
故不进公办 records，作为独立 `minban` 段输出（当前番禺官方 xls 与海珠官方计划表公布民办计划）：

- 字段：`school / district / plan_classes / plan_count / school_id / poi_name / lng / lat`
- 小学一年级计划为 `/`/缺省 的民办（2026 不招小学一年级，如祈福英语实验学校、康乐中学/海珠中学仅初中）不纳入
- 匹配同样走 SchoolMatcher（实体表），未命中宁缺

### B 层匹配

`build_primary_2026.py` 以转录为源，逐个学校名调 `SchoolMatcher.resolve / resolve_all`：

- **带校区名**的记录 → `resolve` 单校区匹配；
- **无校区名的法人多校区**（官方未列校区）→ `resolve_all` 展开为全部校区记录；
- **不读任何手工锚点表**（`_anchors.json` 已废弃）。名字映射全部下沉到实体表别名层（`data/registry/entity/scripts/build_entities.py` 的 `OFFICIAL_PRIMARY_ALIAS` / `PRIMARY_CAMPUS_ALIAS`）。

### 海珠班数挂载（公办计划表）

海珠地段表只有「学校/服务地段」两列（无班数），班数来自官方另发的《2026年海珠区公办小学招生计划表》
（`raw/haizhu_2026_gongban_plan.png`，学校+班数双列 80 条）。`parse_haizhu_plan.py` 转录到
`parsed/_transcripts/haizhu_2026_plan.json`，B 层匹配后按以下顺序挂 `plan_classes`：

1. 官方原文名精确（与计划表同源，如「第二实验小学（南校区）」）；
2. poi 校区名精确/前缀（如「南武小学(北校区)」→4、「宝玉直实验小学(南边路校区)」↔计划表「南边校区」→3）；
3. poi 名精确；
4. 官方名整校合计（本部记录如「南武小学」=南5+北4=9）；
5. poi 校区 + 官方整校单条（如「龙潭小学(龙潭立交)」↔整校 2、万松园两校区各挂官方整校 4）。

转录细节（双列重建/行聚类容差/校正表）见 `scripts/parse_haizhu_plan.py` 头注与 `docs/haizhu_zone_diff_20260921.md`。

产物结构（与历史格式一致）：

```json
{
  "year": 2026,
  "district": "yuexiu",
  "source": "…官方文件名/URL…",
  "source_url": "…",
  "records": [ {"school": "…", "school_id": "gz-…", "lng": …, "lat": …, "plan": …} ],
  "unmatched": ["…"],
  "ambiguous": [],
  "poi_leftover": [],
  "map_fail": []
}
```

## 当前状态（2026-09-21）

| 区 | 官方记录 | 匹配 | 未匹配（真缺） |
|---|---|---|---|
| 越秀 | 51 | 62（含展开） | 1 |
| 荔湾 | 60 | 57 | 4 |
| 海珠 | 78 | 92（全部挂计划班数） | 2 |
| 天河 | 76 | 91 | 2 |
| 番禺 | 150 | 150 | 1 |
| 白云 | 138 | 152 | 9 |
| 黄埔 | 95 | 85 | 12 |

未匹配均为 POI/实体表无点位的真缺（新建/在建/暂定名校区），宁缺不误配。详情见 `docs/2026_old_new_diff_audit.md`。

## 重跑

```bash
# 全部：A 层（转录）+ B 层（匹配）
python3 data/primary/enrollment/scripts/build_primary_2026.py all
# 单区 B 层（转录已存在时）
python3 data/primary/enrollment/scripts/build_primary_2026.py yuexiu
```

B 层依赖 `data/registry/entity/dist/entities.json` 与 `data/poi/dist/*_poi.json`，先跑 `data/registry/entity/scripts/build_entities.py` 保证实体表最新。
