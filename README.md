# 广州学校升学路线调研

为孩子寻找合适升学路线的调研项目。系统性调研广州地区的学校与升学路径，综合考虑学校实力、入学方式、孩子特点与家庭条件，形成可执行的升学决策建议。

## 目录结构

```
.
├── apps/                    # 各端应用
│   ├── web/                 # Web 应用（Vue3 + Vite，npm run dev/build）
│   │   ├── index.html       # 应用入口
│   │   ├── src/             # Vue3 工程：pages（入口/地图/详情/明细）、data 加载层
│   │   └── package.json     # @gz/web
│   ├── miniprogram/         # 微信小程序（原生，根目录 = apps/miniprogram）
│   │   ├── app.json / app.js / app.wxss
│   │   ├── pages/           # index（入口）/ map（内置 <map>）
│   │   ├── utils/data.js    # 数据加载（shared + data 构建产物）
│   │   ├── shared/          # 构建产物：@gz/shared cjs（git 忽略，npm run build:mp 生成）
│   │   └── data/            # 构建产物：data/*.json → CommonJS 模块（git 忽略）
│   └── README.md
├── packages/
│   └── shared/              # @gz/shared 双端共享核心包（TS：类型 + 纯逻辑，零平台依赖）
│       └── src/             # types / const / geo / stats / support
├── data/                    # 共享数据层（JSON 唯一真源，多端共用）
│   ├── primary/             # 小学阶段数据（tier1_schools_all.json / enrollments/；点位见 poi/）
│   ├── middle/              # 初中阶段数据（tier1_schools_all.json；点位见 poi/）
│   ├── high/                # 高中阶段数据（level/src/levels.json / 剔除留痕；录取分见 cutoff_score/；点位见 poi/）
│   │   ├── cutoff_score/    # 高中录取分（dist/ 历年产物 · raw/ 官方源页面 · src/ 手工源 · scripts/ 解析脚本）
│   │   └── level/src/       # 学校清单/分类/指标（levels.json 人工调研源，前端直接消费）
│   ├── poi/                  # POI 点位（dist/*_poi.json 真源，采集/清洗脚本在同目录 scripts/）
│   └── README.md            # 数据治理约定与更新方式
├── scripts/                 # 共享脚本（数据采集/构建 + 小程序构建）
│   ├── entity/scripts/build_entities.py  # 实体注册表（school_id 主键 + 官方名/别名桥接）
│   ├── build_district_enrollment.py  # 五区小学招生数据
│   └── miniprogram/build.mjs  # 小程序构建（shared cjs + data json → 小程序包）
├── docs/                    # 调研报告、分析文档
├── .env                     # 本地密钥（git 忽略，不入库）
└── README.md
```

## 开发命令

```bash
npm install                    # 安装 workspace 依赖（npm workspaces）
npm run build:shared          # 构建 @gz/shared（dist/esm + dist/cjs）
npm run dev:web               # 启动 Vue3 Web 开发服务器（Vite）
npm run build:web             # 构建 Vue3 Web 产物（apps/web/dist）
npm run build:mp              # 生成小程序 shared/data 构建产物
npm run check                 # 全部 workspace 类型检查
```

当前代码分层、数据流与构建边界见 [docs/architecture.md](docs/architecture.md)。历史改造方案仅作迁移留档，不应作为当前实现依据。

数据真源约定：`data/` 下 JSON 为唯一数据真源，Web 与小程序均从该层构建加载，勿手改产物；
小程序包内 `shared/`、`data/` 为构建产物（git 忽略，由 `npm run build:mp` 生成）。

## 教育集团数据流与产物纪律（2026-09 品牌关联修复后强制）

数据流（禁止绕过）：

```
data/registry/group/parsed/_partial_{区}_groups.json   ← 7 区采集底稿（纯源，人工维护，含 school_id 锚点）
data/registry/group/parsed/education_groups_2026.json ← 招考办名额分配表（纯源）
data/registry/group/src/brand_groups.json          ← 8 重点品牌（纯源，unit.school_ids 外键锚点）
        │
        ▼  python3 scripts/merge_groups.py   （本地脚本，无联网）
data/registry/group/dist/education_groups.json      ← ★ 唯一生成产物，禁止手改 ★
        │
        ▼  node scripts/data/compact.mjs  +  npm run build:shared
apps/web/src/data/compact/**  与  @gz/shared 构建产物（Web/小程序实际消费）
```

