# 广州学校升学路线调研

为孩子寻找合适升学路线的调研项目。系统性调研广州地区的学校与升学路径，综合考虑学校实力、入学方式、孩子特点与家庭条件，形成可执行的升学决策建议。

## 目录结构

```
.
├── apps/                    # 各端应用
│   ├── web/                 # Web 应用（Vue3 + Vite，npm run dev/build）
│   │   ├── index.html       # 应用入口
│   │   ├── src/             # Vue3 工程：pages（入口/地图/支撑度）、data 加载层
│   │   └── package.json     # @gz/web
│   ├── miniprogram/         # 微信小程序（原生，根目录 = apps/miniprogram）
│   │   ├── app.json / app.js / app.wxss
│   │   ├── pages/           # index（入口）/ map（内置 <map>）/ support（支撑度）
│   │   ├── utils/data.js    # 数据加载（shared + data 构建产物）
│   │   ├── shared/          # 构建产物：@gz/shared cjs（git 忽略，npm run build:mp 生成）
│   │   └── data/            # 构建产物：data/*.json → CommonJS 模块（git 忽略）
│   └── README.md
├── packages/
│   └── shared/              # @gz/shared 双端共享核心包（TS：类型 + 纯逻辑，零平台依赖）
│       └── src/             # types / const / geo / stats / support
├── data/                    # 共享数据层（JSON 唯一真源，多端共用）
│   ├── primary/             # 小学阶段数据（schools-gz.json / tier1_schools_all.json / enrollments/）
│   ├── middle/              # 初中阶段数据（schools-gz.json / tier1_schools_all.json）
│   ├── high/                # 高中阶段数据（schools-gz.json 清洗版 / levels.json / scores_{year}.json 官方录取分 / 剔除留痕）
│   └── README.md            # 数据治理约定与更新方式
├── scripts/                 # 共享脚本（数据采集/构建 + 小程序构建）
│   ├── fetch_schools.py     # 小学点位采集（写 json 真源）
│   ├── fetch_middle_schools.py  # 初中点位采集
│   ├── fetch_high_schools.py    # 高中原始采集
│   ├── build_high_levels_js.py  # 高中清洗点位（按 levels.json 清洗并写回 json 真源）
│   ├── build_scores.py          # 高中录取分抓取（招考办官网 2025/2026 录取表 → scores_{year}.json，零依赖）
│   ├── registry/build_entities.mjs  # 实体注册表（school_id 主键 + 官方名/别名桥接）
│   ├── build_district_enrollment.py  # 五区小学招生数据
│   ├── backfill_schools.py  # 小学缺校补位
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

数据真源约定：`data/` 下 JSON 为唯一数据真源，Web 与小程序均从该层构建加载，勿手改产物；
小程序包内 `shared/`、`data/` 为构建产物（git 忽略，由 `npm run build:mp` 生成）。


## Web 应用（apps/web）

新版（Vue3 + Vite）：`npm run dev:web` 开发，`npm run build:web` 构建；入口 `apps/web/index.html`，
路由 `#/`（入口）/ `#/map`（地图）/ `#/support`（支撑度），数据经 `src/data/` 从 `data/*.json`（真源）加载，
逻辑复用 `@gz/shared`。构建产物 `apps/web/dist` 可由静态服务器 / GitHub Pages 直接部署（hash 路由，file:// 亦可打开）。

### 中小学·高中合并地图（apps/web#/map）
- 同时展示广州 7 区（荔湾 / 越秀 / 海珠 / 天河 / 白云 / 黄埔 / 番禺）三学段点位：915 小学 + 3 补点、296 初中 + 14 补点（1 所与 POI 重合去重）、126 高中点位（90 所学校，含多校区）
- 七类配色：小学·普通（浅灰蓝）/ 小学·口碑（蓝）/ 初中·普通（暖浅灰）/ 初中·口碑（红）/ 高中普通（灰蓝）/ 高中区属示范（绿）/ 高中省市属示范（琥珀），口碑校按支撑度加粗、有支撑加晕光
- 左侧筛选区：7 个 checkbox + 全选 / 全不选，实时控制点位显示并同步图例统计
- 点击点位展示信息卡：小学（招生数据 + 梯队信号）、初中（中考信号 + 梯队徽标），并链接“支撑度”说明页；高中（分类徽标 + 示范性等级·隶属 + 特控线上线率 / 高分段 / 本科率 + 2025 中考录取线 + 口径说明）
- 区边界色块 + 各区数量图例统计（小学 / 初中 / 高中三栏）；视野锁定七区范围
- 纯本地数据渲染，不做实时请求

