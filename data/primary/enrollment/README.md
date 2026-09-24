# 小学招生（enrollment）

2026 年广州市各区公办小学招生地段/计划的解析与匹配产物。与小升初/初中招生（`data/primary/transition/` + `data/middle/enrollment/`）**业务完全分离**：本目录只做小学招生。
**官方源文件统一共享 `data/enrollment/raw/`**（2026-09-23 迁出，小学/小升初/初中招生共用同一份政府原文，见下节「数据源」）。

## 目录结构

```
enrollment/
├── raw/        官方源文件已迁共享 `data/enrollment/raw/`（2026-09-23；本目录不再存 raw）
├── parsed/     解析层（可审计可重跑）
│   ├── _transcripts/   A 层：parse_*.py 从 raw 提取的结构化 JSON（含 OCR 缓存 ocr/）
│   └── dist/           B 层：build_primary_2026.py 输出 2026-<区>.json
│                      （匹配产物，保留 school/poi_name/lng/lat 等调试字段）
├── src/        手工源文件（业务确认口径）：leftover_notes.json 招生区域承接说明表、manual_patches.json B 层人工修复表
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
  │  B 层（build_primary_2026.py，SchoolMatcher 匹配 data/registry/entity
  │        + src/manual_patches.json 人工修复层，2026-09-23）
  ▼
parsed/dist/2026-<区>.json   ← B 层匹配产物（保留 school/poi_name/lng/lat 调试字段）
  │  C 层（build_enrollment_all.py 合并瘦身）
  ▼
dist/2026-all.json           ← 最终运行时产物（无 school 名，按 school_id 联查）
```

## 数据源（官方 2026-04-28 前后发布）

| 区 | raw 原文件（共享 `data/enrollment/raw/`） | 关键内容 | 解析脚本 |
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

每个 parse_*.py 从共享 `data/enrollment/raw/` 原文件读取，输出 `parsed/_transcripts/<区>_2026.json`。扫描件（海珠 png、天河/黄埔 PDF）走 `scripts/ocr/vision_ocr.py` 或 Read 直读。

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

## B 层人工修复表（src/manual_patches.json，2026-09-23）

承接 A 层脚本**无法复现**的人工转录修正，幂等补齐：转录已含修正 → 不动；转录被 A 层脚本重跑覆盖 → 由本表恢复。保证 B 层产物与快照基线一致，C 层零改动自动收益。当前 3 类：

| 区 | 类型 | 内容 | 触发条件 |
| --- | --- | --- | --- |
| 越秀 | 补录 2 校 | 红火炬小学（6 班）、水荫路小学（8 班） | 转录缺该记录时插入（锚点：永曜北/先烈中路前） |
| 越秀 | zone 裁污染后缀 | 东川路小学、育才学校 | 转录 zone 含下一校块头（脚本分块把红火炬/水荫路并进前一条尾部）时截断 |
| 荔湾 | zone 补前缀 | 真光中学附属培真小学 | 转录 zone 缺「石围塘街·岭南社区」行时补 |

> 重跑须知：荔湾 A 层必须两步（`parse_liwan_primary.py` + `fix_liwan_transcript.py`），本表只兜底 fix 复现不出的培真 1 处；单步初版格式（「街道·社区」拍平）不在兜底范围。越秀 A 层单步后 B 层即兜底 2 校 + 裁剪。

## 海珠班数挂载（公办计划表）

海珠地段表只有「学校/服务地段」两列（无班数），班数来自官方另发的《2026年海珠区公办小学招生计划表》
（共享 `data/enrollment/raw/haizhu_2026_gongban_plan.png`，学校+班数双列 80 条）。`parse_haizhu_plan.py` 转录到
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

### POI 未匹配处置经验（2026-09-22 起，逐区增量）

#### 荔湾 POI 未匹配处置经验（2026-09-22，后续各区按此执行）

背景：荔湾 2026 官方招生计划未单列的 POI 点位共 9 个，逐校联网核实后按以下分类处置，全部闭环（`poi_leftover` 清零）。后续各区（白云/越秀/海珠/天河/番禺/黄埔）的 `poi_leftover` 逐校核实沿用此流程。