纪律：

1. **产物禁止手改**：`education_groups.json` 只能由 `merge_groups.py` 生成。需要调整归属时改三处源
   （partial / brand_groups / entities），然后重跑生产脚本。历史 94 处漂移即因 9 次提交直接手改产物造成。
2. **先跑生产脚本**：`npm run check` 已内置 `check_groups_drift.py`——重跑 `merge_groups.py` 到临时文件
   并与入库产物对比，不一致即失败（丢失/错配/新增逐条列出）。改源后必须重跑
   `python3 scripts/merge_groups.py` 使产物同步，否则 check 红。
3. **匹配器**：`scripts/match_poi.py` 的改动由 `scripts/test_match_poi.py`（14 回归用例）与
   `data_quality_test.py`（3307 项含全量 POI 自我匹配）守护；改匹配器必须全量重跑 `npm run check`。
4. **宁可缺失、不跨区错配**：匹配器对无法收敛到唯一同区候选的成员返回缺失，由调用方以显式
   school_id 锚点（partial/brand_groups 的 school_ids 字段）补救，不允许跨区吸附。
5. **新增/调整学校归属标准流程**：改源 → 重跑 `python3 scripts/merge_groups.py` → `npm run check`
   （含产物一致性）→ 确认缺失清单（若为真实缺失，在 partial 标记 `7区内真实缺失` 并同步产物）→ 提交源+产物。


## Web 应用（apps/web）

新版（Vue3 + Vite）：`npm run dev:web` 开发，`npm run build:web` 构建；入口 `apps/web/index.html`，
路由 `#/`（入口）/ `#/map`（地图）/ `#/middle`（初中明细），数据经 `src/data/` 从 `data/*.json`（真源）加载，
逻辑复用 `@gz/shared`。构建产物 `apps/web/dist` 可由静态服务器 / GitHub Pages 直接部署（hash 路由，file:// 亦可打开）。

### 中小学·高中合并地图（apps/web#/map）
- 同时展示广州 7 区（荔湾 / 越秀 / 海珠 / 天河 / 白云 / 黄埔 / 番禺）三学段点位：915 小学 + 3 补点、296 初中 + 14 补点（1 所与 POI 重合去重）、126 高中点位（90 所学校，含多校区）
- 七类配色：小学·普通（浅灰蓝）/ 小学·口碑（蓝）/ 初中·普通（暖浅灰）/ 初中·口碑（红）/ 高中普通（灰蓝）/ 高中区属示范（绿）/ 高中省市属示范（琥珀）
- 左侧筛选区：7 个 checkbox + 全选 / 全不选，实时控制点位显示并同步图例统计
- 点击点位展示信息卡：小学（招生数据 + 升学路线）、初中（生源小学 + 升学通道）；高中（分类徽标 + 示范性等级·隶属 + 特控线上线率 / 高分段 / 本科率 + 2025 中考录取线 + 口径说明）
- 区边界色块 + 各区数量图例统计（小学 / 初中 / 高中三栏）；视野锁定七区范围
- 纯本地数据渲染，不做实时请求

地图是 web 应用当前首个功能，后续按子功能目录扩展学校详情、对比、路线规划等。

### 广州七区初中明细（apps/web#/middle）
- 7 区全量初中（334 所，荔湾 33 / 越秀 31 / 海珠 34 / 天河 47 / 白云 71 / 黄埔 41 / 番禺 77，以名额分配 quota_matrix 为候选底）升学信号排行：按区 / 按教育集团（brand 优先 + 85 集团名录 loose 匹配，脚本预计算）分组；口碑列已随口碑业务移除
- 6 项指标可选：自招人数（绝对值）/ 自招比例（÷名额分配符合资格考生数）/ 区属指标数 / 区属指标比例 / 省市属指标比例 / 指标×特控率（Σ(区属高中给该校指标名额×该高中特控率)÷该校考生数，即该校考生经区属指标到校预计上特控线的比例）
- 比例口径一律除以考生数，消除学校规模差异；真源 `data/linkage/ranking_middle.json`（`scripts/linkage/build_ranking_middle.py` 三源聚合：quota_matrix 指标到校（7 区全量为底）+ autonomy 自招名单 + levels 特控率，只读不改源文件）
- 首页 features 与全局导航均可进入