地图是 web 应用当前首个功能，后续按子功能目录扩展学校详情、对比、路线规划等。

## 数据

### 小学点位数据（data/primary/schools-gz.json）

- 来源：高德地图 Web 服务 API，2026-09-08 快照（GCJ-02 坐标系）
- 共 915 所：荔湾 75 / 越秀 78 / 海珠 120 / 天河 115 / 白云 227 / 黄埔 101 / 番禺 199
- 已合并同校重复 POI；番禺含 backfill 补充点
- 通过翻页采集突破单区 100 条上限
- 更新：`python3 scripts/primary/fetch_schools.py`（需 `.env` 中的 `AMAP_WEB_KEY`）

### 初中点位数据（data/middle/schools-gz.json）

- 来源：高德地图 Web 服务 API，2026-09-09 快照（GCJ-02 坐标系）
- 范围：7 区（荔湾 / 越秀 / 海珠 / 天河 / 白云 / 黄埔 / 番禺），排除远郊南沙 / 花都 / 从化 / 增城
- 采集：types=141201（初中分类）+ types=141200（中学分类）+ 关键词「初中」三路翻页合并，保留初中与完全中学
- 更新：`python3 scripts/middle/fetch_middle_schools.py`

### 高中点位与分类指标（data/high/）

- 点位来源：高德地图 Web 服务 API，2026-09-09 快照（GCJ-02 坐标系）；types=141202（高中）+ 关键词「高中」+ types=141200（中学）三路翻页合并，剔除培训机构 / 复读 / 托管 / 职业类等，再按 90 所学校清单精确清洗（清洗版点位即 `schools-gz.json`，由 build_high_levels_js.py 写回）
- 范围：7 区（荔湾 / 越秀 / 海珠 / 天河 / 白云 / 黄埔 / 番禺），排除远郊南沙 / 花都 / 从化 / 增城
- 分类口径（替换民间"市重点 / 区重点"的官方称谓）：
  - **省市属示范**（11 所）= 省属或市属示范性高中（国家级示范 / 市示范 / 市属优质，含市属名额分配新增校），对应民间"市重点"
  - **区属示范**（43 所）= 区属国家级 / 市级示范性高中，对应民间"区重点"
  - **普通高中**（36 所）= 其余公办（省一级等）+ 民办
- 分类依据（广州市招考办官方文件）：2026 名额分配招生学校名单、2025 第三批录取表、2025 第四批录取表
- 客观指标（levels.json，逐校）：特控线上线率 2026 / 2025（含网传口径）、600 分以上高分段占比、本科率、隶属与示范性等级、nature（公办/民办，取官方录取表"学校性质"列）；无公开数据的学校如实标注"高考出口数据未公开"
  - 特控率来源：2026 高考喜报（广州日报报道）+ 2025 年 51 校成绩汇总，均为喜报 / 网传口径，非官方统一发布（页面卡片已注明）
  - **中考录取分已迁出 levels**：2025/2026 两年官方分数见 `data/high/scores_2025.json` / `scores_2026.json`（由脚本从招考办官网录取表抓取，按 school_id 引用实体表），levels 不再存任何分数
- 点位统计：126 个（含 15 个高德补点），荔湾 17 / 越秀 18 / 海珠 14 / 天河 19 / 白云 25 / 黄埔 14 / 番禺 19
- 更新：`python3 scripts/high/fetch_high_schools.py`（原始 POI）→ `python3 scripts/high/build_high_levels_js.py`（按 levels.json 清洗点位并写回 json 真源）；录取分链路见「高中录取分数（data/high/scores_{year}.json）」一节

### 高中录取分数（data/high/scores_{year}.json）

