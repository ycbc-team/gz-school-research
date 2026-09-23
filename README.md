# 广州学校升学路线调研

为孩子寻找合适升学路线的调研项目。系统性调研广州地区的学校与升学路径，综合考虑学校实力、入学方式、孩子特点与家庭条件，形成可执行的升学决策建议。

## 业务模块

每个业务模块的信息都维护在**各自的 README**，本文件只给概览与入口；数据细节一律以各业务 README 为准。

| 模块 | 路径 | 概要 | 业务 README |
|---|---|---|---|
| Web 应用 | `apps/web/` | Vue3 + Vite 单页：七区三学段合并地图（`#/map`）、初中升学信号明细（`#/middle`）、学校详情 | [`apps/web/README.md`](apps/web/README.md) |
| 微信小程序 | `apps/miniprogram/` | 原生小程序骨架（入口/地图），shared + data 构建产物由 `npm run build:mp` 生成 | [`apps/miniprogram/README.md`](apps/miniprogram/README.md) |
| 共享核心包 | `packages/shared/` | `@gz/shared`：类型 + geo/stats/support 纯逻辑（esm + cjs），Web/小程序同构复用 | — |
| 数据层总则 | `data/` | JSON 唯一真源；数据治理约定、坐标系、新校核对流程、数据依赖链（源头→脚本→产物→运行时） | [`data/README.md`](data/README.md) |
| 小学招生 | `data/primary/enrollment/` | 2026 七区公办小学招生地段/计划，ABC 三层（转录/匹配/合并）；含 **POI 未匹配逐区处置经验**（荔湾/白云/越秀/天河/番禺/海珠） | [`data/primary/enrollment/README.md`](data/primary/enrollment/README.md) |
| 小学升学路线 | `data/primary/transition/` | 小升初对口/派位/直升记录、初中生源反查（middlePrimaryFeed）、生源快照测试 | [`data/primary/transition/README.md`](data/primary/transition/README.md) |
| 初中招生/排序 | `data/middle/` | 公办初中招生计划、默认排序（org_sort） | `data/README.md` |
| 高中 | `data/high/` | 高中清单/分类指标（levels.json）、录取分数（cutoff_score） | `data/README.md` |
| POI 点位 | `data/poi/` | 高德快照三学段点位（GCJ-02），采集/清洗脚本 | `data/README.md` |
| 实体表 | `data/registry/entity/` | `school_id` 维度枢纽，POI—Entity—Fact 三分离；SchoolMatcher 别名桥接 | [`data/registry/entity/README.md`](data/registry/entity/README.md) |
| 教育集团 | `data/registry/group/` | 政府源→成员→校区解析、品牌关联、P0–P4 任务状态 | [`data/registry/group/README.md`](data/registry/group/README.md) |
| 民办名单 | `data/registry/private/` | 民办学校真源（官方年检 + 7 区采集） | [`data/registry/private/README.md`](data/registry/private/README.md) |
| 升学通道数据 | `data/linkage/` | 名额分配矩阵、第二批次录取分、自招/特长生名单、初中升学信号；含 **OCR 方案记录**（踩坑/已弃用方案） | [`data/linkage/README.md`](data/linkage/README.md) |
| 调研文档 | `docs/` | 架构说明（architecture.md）、数据源调研、分析报告、新校核对清单 | `docs/architecture.md` |

## 顶层目录结构

```
apps/           各端应用（web / miniprogram，详见各子目录 README）
packages/       共享核心包 @gz/shared
data/           共享数据层（JSON 唯一真源，详见 data/README.md 与各业务 README）
scripts/        共享脚本（数据构建/检查/小程序构建）
docs/           调研报告、分析文档
.env            本地密钥（git 忽略，不入库）
```

## 开发命令

```bash
npm install                    # 安装 workspace 依赖（npm workspaces）
npm run build:shared          # 构建 @gz/shared（dist/esm + dist/cjs）
npm run dev:web               # 启动 Vue3 Web 开发服务器（Vite）
npm run build:web             # 构建 Vue3 Web 产物（apps/web/dist）
npm run build:mp              # 生成小程序 shared/data 构建产物
npm run check                 # 全量校验（类型检查 + 单测 + 数据质量 + 产物漂移 + 快照 + 竞赛构建）
```

代码分层、数据流与构建边界见 [`docs/architecture.md`](docs/architecture.md)。历史改造方案仅作迁移留档，不应作为当前实现依据。

数据真源约定：`data/` 下 JSON 为唯一数据真源，Web 与小程序均从该层构建加载，勿手改产物；小程序包内 `shared/`、`data/` 为构建产物（git 忽略，由 `npm run build:mp` 生成）。

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

## 调研维度（建议）

- 学校类型：公办 / 民办 / 国际学校 / 其他
- 升学路径：学区 / 摇号 / 考试 / 国际路线等
- 学校实力：办学历史、师资、成绩、口碑
- 适配性：孩子特点、通勤距离、学费预算
- 时间节点：幼升小 / 小升初 / 中考 等关键节点

## 当前状态（2026-09-23）

- **工程化**：monorepo（npm workspaces：shared + web + miniprogram）；GitHub Pages 部署（hash 路由 SPA）；旧版页面/产物已清理
- **小学**：7 区 2026 公办小学招生全量构建（C 层 781 条记录，ABC 三层）；POI 未匹配点位七区逐校核实清零（处置经验见小学招生 README）；网传口碑名单保留为学校名单（不做梯队评分）
- **初中**：7 区点位采集（309 点）、升学信号明细（自招/指标/特控率，334 校）、合并地图；公办初中招生计划已迁入 `data/middle/enrollment/`
- **高中**：7 区点位（126 点，90 校）、官方口径分类（省市属示范 11 / 区属示范 43 / 普通 36）、2025/2026 录取分官方链路
- **教育集团**：P0–P3 完成（招考办名额分配表、成员覆盖比对、8 品牌组、区属非示范集团全量 85 个/334 成员校）；P4 年度更新机制待建

## 安全约定

- 所有 Key / token 只放 `.env`（已 git 忽略），代码与页面不出现明文凭据
- 地图瓦片为公开服务，页面本身无需 Key