#### 名额分配矩阵 OCR 方案记录（2026-09-15 重建）
真源 `data/linkage/raw/quota_detail.pdf`（官方 31 页，无文本层，带灰色水印）。以下为踩坑与最终方案记录，避免重蹈覆辙。

**最终采用（成功）方案**：整页 200 dpi 渲染（`/tmp/qpage/p*.png`）+ 视觉识读（Read 整页图），逐格/逐列裁剪复核疑点（600–900 dpi）。权威三列值落盘为 `scripts/linkage/quota_vision_values.py`（P[页码][行]=[考生,省市,区属]，含番禺两条缺行），由 `scripts/linkage/rebuild_quota_matrix.py` 重建 `data/linkage/quota_matrix.json`（503 校，11 区）。已校验：10/11 区级合计与官方区头精确一致；天河省市行和 554 vs 区头 555 差 1，四路独立复核一致，判定为官方原表口径差。

**已弃用（失败）方案与原因**（脚本已删除，仅留此记录）：
1. tesseract 5.5.3（白名单数字 + psm 6/7/8 × 阈值 × 放大）——裁剪小图全部空读；
2. Swift Vision 整行 600 dpi——相邻格数字被合并成单个文本块，列归属失败；
3. Swift Vision 逐格裁剪（v6/v6fix）——部分页 grid 列坐标偏移致逐格错位（荔广省市"8"空读、番中实验"27"读成"391"），多数省市窄格空读；6↔9 混淆在区级合计中互相抵消，"区级对齐即定稿"的裁决贪心不可靠（adjudicate_quota.py 已否决）；
4. 阈值二值化去水印——打丢淡色数字（真光区属 335）；
5. 整行 OCR 对区属列系统性 6↔9 误读（荔广 249、培正矿泉 128 根因）。

**保留/删除说明**：`data/linkage/raw/quota_grid_final.json`（整行 OCR 网格）仅保留其 sz 高中分额列供补行使用，三列（考生/省市/区属）作废；`schoolnames.json` 为校名源保留；其余 OCR 中间产物（v6/v6fix/adjudicated/_ocr/headers）与失败脚本已删除。

**已知残差**：番禺补行"广东第二师范学院广州南站附属学校 / 番禺附属初级中学"的 sz 高中分额明细暂缺（sz_sum=0，见 quota_matrix.json note）。

**2026-09-15 复核修复**：
1. **番禺铁一校名错位**：官方 p18 序号 49「广州铁一中学（番禺校区）」(266/14/73) 曾被 schoolnames 读残缺为"广州市铁"（榜单显示"铁"）；序号 50「广州大学附属中学（番禺校区）」(557/29/154) 被 NAME_FIX 误改名为"广州市铁一中学（番禺校区）"，造成铁一/铁英"重复"假象。已修正 NAME_FIX：`(18,9)='广州铁一中学（番禺校区）'`、移除 `(18,10)` 误改；school_id 对应 entities 番禺铁一(97e0acaa) 与广大附中大学城(8f5e4721)。
2. **school_id 修正（SID_FIX）**：7 所 quota 行此前为 md5 生成/误配的假 id，导致民办 Badge 漏标（华立/海龙博雅/爱莎文华/同仁实验/东风）与详情页 stage 错乱。已按 entities 名/别名核对修正：华立→gz-440105-8371ce9c、海龙博雅→gz-440103-957da59e、爱莎文华→gz-440103-5143f5a1、同仁实验→gz-440106-77787b4a、东风→gz-440106-24ff78f9、黄埔铁英→gz-440112-c80ac6ac、番禺丽江→gz-440113-2264148c。民办 Badge 99→104。
3. **详情页学部覆盖核查（334 校模拟 buildDetailModel）**：含初中部（middle）315 所；仅小学部 8 所（海龙博雅/知用/天河华实/培智/东风/省教院黄埔实验/祈福新邨/番禺金华）；仅高中部 6 所（爱莎文华/为明/奥林匹克/华美/开元/苏元）；无任何点位 5 所（华立/江高二中/三元里/南悦/二师南站附属）——后两类属 POI/实体数据缺口，未修。
4. **详情页跳转/自招数据修复（2026-09-15 第二轮）**：
   - 榜单链接统一加 `stage=middle`：从初中明细跳详情页默认打开初中部（修复祈福新邨/新英豪等 93 所九年制学校默认落小学部）。
   - 祈福新邨 school_id 修正：`1963cc5e`（小学实体）→ `8ef59a4c`（初中实体/初中 POI），详情页从"祈福新村小学"改为初中部（自招 185 人正常显示）。
   - 详情页自招补充：tier1（口碑校 54 所）未覆盖的初中，从 `rankingMiddle`（2026 官方自招资格名单）补充"自主招生"行（`官方资格名单`标注）。共修复 180 所（清单 `outputs/detail_autonomy_gap_20260915.csv`）；另有 10 所 aut>0 但详情页无初中 tab（POI 点位缺口，未修复）。