**处置分类（用户定夺口径）：**

1. **废弃（学校彻底关闭，无在读学生）** → 从 `primary_poi.json` 清除点位。判定依据须为官方关闭证据（固定资产报废公示/撤销批复），且确认无在读与毕业出口。
2. **更名** → 实体表 `entities.json` 对新名字学校加旧名别名（`build_entities.py` 生产）；`leftover_notes.json` 可注明更名。例：芳村实验小学 → 芳村小学实验学校。
3. **不招一年级但学校仍在（多校区/停招，有在读或毕业出口）** → 点位保留，在 `data/primary/enrollment/src/leftover_notes.json` 按 school_id 加说明（详情页展示）；招生侧生成 zone=note 记录，原校保留遗留学生升学。例：乐贤坊荔枝湾、沙面本部/岭南/悦江、西关实验芳园、河沙。
4. **民办学校（无地段招生）** → 确认民办后补标 `nature=民办`（`data/registry/private/src/minban_*.md` 核实 → 权威表），自动不计入 `poi_leftover`。例：芳村新苗学校(广佛新城校区)。
5. **错误/噪音点位（非小学）** → 直接从小学 POI 池清除，初中/高中池不受影响。例：西关外国语学校(初中部)——小学招生已由泮溪校区点位覆盖。

**note 文案规范（详情页直接展示，面向家长）：** 只写「2026 年官方招生计划未单列」+「该片区由 XX 学校承接招生」（有官方依据才写承接校）；不写「学校仍在运营/场馆在册」等内部口径，不写「待后续核实」类内部待办；更名信息可保留（家长按旧名找得到新校）；新开办校区如实写「新开办 + 实际招生情况」。

**教训（河沙小学，2026-09-22）：** 河沙小学 2021 年起暂停招一年级，但 2026 年招生季仍有最后一届在读与小学毕业出口（2026-08 固定资产报废公示发生在毕业之后）。一度误判为"废弃"删除 POI，导致实体表联动删除、小升初记录 school_id 置空。**判定标准：停招（有在读/毕业出口）≠ 废弃（彻底关闭）**；只有官方明确关闭且无在读学生时才删除点位。删除 POI 前先全局检索该 school_id 在 transition/group 等表的引用。

**补充检查项（2026-09-23 复盘，四区处置后新增）：**

1. **删点/更名前先判定是否同一实体**：「并入/更名」的旧名必须用 `REMOVED_POI_ALIAS` 承继为新实体别名（用户按旧名反查仍可命中），例：低涌小学→海傍学校、石楼镇沙南小学→海鸥学校、茭塘小学→广东仲元中学莲花湾学校、番中附小→广东番禺中学附属学校、暨南大学附属小学→暨南大学附属实验学校、暨南大学华文学院-长征小学→广州市天河区长征小学、育华教育集团长虹学校→长虹小学。**「招生范围承接」≠「同一实体」**：胜洲村由石楼镇中心小学招生（区教育局人大答复）是地段归属而非并入，不加承继；废弃校（三善→红基学校承接）同样不加。
2. **官方地段 zone 明确列出校区招生范围的，优先 matched 而非 note**：石碁中心小学大龙校区官方 zone 原文含「大龙校区：大龙村户籍…金龙居委…」，用 `POI_NAME_FIX` 把后缀式校区名规范为括号式（石碁中心小学大龙校区 → 石碁镇中心小学(大龙校区)），`resolve_all` 自动吸附展开为多行完整地段记录，不写 note；note 只留给官方确实未单列的情形（同福西路/新民六街/滨江西一等集团成员校）。

#### 白云 POI 未匹配处置经验（2026-09-22，增量）

背景：白云 2026 官方招生计划未单列的 POI 点位共 16 个，逐校联网核实后全部闭环（`poi_leftover` 清零），处置分布：删除 10 / note 覆盖保留 5 / 民办补标 1。

**处置明细（school_id → 分类）：**

