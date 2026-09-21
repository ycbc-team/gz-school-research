# 小学招生（enrollment）

2026 年广州市各区公办小学招生地段/计划的解析与匹配产物。与小升初/初中招生（`data/primary/transition/`）**完全分离**：本目录只做小学招生。

## 目录结构

```
enrollment/
├── raw/        政府源文件（原文件只读归档，含 xls/xlsx/pdf/png/doc/docx）
├── parsed/     解析产物
│   ├── _transcripts/   A 层转录（parse_*.py 从 raw 提取的结构化 JSON，可审计可重跑）
│   └── 2026-<区>.json  B 层最终匹配产物（build_primary_2026.py 输出）
├── scripts/    生产脚本
│   ├── parse_*.py         A 层：raw → _transcripts（openpyxl/docx/OCR）
│   ├── build_primary_2026.py  B 层：_transcripts → 2026-<区>.json（SchoolMatcher 匹配实体表）
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
parsed/2026-<区>.json   ← 消费产物
```

### A 层（转录）
每个 parse_*.py 从 `raw/` 原文件读取，输出 `parsed/_transcripts/<区>_2026.json`。扫描件（海珠 png、天河/黄埔 PDF）走 `scripts/ocr/vision_ocr.py`，产出后用 `audit_*.py` 与 WebFetch/pdftotext 等交叉比对。

### B 层（匹配）
`build_primary_2026.py` 以转录为源，逐个学校名调 `SchoolMatcher.resolve / resolve_all`：

- **带校区名**的记录 → `resolve` 单校区匹配；
- **无校区名的法人多校区**（官方未列校区）→ `resolve_all` 展开为全部校区记录；
- **不读任何手工锚点表**（`_anchors.json` 已废弃）。名字映射全部下沉到实体表别名层（`data/registry/entity/scripts/build_entities.py` 的 `OFFICIAL_PRIMARY_ALIAS` / `PRIMARY_CAMPUS_ALIAS`）。

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
| 海珠 | 78 | 92 | 2 |
| 天河 | 76 | 91 | 2 |
| 番禺 | 150 | 148 | 3 |
| 白云 | 138 | 151 | 10 |
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