- 真源：广州市招考办官网（gzzk.gz.gov.cn）普通高中录取分数表，脚本抓取解析（零第三方依赖，`python3 scripts/high/build_scores.py [--fetch]` 重下官方页）
- 覆盖批次：第一批次（外语艺术类，末位考生分数口径）/ 第三批次 / 第四批次；2025 与 2026 两年
- 口径：公办=户籍生最低分（另有非户籍生/外区生）；民办/中外合作=最低分数（公费班为独立条目）；外语艺术类=末位考生分数
- 关联：`by_school_id` 按实体主键引用 `data/registry/entities.json`（官方录取表原文名经 `scripts/registry/build_entities.mjs` 的 OFFICIAL_HIGH_ALIAS 桥接 POI 名，全角校区名 ↔ 半角 POI 名系统性差异已治理）；未收录实体（远郊 7 区外 / 中外合作办学项目 / 无 POI 新校）保留在 `unmapped` 官方原文
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
- [x] Web Vue3 重构：Vite + vue-router（hash），入口/地图（Leaflet+高德瓦片+区筛选+梯队配色）/支撑度三页，数据全部来自 data/*.json + shared
- [x] 微信小程序原生骨架：pages/index + map（内置 <map>，GCJ-02）+ support；构建脚本生成 shared/data 产物
- [x] 旧版页面下线：apps/web/map、support.html、legacy/ 及纯产物脚本已删除（git 历史保留）；数据脚本只写 json 真源
- [x] GitHub Pages 部署：pages.yml 仅构建新版 SPA + img/，部署为站点根
- [ ] 小程序打开体验完善：marker 聚类 / 梯队配色 icon / 详情页

### 小学阶段
- [x] 确定调研范围与目标（7 区）
- [x] 收集候选学校清单（915 所小学，2026-09-08 快照，已去重）
- [x] 搭建 Web 应用（apps/web，地图为当前功能）
- [x] 番禺招生数据试点闭环（2026，182/189 绑定）
- [x] 荔湾 / 越秀 / 海珠 / 天河 + 番禺统一构建（2026，400/441 绑定，含 NAME_MAP 映射表）
- [x] 网传"口碑学校"核验（59 所，有支撑 21 / 部分支撑 36）
- [ ] 白云、黄埔招生数据（低优先级）
- [ ] 未匹配 42 所逐校核实（新建校/更名）

### 初中阶段
- [x] 目录结构分离（data/primary/ + data/middle/）
- [x] 7 区初中点位采集（已剔除增城，2026-09-09 快照，296 所 + 14 补点）
- [x] 各区网传口碑学校初中名单 + 客观数据核验（53 所，有支撑 41 / 部分支撑 12）
- [x] 中小学合并地图（四类配色 + 筛选）

### 高中阶段
- [x] 7 区高中点位采集（2026-09-09 快照，126 点，90 所学校）
- [x] 官方口径分类（省市属示范 11 / 区属示范 43 / 普通高中 36，依据招考办名额分配名单与录取表）
- [x] 逐校客观指标（特控线上线率 / 高分段 / 本科率，喜报与网传口径已注明）
- [x] **中考录取分官方链路**（2025/2026 两年，脚本抓取招考办录取表 → scores_{year}.json，school_id 引用实体表；levels 移除人工录入分数，补 nature 民办标志，页面同屏两年展示）
- [x] 三学段合并地图（七类配色 + 筛选 + 高中信息卡）
- [ ] 个别学校指标核实（"网传 / 未公开"项逐条回查官方渠道）

### 教育集团齐全化
- [x] **P0** 招考办 2026 集团名额分配表落盘（`data/registry/education_groups_2026.json`，43 核心校 / 118 成员关系，官方源 http://gzzk.gz.gov.cn/gkmlpt/content/10/10809/post_10809470.html ）
- [x] **P1** 集团成员覆盖比对（`docs/education-groups-coverage/集团成员覆盖清单_P1.md`，161 校逐一比对 POI 三层：精确命中 49 / 变体命中 45 / 7 区内真实缺失 2 / 远郊不在范围 65）
- [x] **P2** 8 品牌组官方来源交叉核实（`data/registry/brand_groups.json`，新增 25 个成员单位，全部附来源 URL + 法人关系标注；单测 12/12 通过，快照已更新）
- [ ] **P3** 区属非示范集团 + 小学集团全量（华阳、体育东、天府、东风东等）按各区文件补录
- [ ] **P4** 年度更新机制（每年 5 月招考办新表发布后跑更新脚本）

## 安全约定

- 所有 Key / token 只放 `.env`（已 git 忽略），代码与页面不出现明文凭据
- 地图瓦片为公开服务，页面本身无需 Key