| 点位 | 分类 | 依据与去向 |
|---|---|---|
| 中八小学 | 删（并入他校） | 2002 年并入神山第二小学，神山二小 2026 地段含中八村；别名承继到神山二小 |
| 人和第六小学 | 删（高德变体） | 官方名"人和镇第六小学"（鹤亭村）已匹配，高德无"镇"变体删点，别名承继 |
| 南方中英文小学 | 删（废弃） | 企查查 2019-06-17 注销，高德标"暂停营业" |
| 南村学校 | 删（误名） | 官方对口表为"南村小学"，POI"南村学校"为地名误名；别名承继到南村小学 |
| 大沥小学西 | 删（重复点位） | 官方仅"大沥小学"，高德方位后缀同址重复；别名承继到 9588f926 |
| 广东外语外贸大学实验中学 | 删（初中点位混入） | middle_poi 仍有该 id，小学池清洗（同荔湾西关外校先例） |
| 张村中心小学教育联盟红星小学 | 删（机构噪音） | 实为石潭西路品致创意园集团办公机构；红星小学本体已匹配 abb00177 |
| 积德花园小学 | 删（民办废弃） | 民办，官方 2019-11-19 注销 |
| 金广实验小学 | 删（筹备名→正式名） | 钟落潭星汇城配建筹备名 = 星悦实验学校（2025-09 首开），别名承继到 88372834 |
| 陈田小学 | 删（更名并入） | 2026 正式挂牌"广外实验中学陈田西校区"小学部；别名承继到 c553e806，景泰教育集团移除、广外实验集团纳入 |
| 草庄小学 | note 保留 | 已注销，大沥小学 2026 地段含草庄村承接招生 |
| 马洞小学 | note 保留 | 已注销，马洞村地段 2022 年起由蟠龙小学承接 |
| 人和镇第四小学 | note 保留 | 人和村片区由七十三中小学部、高增村由六中实验小学（南校区）承接 |
| 太和镇第二小学(和龙校区) | note 保留 | 米龙校区 2026 地段含和龙村、白山村 |
| 白山小学 | note 保留 | 已并入太和第二小学（白山校区） |
| 颐和实验小学 | 民办补标 | 民办非企业单位（2007 成立），minban_schools.json 227 所 |

**本次新增教训：**

1. **同名异校必须按地理位置先核实再建映射。** 官方小升初表里的"金广实验学校"是金沙洲广附系（金域蓝湾/御金沙两校区，POI 一直存在），而钟落潭"金广实验小学"是星汇城配建筹备名（=星悦实验学校）。历史 BW_MAP 把官方"金广实验学校"错挂到钟落潭筹备点；删筹备点后修正为金沙洲两校区，金沙洲毕业生对口"广大附中实验中学"记录恢复。教训：同名不同地，删点/改映射前先确认官方名对应的实际位置。
2. **删 POI 后必须同步清理下游映射**：`build_xiaoshengchu_all.py` 的 BW_MAP（映射目标指向已删点位 → 校验报"映射目标不存在"）、BW_NO_FEED（残留已删行）；`test_match_poi.py` 期望（本次"金广实验学校→f501b6b5"回归失败即此）；`packages/shared/tests/snapshots/group_roster.json`（集团名单快照感知组内成员移除，如白云广附组移除金广实验小学、景泰组移除陈田小学）。
3. **更名承继用 REMOVED_POI_ALIAS（build_entities.py）**：删点一次重跑即同步删实体，旧名自动承继到新实体（7 组：中八→神山二小、南村学校→南村小学、大沥小学西→大沥小学、人和第六小学→人和镇第六小学、联盟红星→红星小学、陈田小学→陈田西小学部、金广实验小学→星悦实验学校）；裸名/俗称桥接走 POI_NAME_FIX（金广实验学校 → 金域蓝湾校区）。
4. **小升初构建链顺序**：`build_xiaoshengchu_all.py <区>` 生成区分文件 → 再 `all_done`（只 merge_all 分文件 + resolve_records）→ `upgrade_xiaoshengchu.mjs`。直接 all_done 不更新产物（本次踩：跳区直接 all_done，金域蓝湾/陈田西记录丢失）。
5. **集团成员"陈田西校区"不在 members 而在 core_poi 是设计行为**：merge_groups 核心校成员去重把 core 法人的校区成员行并入 core_poi（展示层不重复），任一校区仍经 school_id 外键命中集团。改 partial 后核对 education_groups 时看 core_poi 而非只看 members。
6. **快照联动清单**（数据变更后逐一更新）：enrollment（`--update-snapshot`）、entities/orphans/co_located/minban（`UPDATE_SNAPSHOT=1 data_quality_test`）、middle_feed（`build_middle_feed_snapshot.py`）、group_roster（node 重算 collectEdu/collectBrand）、brand_card（`UPDATE_SNAPSHOT=1 npm test`）；`npm run check` 的 check_groups_drift 做"产物重跑=HEAD"比对，**必须先 commit 再 check**。