5. **数据治理（2026-09-15 第三轮，按用户 5 条批评重构）**：
   - **school_id 解析重构（废除 SID_FIX）**：`rebuild_quota_matrix.py` 内置通用匹配器 `SidResolver`（区 + 名字/别名，norm 全等 3 → pynorm 2 → core 1 → 前缀 0.5，学部分层 middle→primary→high，歧义同区消歧，有效旧 id 沿用保护），实体表变更后重跑脚本自动联动，不再点对点打补丁。
   - **实体表治理（数据源修复，联动生效）**：删海珠知用 `934833e1`、越秀协和 `1b1d2659` 两条错区重复记录；补录三元里中学（在办未收录 → `gz-440111-a20eb9b6`，旧 md5 占位自动升级为实体）、协和 middle、海龙博雅/爱莎文华/知用 middle 学部记录；奥中本部初中实体（黄村西路校区）补别名；祈福实体/POI 名"祈福新邨"→"祈福新邨学校"。由此自动修复：西关培英（原误挂四中丰宁 `3b870a8e`→`d78c848a`）、协和（→`e281e7d0`）、奥中（→`d40d0dbe`）、三元里（→`a20eb9b6`）、天健/开元/省教院黄埔实验/金华等错区或错学部 id。匹配器另加"中学↔小学 core 交叉防护"与"九年一贯"学段。复核：7 区 334 所 quota 校 school_id 全部命中实体且含初中 stage（仅二师南站附属保持 md5 占位，POI 缺口）。
   - **祈福地图点位修正（问题 2）**：middle POI `8ef59a4c` 原为住宅片区名"祈福新邨"、坐标 (113.329043, 22.961537)，改为"祈福新邨学校"、坐标 (113.322074, 22.962704)（与小学 POI 同址，学校建筑真实位置）。
   - **升学信号源纠正（问题 3）**：tier1 只做学校信号（`formatMiddleSignals` 移除"自主招生"行）；详情页"自主招生"行一律取 `linkage/ranking_middle.json`（官方自招资格名单），标注"官方资格名单"。
   - **铁一番禺自招=0（问题 4）**：quota 名"广州铁一中学（番禺校区）"与官方名单"广州市铁一中学（番禺校区）"差"市"字，norm 去括号撞多校区返回 0；`AUT_ALIAS` 归一 → 109。
   - **广大附两校区"65"（问题 5，数据澄清）**：初中自招按校区正确（番禺 131 / 越秀 80，官方资格名单）；"65"为大学城初中"中考-第一批"升入广大附高中自招资格 65 人 + 广大附高中部 2026 自招计划 65 人（官方法人统一计划，两校区高中页面共用同一份第一批/第二批招生表），已在该表头加注"高中部招生计划按法人单位统一公布，多校区共用同一计划"消除误导。
   - **广大附"65"复核修正（2026-09-15 第四轮，按用户查证）**：上轮"高中自招计划 65"表述有误，更正如下——
     1. **官方招生单位不分校区，但办学地点在大学城**：官方 2026 高中招生（招生总计划 812、自招计划 **102**、名额分配 406、第三批录取线 732/738、自招资格名单 461 人）全部以法人"广州大学附属中学"一个单位发布（gzzk 官方汇总表/录取表原文）。黄华路校区自 2017 年起为**纯初中部**（高中部全在大学城校区，官方多来源佐证），故"65"与高中招生无关。
     2. **65 的真实口径**：番禺校区（大学城）初中升入广大附中高中的**自招资格人数**（官方资格名单：番禺 65 / 越秀 24），是"中考-第一批"表的数据，不是高中招生计划。
     3. **数据根修正（非点对点）**：黄华路高中 POI（data/poi/dist/high_poi.json）删除；实体 b22c4eca 撤销 high 学部、移除法人名别名（法人名"广州大学附属中学"改挂大学城实体 8f5e4721，官方分数 scores 2025/2026 改挂 8f5e4721）；levels 广大附中 district 越秀→番禺。由此高中明细只剩"广州大学附属中学(大学城校区)"一行（番禺区），黄华路详情页只剩初中 tab，任何官方名单名跳转均落大学城高中。上轮临时加的 findExactLoose / resolvePoiName 多校区规则 / 高中行归并三处复杂逻辑已全部回退，保持代码简单。

## 数据

### 小学点位数据（data/poi/dist/primary_poi.json）

- 来源：高德地图 Web 服务 API，2026-09-08 快照（GCJ-02 坐标系）
- 共 915 所：荔湾 75 / 越秀 78 / 海珠 120 / 天河 115 / 白云 227 / 黄埔 101 / 番禺 199
- 已合并同校重复 POI；番禺含 backfill 补充点
- 通过翻页采集突破单区 100 条上限
- 更新：`python3 data/poi/scripts/fetch_schools.py`（需 `.env` 中的 `AMAP_WEB_KEY`）

### 初中点位数据（data/poi/dist/middle_poi.json）

- 来源：高德地图 Web 服务 API，2026-09-09 快照（GCJ-02 坐标系）
- 范围：7 区（荔湾 / 越秀 / 海珠 / 天河 / 白云 / 黄埔 / 番禺），排除远郊南沙 / 花都 / 从化 / 增城
- 采集：types=141201（初中分类）+ types=141200（中学分类）+ 关键词「初中」三路翻页合并，保留初中与完全中学
- 更新：`python3 data/poi/scripts/fetch_middle_schools.py`

### 高中点位与分类指标（data/poi/dist/high_poi.json + data/high/level/src/levels.json）

- 点位来源：高德地图 Web 服务 API，2026-09-09 快照（GCJ-02 坐标系）；types=141202（高中）+ 关键词「高中」+ types=141200（中学）三路翻页合并，剔除培训机构 / 复读 / 托管 / 职业类等，再按 90 所学校清单精确清洗（清洗版点位即 `high_poi.json`，由 data/poi/scripts/build_high_levels_js.py 写回）
- 范围：7 区（荔湾 / 越秀 / 海珠 / 天河 / 白云 / 黄埔 / 番禺），排除远郊南沙 / 花都 / 从化 / 增城
- 分类口径（替换民间"市重点 / 区重点"的官方称谓）：
  - **省市属示范**（11 所）= 省属或市属示范性高中（国家级示范 / 市示范 / 市属优质，含市属名额分配新增校），对应民间"市重点"
  - **区属示范**（43 所）= 区属国家级 / 市级示范性高中，对应民间"区重点"
  - **普通高中**（36 所）= 其余公办（省一级等）+ 民办
- 分类依据（广州市招考办官方文件）：2026 名额分配招生学校名单、2025 第三批录取表、2025 第四批录取表
- 客观指标（data/high/level/src/levels.json，逐校）：特控线上线率 2026 / 2025（含网传口径）、600 分以上高分段占比、本科率、隶属与示范性等级、nature（公办/民办，取官方录取表"学校性质"列）；无公开数据的学校如实标注"高考出口数据未公开"
  - 特控率来源：2026 高考喜报（广州日报报道）+ 2025 年 51 校成绩汇总，均为喜报 / 网传口径，非官方统一发布（页面卡片已注明）
  - **中考录取分已迁出 levels**：2025/2026 两年官方分数见 `data/high/cutoff_score/dist/scores_2025.json` / `scores_2026.json`（由 `data/high/cutoff_score/scripts/build_scores.py` 从招考办官网录取表抓取，按 school_id 引用实体表），levels 不再存任何分数