#### 越秀 POI 未匹配处置经验（2026-09-22，增量）

背景：越秀 2026 官方招生计划未单列的 POI 点位共 11 个，逐校联网核实后全部闭环（`poi_leftover` 清零），处置分布：删除 4 / note 覆盖保留 6 / 民办补标 1。

**处置明细（school_id → 分类）：**

| 点位 | 分类 | 依据与去向 |
|---|---|---|
| 广州海印实验学校 | 删（初中点位混入小学池） | 官方 2026 招生计划表为"民办初中"，middle_poi 保留同 id；pending_items 早标注"primary 阶段实体疑似历史误植"（同白云广外实验先例） |
| 惠福西路小学(惠福校区) | 删（并入他校） | 2021-04 越秀布局调整与旧部前小学合并为新旧部前小学；别名承继到旧部前小学 |
| 泰康路小学 | 删（撤并） | 2010 年撤并，原泰康校区用地划拨第十中学 |
| 越秀区培智学校 | 删（并入他校） | 2020-07 整体并入启智学校，一校三区（白云路/大德路/五常里）；别名承继到越秀区启智学校(白云路校区) |
| 东风东路小学天伦校区 | note 保留 | 东风东按年级分校区：锦城 1-3/本部 4-6、东风广场 1-3/天伦 4-6，一年级按锦城/东风广场登记招生 |
| 东风东路小学(本部校区) | note 保留 | 同上，一年级按锦城/东风广场登记招生 |
| 东山培正小学海印苑校区 | note 保留 | 海印苑校区教学楼扩建公示在建，一年级按整体招生登记 |
| 小北路小学天香街校区 | note 保留 | 小北路按年级分校区，一年级按小北/天秀校区登记招生 |
| 小北路小学应元校区 | note 保留 | 同上（26 学年应元校区装修中） |
| 越秀区启智学校(白云路校区) | note 保留 | 区属特殊教育学校，官方计划单列"特殊学校小学部"，不参与普通小学地段招生 |
| 广州至灵学校 | 民办补标 | 民办非营利特教康复机构（1985 创办，小学部/初中部/职高班），面向 6-18 岁智障/孤独症儿童，特教渠道报名；minban_schools.json 228 所 |

**本次新增教训：**

1. **民办/特殊教育在运营学校一律不删点，走民办补标。** 至灵学校仍在运营（有在读/毕业出口），此前残留半成品误当作废弃删除，与用户口径"停招≠废弃"冲突——本次恢复 POI 并民办补标。判删点必须同时满足：官方计划无此校 + 无在读毕业生出口（小升初记录为"民办/特殊教育/官方未单列"）+ 权威撤并/注销依据。
2. **小升初三件套必须同一时刻产物。** `build_xiaoshengchu_all.py <区>`（区分文件）→ `all_done` → `upgrade` 三步连续执行，否则区分文件与 all/2026 记录不一致（本次 HEAD 曾出现：区分文件 77 条不含至灵 vs all/2026 含至灵 931 条 → check 报 xiaoshengchu 漂移）。
3. **提交自洽性：同一 commit 内 primary_poi / 区分文件 / 快照必须互相一致。** 曾出现 POI 已删但实体/快照仍含该校（或反之）的提交，check 全绿校验逐项暴露。删点后按快照联动清单全量重跑再提交。
4. **实体重建会改变 entities 顺序 → merge_groups / school_groups 产物需重跑提交**（campuses/school_id 键顺序随实体顺序变化，check_groups_drift 会报"产物漂移"），group_roster 测试快照同理。
5. **note 文案面向详情页用户**：只写"2026 年官方招生计划未单列该校区 + 实际承接招生校区/学校"，不写内部口径（"待确认""点位未核"等内部词一律不出现）。