- 点位统计：126 个（含 15 个高德补点），荔湾 17 / 越秀 18 / 海珠 14 / 天河 19 / 白云 25 / 黄埔 14 / 番禺 19
- 更新：`python3 data/poi/scripts/fetch_high_schools.py`（原始 POI）→ `python3 data/poi/scripts/build_high_levels_js.py`（按 levels.json 清洗点位并写回 data/poi/dist/high_poi.json）；录取分链路见「高中录取分数（data/high/cutoff_score/dist/scores_{year}.json）」一节

### 高中录取分数（data/high/cutoff_score/dist/scores_{year}.json）

- 真源：广州市招考办官网（gzzk.gz.gov.cn）普通高中录取分数表，官方页原始 HTML 存 `data/high/cutoff_score/raw/`（入库跟踪），`python3 data/high/cutoff_score/scripts/fetch_scores.py` 重下官方页（仅每年批次公布时手动跑），`python3 data/high/cutoff_score/scripts/build_scores.py` 解析到 `data/high/cutoff_score/dist/`（每次 check 重跑比对）
- 覆盖批次：第一批次（外语艺术类，末位考生分数口径）/ 第三批次 / 第四批次；2025 与 2026 两年
- 口径：公办=户籍生最低分（另有非户籍生/外区生）；民办/中外合作=最低分数（公费班为独立条目）；外语艺术类=末位考生分数
- 关联：`by_school_id` 按实体主键引用 `data/registry/entity/dist/entities.json`（官方录取表原文名经 `data/registry/entity/scripts/build_entities.py` 的 OFFICIAL_HIGH_ALIAS 桥接 POI 名，全角校区名 ↔ 半角 POI 名系统性差异已治理）；未收录实体（远郊 7 区外 / 中外合作办学项目 / 无 POI 新校）保留在 `unmapped` 官方原文
- 展示：地图卡与详情页同屏展示 2025/2026 两年录取线；levels 的 nature（公办/民办）随官方"学校性质"列联动，民办不再误标"户籍生"口径
- 已核验：levels 旧版 89 校人工录入分数与官方 2025 表逐校比对全部一致（唯一差异=海珠外国语江海校区未被 levels 收录，数据保留在 unmapped）；2026 抽查（华附 739/南武 683/十三中 625/西关培英 607/广州外国语 712/北师大实验 672/为明 500 等）与官方原文一致

### 招生数据（data/primary/enrollments/）

- 番禺（试点闭环）：2026 官方名单 189 条 → 182 条绑定点位、7 条高德缺失
- 荔湾 / 越秀 / 海珠 / 天河：2026 官方文件 252 条 → 211 条绑定点位、41 条高德缺失
- 海珠为官网图片 OCR、天河为扫描 PDF OCR，个别字可能有误差，均以官方原文件为准

## 调研维度（建议）

- 学校类型：公办 / 民办 / 国际学校 / 其他
- 升学路径：学区 / 摇号 / 考试 / 国际路线等
- 学校实力：办学历史、师资、成绩、口碑
- 适配性：孩子特点、通勤距离、学费预算
- 时间节点：幼升小 / 小升初 / 中考 等关键节点

## 状态