#### 天河 POI 未匹配处置经验（2026-09-22，增量）

背景：天河 2026 官方招生计划未单列的 POI 点位共 10 个，逐校联网核实后全部闭环（`poi_leftover` 清零），处置分布：转录补录企事业办小学（华工附小/暨大附小等归位 matched）/ 更名归一 3 处 / 民办补标 1 / note 覆盖 3 条 / 停办结论修订 1。

**处置明细：**

| 点位 | 分类 | 依据与去向 |
|---|---|---|
| 华南理工大学附属实验学校 | 转录补录 | 2026 天河细则附件 7「企事业办小学」在案（5 班）；官方名「华南理工大学附属实验学校」，转录补录后归位 matched |
| 暨南大学附属实验学校 | 转录补录 | 附件 7 在案；官方名「暨南大学附属实验学校」，转录补录归位 matched |
| 暨南大学华文学院-长征小学 | 更名归一 | POI_NAME_FIX → 广州市天河区长征小学（2026 细则附件 7 在案） |
| 暨南大学附属小学 | 更名归一 | POI_NAME_FIX → 暨南大学附属实验学校 |
| 广州市育华教育集团长虹学校 | 民办补标 | 附件 8 #28「长虹小学」3 班 128 人民办；育华学校 2025 停办不并入；minban_snapshot 229 所 |
| 华阳小学(林和东校区) | note 保留 | 2026 官方计划未单列该校区，按天河东校区（华成）登记招生 |
| 华阳小学(天润校区) | note 保留 | 同上，按天河东校区（华成）登记招生 |
| 天府路小学(翠湖校区) | note 保留 | 2026 官方计划未单列该校区，按东方校区（翠湖建业）登记招生 |
| 志才小学 | 停办结论修订 | 2024 年检不合格，2025 年度已停办，「待核」文案修订为停办结论 |

**本次新增教训：**

1. **企事业办/高校附属小学从官方细则附件转录补录，而不是 note 覆盖。** 天河 2026 细则附件 7「企事业办小学招生计划」单独列出华工附小/暨大附小等，属官方在案招生校，应转录为 matched（同海珠中大附小情形需逐区看官方是否单列，单列则转录、不单列则 note 覆盖）。
2. **POI_NAME_FIX 负责裸名/旧名/集团名桥接到官方名**，配合转录补录一次性让多个 POI 归位同一官方记录，比逐点 note 覆盖更干净。
3. **民办确认优先于 note**：长虹小学在官方民办招生计划（附件 8）在案 → 民办补标自动排除，不占 note 名额；「育华教育集团」只是办学集团名，不改变长虹小学为民办实体的结论。
4. **「待核」类文案一旦有官方年度结论（年检结果/停办公告）立即修订为结论**，不留给详情页任何待办口吻。

#### 番禺 POI 未匹配处置经验（2026-09-22，增量）

背景：番禺 2026 官方招生计划未单列的 POI 点位共 9 个，逐校联网核实后全部闭环（`poi_leftover` 清零），处置分布：删除 8（均有官方撤并/并入/更名证据）/ note 覆盖保留 1 / NO_FEED 补民办 1、清理历史残留 2。

**处置明细：**