### 工程化（本轮完成）
- [x] 数据治理：data/ 收敛为 JSON 唯一真源（小学 971→915、高中 329→126 对齐，tier1 aliases/coords/district 已回写）
- [x] monorepo：npm workspaces（packages/shared + apps/web + apps/miniprogram）
- [x] @gz/shared 共享核心包：类型 + 常量 + geo/stats/support 纯函数（esm + cjs 双产物）
- [x] Web Vue3 重构：Vite + vue-router（hash），入口/地图（Leaflet+高德瓦片+区筛选+学段配色）/初中明细，数据全部来自 data/*.json + shared
- [x] 微信小程序原生骨架：pages/index + map（内置 <map>，GCJ-02）；构建脚本生成 shared/data 产物
- [x] 旧版页面下线：apps/web/map、support.html、legacy/ 及纯产物脚本已删除（git 历史保留）；数据脚本只写 json 真源
- [x] GitHub Pages 部署：pages.yml 仅构建新版 SPA + img/，部署为站点根
- [ ] 小程序打开体验完善：marker 聚类 / 梯队配色 icon / 详情页

### 小学阶段
- [x] 确定调研范围与目标（7 区）
- [x] 收集候选学校清单（915 所小学，2026-09-08 快照，已去重）
- [x] 搭建 Web 应用（apps/web，地图为当前功能）
- [x] 番禺招生数据试点闭环（2026，182/189 绑定）
- [x] 荔湾 / 越秀 / 海珠 / 天河 + 番禺统一构建（2026，400/441 绑定，含 NAME_MAP 映射表）
- [x] 网传"口碑学校"清单保留为学校名单（58 所，保留历史称号/集团/学位预警/招生班数等源数据，2026-09-15 口碑判定已移除，不再做梯队评分）
- [ ] 白云、黄埔招生数据（低优先级）
- [ ] 未匹配 42 所逐校核实（新建校/更名）

### 初中阶段
- [x] 目录结构分离（data/primary/ + data/middle/）
- [x] 7 区初中点位采集（已剔除增城，2026-09-09 快照，296 所 + 14 补点）
- [x] 各区网传初中清单 + 客观数据保留（54 所，保留历史称号/集团/喜报/录取线/自招等源数据；2026-09-15 口碑判定已移除，不再做梯队评分）
- [x] 中小学合并地图（四类配色 + 筛选）

### 高中阶段
- [x] 7 区高中点位采集（2026-09-09 快照，126 点，90 所学校）
- [x] 官方口径分类（省市属示范 11 / 区属示范 43 / 普通高中 36，依据招考办名额分配名单与录取表）
- [x] 逐校客观指标（特控线上线率 / 高分段 / 本科率，喜报与网传口径已注明）
- [x] **中考录取分官方链路**（2025/2026 两年，脚本抓取招考办录取表 → cutoff_score/dist/scores_{year}.json，school_id 引用实体表；levels 移除人工录入分数，补 nature 民办标志，页面同屏两年展示）
- [x] 三学段合并地图（七类配色 + 筛选 + 高中信息卡）
- [ ] 个别学校指标核实（"网传 / 未公开"项逐条回查官方渠道）

### 教育集团齐全化
- [x] **P0** 招考办 2026 集团名额分配表落盘（`data/registry/group/parsed/education_groups_2026.json`，43 核心校 / 118 成员关系，官方源 http://gzzk.gz.gov.cn/gkmlpt/content/10/10809/post_10809470.html ）
- [x] **P1** 集团成员覆盖比对（`data/registry/group/docs/coverage/集团成员覆盖清单_P1.md`，161 校逐一比对 POI 三层：精确命中 49 / 变体命中 45 / 7 区内真实缺失 2 / 远郊不在范围 65）
- [x] **P2** 8 品牌组官方来源交叉核实（`data/registry/group/src/brand_groups.json`，新增 25 个成员单位，全部附来源 URL + 法人关系标注；单测 12/12 通过，快照已更新）
- [x] **P3** 区属非示范集团 + 小学集团全量（7区85个教育集团/334所成员校，`data/registry/group/dist/education_groups.json`，覆盖清单见 `data/registry/group/docs/coverage/集团成员覆盖清单_P3.md`；POI精确命中157/变体命中167/7区内缺失2/远郊8；缺失2所=三元里中学（已补录实体，2026-09-15）+广龙地块配建学校（建设中））
- [ ] **P4** 年度更新机制（每年 5 月招考办新表发布后跑更新脚本）

## 安全约定

- 所有 Key / token 只放 `.env`（已 git 忽略），代码与页面不出现明文凭据
- 地图瓦片为公开服务，页面本身无需 Key