| 点位 | 分类 | 依据与去向 |
|---|---|---|
| 三善小学 | 删（废弃） | 校址已改造为「匠源坊」文创园；2025 起三善村由红基学校承接招生（区教育局） |
| 低涌小学 | 删（并入） | 官方预算公开信息并入海傍小学；2026 海傍小学在案 |
| 赤山东小学 | 删（改办） | 校址改办集体幼儿园，小学段不再办学 |
| 沙南小学 | 删（并入） | 2010 年并入海鸥学校，现为海鸥学校沙南校区 |
| 胜洲小学 | 删（并入） | 区教育局人大答复：属石楼镇中心小学招生范围 |
| 茭塘小学 | 删（并入） | 2020 年并入山海连城学校（现莲花湾学校） |
| 明德实验小学 | 删（同址重复） | 与明德广地实验学校同址，民办名单已在册（7997c707），重复点位 |
| 番禺中学附属小学 | 删（同址重复） | 与番禺中学附属学校同址，重复点位 |
| 石碁中心小学(大龙校区) | note 保留 | 官方 139 行在案，按本部+大龙校区整体登记招生 |

**本次新增教训：**

1. **删点必须有官方撤并/并入/承接招生证据**：番禺 8 个删点全部有官方来源（人大答复、预算公开、招生工作意见、旧址改造报道），无证据不删。
2. **NO_FEED/MAP 残留与删点联动清理**：PY_MAP 中番中附小/傍东小学(后门)指向已删点位 → 同步移除；三善小学「待核」文案随删点删除；加拿达外国语(剑桥郡校区)补民办 NO_FEED。
3. **重复点位的处置是删（POI 池去重）而非更名**：同址重复（明德实验/番中附小）与真更名（改名换址）不同，删点后无需 REMOVED_POI_ALIAS，实体表保留在册实体。

#### 海珠 POI 未匹配处置经验（2026-09-22，增量）

背景：海珠 2026 官方招生计划未单列的 POI 点位共 7 个，逐校联网核实后全部闭环（`poi_leftover` 清零），处置分布：删除 2 噪音 / note 覆盖保留 5（含高校附属 1、集团成员校 4）。

**处置明细：**

| 点位 | 分类 | 依据与去向 |
|---|---|---|
| 丝雨街小学 | 删（POI 噪音） | 无该校任何办学记录，「丝雨街」为街道名误作校名 |
| 中小学全科教育 | 删（机构噪音） | 培训机构非学校实体 |
| 中山大学附属小学 | note 保留 | 高校附属小学（企事业单位办，非民办），2026 官方计划未单列，面向中山大学教职工子女招生 |
| 同福西路小学(龙庆校区) | note 保留 | 同福中路第一小学教育集团成员校，2026 官方计划未单列 |
| 滨江西路第一小学 | note 保留 | 同福中路第一小学教育集团成员校，2026 官方计划未单列 |
| 新民六街小学(北校区) | note 保留 | 宝玉直实验小学教育集团成员校，2026 官方计划未单列 |
| 新民六街小学(南校区) | note 保留 | 同上 |

**本次新增教训：**

1. **高校附属小学按官方是否单列分流**：天河细则附件 7 单列企事业办小学 → 转录 matched；海珠官方计划未单列中大附小 → note 覆盖保留。先查官方，不预设结论；民办源文件（minban_haizhu.md）已把中大附小列入「已排除（企事业单位办，非民办）」，故不走民办补标。
2. **集团成员校 2026 未单列 ≠ 停办**：同福西路/新民六/滨江西一为集团成员校（2024 区教育局集团通知确认），2026 公办计划未单列但学校在册（有在读/毕业出口），note 只写「官方计划未单列 + 集团成员身份」，不编造承接校（官方无「由 XX 承接」声明时不写）。
3. **小升初链与招生处置联动**：note 保留的点位必须在 `build_xiaoshengchu_all.py` 有出口——公办成员校补 HZ_MAP/HZ_DIRECT（滨江西一参加海珠电脑派位、南武中学附属学校直升本校初中），民办补 HZ_NO_FEED（华海双语/为明光大/育华/华洲实验/贝赛思/春晖共 6 所）；北山小学历史空映射（「待核」注释）补实映射。缺口=0 才算闭环。
4. **待核文案清理**：海珠 HZ_NO_FEED 遗留「东风第二小学」「宝玉直实验第二小学」等「待核」行，本轮把丝雨街改噪音结论、民办改派位说明，逐条清掉内部待办口径。

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
