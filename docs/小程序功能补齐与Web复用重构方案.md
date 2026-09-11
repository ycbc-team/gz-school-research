# 小程序功能补齐与 Web 复用重构方案

> 目标：把小程序从 "三页骨架" 补齐到与 Web 对齐（地图全功能 / 学校详情 / 升学通道 / 政策说明 / 支撑度）。
> 手段：重构 Web 侧，把业务层与数据层下沉到 
>
> `@gz/shared`
>
> ，双端只保留各自的 UI 层（View）与平台适配层。
> 状态：已确认（2026-09-11 拍板）・2026-09-11



***

## 1. 现状盘点

### 1.1 两端功能矩阵



| 功能                   | Web（Vue3）                                       | 小程序（原生）                       | 差距     |
| -------------------- | ----------------------------------------------- | ----------------------------- | ------ |
| 首页统计                 | HomeView.vue（96 行）                              | pages/index（基础统计）             | 基本对齐   |
| 三学段地图                | MapView.vue（764 行）                              | pages/map（仅小学点位 + 区筛选，约 50 行） | **大**  |
| 地图七类配色 / 梯队图标        | ✅ 七类配色 + 有支撑加粗 / 晕光 / 挂牌虚线                      | ❌ 单一默认图标                      | **大**  |
| 地图三级筛选（区域 / 学段 / 分级） | ✅ 贝壳式浮层                                         | ❌ 仅区域单选                       | **大**  |
| 地图搜索                 | ✅ 按校名搜索 + 徽章                                    | ❌                             | 缺失     |
| 地图点选信息卡              | ✅ 高中指标 / 小学初中梯队信号 + 招生条件                        | ❌                             | 缺失     |
| 地图 → 详情跳转            | ✅ `/school/:stage/:name`                        | ❌                             | 缺失     |
| 学校详情页                | SchoolDetailView.vue（561 行）                     | ❌ 无                           | **缺失** |
| 口碑支撑度                | SupportView.vue（232 行，完整信号列）                    | pages/support（简化列表）           | 中等     |
| 升学通道（名额分配 / 特招）      | LinkageView.vue（181 行）+ LinkagePanel.vue（227 行） | ❌ 无                           | **缺失** |
| 招生政策说明               | PolicyView.vue（185 行）                           | ❌ 无                           | 缺失     |
| marker 聚类            | ❌（Web 未做）                                       | ❌                             | 两端都待做  |

### 1.2 现有复用情况



* `packages/shared`**（@gz/shared）**：已有 types /const/geo /stats/support /format，约 **525 行**纯 TS，双产物（ESM + CJS）已打通双端：


  * Web：`import { ... } from '@gz/shared'`（Vite ESM）

  * 小程序：`npm run build:mp` 把 `shared/dist/cjs` 拷入 `apps/miniprogram/shared/`，页面 `require('../../shared/index.js')`

* **数据真源**：`data/**/*.json`，Web 用 Vite JSON import，小程序由 `scripts/miniprogram/build.mjs` 转成 CommonJS 模块拷贝进包。

* **已下沉到 shared 的逻辑**：`normName`、`buildAliasTable`、`matchTier1ByPoiName`、`attachTier1ToPois`、`matchBrandByPoiName`、`summarizeSchools`、`formatPrimarySignals`、`formatMiddleSignals` 等纯函数。

### 1.3 复用瓶颈（问题诊断）



1. **真正的业务逻辑在 Web 应用内，没进共享包**。

   `apps/web/src/data/index.ts`（**422 行**）才是核心业务层：完中判定、升学通道矩阵查询（`linkageOf` / `specialOf` / `batch2Of` / `quotaCoverage` / `specialCoverage`）、小学招生计划匹配（`matchEnrollment`，含精确 / 归一 / 模糊三级兜底）、生源小学反查（`middlePrimaryFeed`）、学校徽章（`schoolBadges` / `supportBadge`）、学校身份注册表（`resolveSite`）、品牌关联（`brandGroupOf`）、校区映射表（`CAMPUS_SHORT` / `CAMPUS_SCHOOL` / `CAMPUS_TO_SPECIAL` / `CAMPUS_TO_BATCH2`）。

   它**没有任何 Vue/DOM 依赖，纯函数即可迁移**—— 但停留在 `apps/web/src`，小程序完全无法复用。小程序 `utils/data.js` 只有 24 行数据加载，没有业务层，所以每个功能都得从零写。

2. **页面组件里混着大量 "该共享" 的逻辑**。

* `MapView.vue` 764 行中约一半是业务逻辑：点位构建（`buildPoints`，三学段 + tier 匹配 + 补点去重）、梯队判定（`tierOf` / `isTierRecord`）、高中分类（`highRecord` / `highCls`）、筛选状态机（区域 / 学段 / 分级三组 Set）、信息卡模型构建（`infoModel`，高中 / 梯队 / 挂牌 / 普通四分支）、搜索（`searchResults` / `badgesOf`）。这些**与 Leaflet 无关**，只依赖 `@gz/shared` + 数据。

* `SchoolDetailView.vue` 561 行同理：详情页的字段行、徽章、信号格式化、出口数据口径、品牌关联等都是纯业务，只有顶部模板是 Vue。

* `SupportView.vue` / `LinkageView.vue` 的表格构建逻辑也是纯函数。

1. **两端状态管理各自为政**：Web 用 Vue `ref`/`computed`，小程序用 `setData`，筛选、选中态、搜索态没有统一模型，未来两端行为会漂移。



***

## 2. 目标架构：MVVM 分层 + 共享业务层

借鉴 MVVM 分层思想，按 "**平台相关性**"切分，复用边界放在" 与 UI 无关的业务逻辑 "：



```
┌─────────────────────────── View 层（各端独有，不复用）───────────────────────────┐

│  Web:    Vue 组件 + Leaflet 渲染 + vue-router                                    │

│  小程序:  Page + WXML/WXSS + \<map> + wx.navigateTo                               │

└─────────────────────────────────────────────────────────────────────────────────┘

&#x20;                                   ▲ 平台适配层（薄）：

&#x20;                                   │ Web: ref/computed 包装；小程序: setData 绑定

┌─────────────────────────── ViewModel / 业务服务层（共享）────────────────────────┐

│  packages/shared/src/domain/  —— 纯 TS，零平台依赖，双端复用                      │

│   · map/      点位构建 · 梯队/分类判定 · 筛选状态机 · 信息卡模型 · 搜索             │

│   · detail/   学校详情模型（各学段字段行/徽章/出口数据口径/品牌关联）               │

│   · linkage/  升学通道查询（名额分配/特招/第二批次）                               │

│   · support/  支撑度表格模型（信号列/分组统计）                                    │

└─────────────────────────────────────────────────────────────────────────────────┘

&#x20;                                   ▲

┌─────────────────────────── Model / 数据层（共享）───────────────────────────────┐

│  packages/shared/src/data/  —— Repository/查询接口（从 apps/web/src/data 下沉）    │

│  · loader 接口（各端注入数据，保持"数据不内嵌"约定）                               │

│  · 查询服务：enrollment / quota / linkage / site / brand / badges / 完中判定      │

│  data/\*\*/\*.json  —— 唯一真源（Web JSON import / 小程序 CJS 构建产物）              │

└─────────────────────────────────────────────────────────────────────────────────┘
```



* **View**：双端 UI 天然不同（DOM vs WXML），不追求复用，只追求 "薄"。

* **ViewModel**：复用的核心。小程序原生 Page 本身就是一个 VM（data + methods + 模板绑定），Web 的 Vue 组件也是 VM。两者共同需要的那部分 "**领域逻辑**" 抽成共享 service（等价于把 VM 的纯逻辑部分上移一层）。状态用**纯 TS Store**（普通对象 + 订阅 / 快照），双端各自做响应式适配：Web 用 `reactive`/`computed` 包一层，小程序 `setData` 拉取渲染切片。

* **Model**：`data/*.json` 真源不变；`@gz/shared/src/data/` 提供统一查询接口，双端注入各自的 loader。

> 不引入共享的响应式框架（Pinia/MobX 等）：小程序原生环境无法直接复用，且为 2MB 包体积增加重量。纯 TS 是最低成本的共享形态，这也延续了 @gz/shared 现有约定。



***

## 3. Web 侧重构方案（按文件）

### 3.1 `apps/web/src/data/index.ts` → `packages/shared/src/data/`

422 行整体迁移，拆为职责清晰的模块（保持现有导出名，Web 引用处改 import 来源即可）：



| 迁移目标                 | 内容                                                                                                                                                        |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `data/schools.ts`    | 数据加载抽象 + `isComprehensive` 完中判定                                                                                                                           |
| `data/enrollment.ts` | `normSchoolName` / `matchEnrollment`（精确→归一→模糊）                                                                                                            |
| `data/quota.ts`      | `QuotaSchool` / `QuotaMatrix` / `linkageOf` / `specialOf` / `batch2Of` / `quotaCoverage` / `specialCoverage` / `middleQuotaSummary` / `middlePrimaryFeed` |
| `data/badges.ts`     | `schoolBadges` / `supportBadge` / `SchoolBadge`                                                                                                           |
| `data/registry.ts`   | `resolveSite` / `brandGroupOf` / `BrandGroup` 类型                                                                                                          |
| `data/campuses.ts`   | `CAMPUS_SHORT` / `CAMPUS_SCHOOL` / `CAMPUS_TO_SPECIAL` / `CAMPUS_TO_BATCH2`                                                                               |

**关键设计 ——loader 注入**：shared 不直接 `import data/*.json`（保持 "数据不内嵌" 约定，且小程序 require CJS 产物、Web import JSON 的机制不同）。改为：



```
// packages/shared/src/data/loader.ts

export interface DataLoaders {

&#x20; primarySchools: SchoolsSnapshot;

&#x20; primaryTier1: Tier1Snapshot;

&#x20; middleSchools: SchoolsSnapshot;

&#x20; middleTier1: Tier1Snapshot;

&#x20; highSchools: SchoolsSnapshot;

&#x20; highLevels: HighLevelsSnapshot;

&#x20; enrollments: EnrollmentSnapshot\[];

&#x20; quotaMatrix: QuotaMatrix;

&#x20; specialMatrix: SpecialMatrix;

&#x20; batch2Scores: Batch2Scores;

&#x20; sites: SiteRegistry;

&#x20; brandGroups: BrandGroups;

}

export function createRepository(loaders: DataLoaders) { ... }
```



* Web 端：`apps/web/src/data/loader.ts` 保留现有 JSON import 组装 `DataLoaders`，一行注入。

* 小程序端：`apps/miniprogram/utils/data.js` 用现有 `require` 组装同一结构注入。

* 好处：shared 保持可单测、可 tree-shake；查询表（`enrollByNorm`、`middleByNorm` 等）在 `createRepository` 内部构建一次，双端行为完全一致。

### 3.2 MapView 业务逻辑 → `packages/shared/src/domain/map/`

从 `MapView.vue` 抽出的纯逻辑（均与 Leaflet 无关）：



| 模块                 | 内容                                                                                                                        | 说明                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `map/points.ts`    | `buildPoints(loaders)` → `MapPoint[]`（三学段点位 + tier / 高中分类 + 补点去重）                                                         | 现在的 `buildPoints` / `tierOf` / `isTierRecord` / `highRecord` / `highCls` |
| `map/constants.ts` | `CLASS_CFG`（七类配色 label / 颜色 / 学段）、`DISTRICTS`（区 + adcode + 边界色）、`GRADE_GROUPS` / `STAGE_TABS`（筛选 UI 枚举）                   | 颜色值同时是 Web CSS 与小程序 marker 图标的输入                                         |
| `map/filters.ts`   | `createMapFilterStore()` → `{ selectedDistricts, selectedStages, selectedGrades, toggle, flip, isVisible, visibleCount }` | 纯 TS 状态机，返回快照 + 变更方法                                                     |
| `map/info.ts`      | `buildInfoModel(point, loaders)` → 信息卡模型（高中 / 梯队 / 挂牌 / 普通四分支 + 招生条件 + 详情链接参数）                                            | 现在 `infoModel` computed 的纯函数版                                            |
| `map/search.ts`    | `searchSchools(points, kw)`                                                                                               | 现在 `searchResults`                                                       |

**Web 端瘦身后的 MapView.vue（预估 764 → \~380 行）**：



* `setup` 里只做三件事：注入 loader 调 `createRepository`；调 `buildPoints` / `createMapFilterStore`；把 store 状态用 `reactive`/`computed` 包装成响应式。

* 模板保留浮层、Leaflet 地图容器、信息卡 DOM。

* Leaflet 渲染（`renderPoints` / `renderBoundaries` / `applyFilters` / `markerStyle`）留在组件，但 `markerStyle` 的输入（`cls`/`tier`）来自共享的 `MapPoint`，保证两端同一数据不同渲染。

### 3.3 SchoolDetailView 逻辑 → `packages/shared/src/domain/detail/`



* `detail/model.ts`：`buildDetailModel(stage, name, repository)` → 详情页全部数据模型（学段 / 区 / 徽章 / 招生计划 / 口碑信号 / 出口机制 / 对口初中 / 生源小学 / 高中指标 / 品牌关联 / 教育集团）。

* `LinkagePanel.vue` 的数据组装（`quotaCoverage` / `specialCoverage` 反查）同样下沉到 `domain/linkage/`。

* Web `SchoolDetailView.vue`（预估 561 → \~320 行）只保留路由 props 解析、模板、返回 / 跳地图交互。

### 3.4 Support / Linkage / Policy



* `SupportView.vue` 的 `buildRows` / `fmtCells` / 分组统计 → `domain/support/table.ts`。

* `LinkageView.vue` 的候选列表 / 筛选 / 选中态 → `domain/linkage/store.ts`（复用 `createMapFilterStore` 同一套纯 TS 状态机模式）。

* `PolicyView.vue` 是纯静态文案页，无业务逻辑，不迁移（小程序如需，直接搬文案）。

### 3.5 Web 端验证



* `npm run check`（全 workspace 类型检查）+ `npm run build:web` 零回归。

* shared 新增模块补单测（沿用 `packages/shared/tests/` 现有 vitest / 快照方式），重点覆盖：`matchEnrollment` 三级兜底、`linkageOf` 归一匹配、`buildPoints` 去重、筛选状态机。



***

## 4. 小程序侧实现方案

### 4.1 构建链路（现有机制扩展，无需新基建）

`scripts/miniprogram/build.mjs` 已做两件事，扩展后不变：



1. 拷贝 `packages/shared/dist/cjs` → `apps/miniprogram/shared/`（domain + data 层自动带上）

2. 把 `data/**/*.json` 转 CJS → `apps/miniprogram/data/`

小程序 `utils/data.js` 改为组装 `DataLoaders` 并调 `createRepository`，页面全部从 repository + domain service 取数：



```
// apps/miniprogram/utils/data.js（改造后）

const shared = require('../shared/index.js');

const { createRepository } = shared;

module.exports = createRepository({

&#x20; primarySchools: require('../data/primary/schools-gz.js'),

&#x20; primaryTier1: require('../data/primary/tier1\_schools\_all.js'),

&#x20; // ...其余 loader 同构

});
```

### 4.2 各页面补齐路线



| 页面                        | 现状 → 目标                                         | 页面 JS 形态                                                                                                   |
| ------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `pages/map`               | 小学 + 区筛选 → **三学段七类配色 + 三级筛选 + 搜索 + 信息卡 + 详情跳转** | 调用 `buildPoints` + `createMapFilterStore` + `buildInfoModel` + `searchSchools`；`<map>` 的 markers 由共享点位模型渲染 |
| `pages/school-detail`（新增） | 详情页                                             | 调用 `buildDetailModel`，WXML 渲染                                                                              |
| `pages/linkage`（新增）       | 升学通道                                            | 调用 `domain/linkage`                                                                                        |
| `pages/support`           | 简化列表 → 完整信号列                                    | 调用 `domain/support/table`                                                                                  |
| `pages/index`             | 统计 → 对齐 Web 首页入口                                | 调 `summarizeSchools`（已有）                                                                                   |

### 4.3 小程序地图渲染要点（与 Web 的差异点）



* **七类配色**：微信 `<map>` 的 `markers[].icon` 需要本地图片路径。方案：由 `map/constants.ts` 的七类配置**生成 7 张小圆点图标 PNG**（构建脚本 `scripts/miniprogram/build.mjs` 增加一步：用 shared 的颜色值渲染 base64/PNG 写入 `apps/miniprogram/assets/markers/`），两端颜色永远一致。

* **1000+ markers 性能**：915 小学 + 296 初中 + 126 高中 ≈ 1300+ 点，直接全量 `markers` 会卡。方案：


  * 按筛选结果**仅渲染可见集**（复用共享 `isVisible`）；

  * 缩放级别低时用**聚合**（微信 `markers` 无内置聚类，P4 用 `cover-view` 或按网格合并计数点）；

  * 微信 `<map>` 单帧 marker 上限约 250 个左右时性能最佳，超限先按 "市 / 区统计点" 降级。

* **信息卡**：微信 `<map>` 上叠加 `cover-view` 浮层（现有 Web 是普通 DOM 浮层，不通用，各自实现，但**数据模型来自同一个&#x20;**`buildInfoModel`）。

* **详情跳转**：`wx.navigateTo('/pages/school-detail/index?stage=xx&name=xx')`，参数结构对齐 Web 路由。

### 4.4 包体积与运行时约束



* **当前包体积**：构建产物 `data/` ≈ **3.2MB**、`shared/` ≈ 32KB（2026-09-11 实测）。微信主包上限 2MB / 总包 20MB（含分包）。


  * 结论：**必须引入分包**。建议：`pages/index` + `pages/map` 进主包（核心高频），`school-detail` / `linkage` / `support` / `policy` 进 `subpackages`（按需加载）。

  * 补充：`data/linkage/*`（quota/special/batch2 三个 JSON 约 1.2MB）只有 linkage / 详情页用到，可放分包目录内，不进主包。

* **JS 运行时**：shared 保持 tsc `target` 保守（ES2018 以下，微信基础库 2.x 全支持）；避免在 shared 里用 `?.`、`??` 等新语法（或确认开发者工具 "增强编译" 开启后统一约束，二选一并写进 shared 的贡献规范）。

* **命名约束**：shared 不输出 "中文类名 / WXSS 相关" 内容（小程序 WXSS 类选择器不支持中文，现有 `CONCLUSION_CLASS` 映射保留在页面层）。



***

## 5. 关键决策与风险



| 决策点        | 建议                                                      | 理由                                                  |
| ---------- | ------------------------------------------------------- | --------------------------------------------------- |
| 状态管理       | 纯 TS Store + 各端响应式适配，不引入 Pinia/MobX                     | 小程序无法复用框架层，纯 TS 双端零成本                               |
| 数据共享形态     | loader 注入，shared 不内嵌 JSON                               | 延续 "数据不内嵌" 约定；Web import JSON 与小程序 require CJS 机制不同 |
| 地图渲染       | 两端各自渲染，共享数据模型                                           | Leaflet 与微信 `<map>` API 完全不同，强行抽象渲染层收益低             |
| marker 图标  | 构建脚本按共享颜色常量生成 7 类 PNG                                   | 保证两端配色唯一真源在 shared                                  |
| 分包         | 主包：index/map；分包：detail/linkage/support/policy + 相关 data | 主包 2MB 限制（当前 data 已 3.2MB）                          |
| 重构节奏       | 先下沉 shared + Web 适配零回归，再补小程序                            | 避免 "重构 + 新功能" 同时进行导致的回归面过大                          |
| 风险：Web 回归  | shared 迁移后跑 `npm run check` + 手测地图 / 详情 / 通道三页          | 导出名不变，改动集中在 import 来源                               |
| 风险：小程序地图性能 | 1300+ markers                                           | P1 先做筛选降载，P4 做聚类                                    |



***

## 6. 分期路线



```
P0  共享层重构（预计 1\~2 天）

&#x20;   ├─ packages/shared/src/data/（422 行迁移 + loader 接口）

&#x20;   ├─ packages/shared/src/domain/map|detail|linkage|support

&#x20;   └─ Web 适配：引用改源 + 验证零回归（check + build:web + 手测）

P1  小程序地图补齐（预计 2\~3 天）

&#x20;   ├─ 三学段点位 + 七类配色图标（构建脚本生成）

&#x20;   ├─ 三级筛选 + 搜索 + 信息卡（cover-view 浮层）+ 详情跳转

&#x20;   └─ 分包结构落地（主包 index/map）

P2  小程序学校详情页（预计 1\~2 天）

&#x20;   └─ buildDetailModel 复用 + WXML 渲染

P3  小程序剩余页面（预计 1\~2 天）

&#x20;   ├─ 升学通道（domain/linkage）

&#x20;   ├─ 支撑度完整信号列（domain/support）

&#x20;   └─ 政策说明（静态文案）

P4  体验优化（待评估）

&#x20;   ├─ marker 聚类 / 聚合降级

&#x20;   ├─ 包体积治理（数据裁剪/按需打包）

&#x20;   └─ 搜索增强（拼音/模糊）
```



***

## 7. 复用率量化预估



| 指标                         | 现状                                                  | 重构后                    | 变化           |
| -------------------------- | --------------------------------------------------- | ---------------------- | ------------ |
| 共享代码量（packages/shared/src） | \~525 行                                             | \~1,800–2,000 行        | +3.5x        |
| Web 端不可复用业务逻辑（data + 页面内嵌） | \~1,200 行（data 422 + Map 约 380 + Detail 约 240 + 其余） | 全部下沉，页面仅剩 UI + 渲染      | 100% 迁移      |
| MapView.vue                | 764 行                                               | \~380 行（UI / 渲染为主）     | -50%         |
| SchoolDetailView.vue       | 561 行                                               | \~320 行                | -43%         |
| 小程序页面 JS                   | 无业务层，每功能从零写                                         | 每页仅 View 绑定（60\~120 行） | 业务逻辑 100% 复用 |
| 双端行为一致性                    | 各自实现，易漂移                                            | 同一 repository + domain | 单点维护         |

**结论**：Web 侧重构的核心收益不在 "Web 变短"，而在把～1,200 行业务逻辑变成**双端单点维护**。小程序补齐 5 个功能时，数据层与业务层不再重写，只写 UI 与平台适配。



***

## 8. 决策确认记录（2026-09-11 已拍板）

1. **信息卡交互形态**：✅ 已确认 —— **底部抽屉**（cover-view），**Web 同步改为底部抽屉对齐**，不做右上角浮卡。
2. **小程序首批范围**：✅ 已确认 —— **只做地图页 + 学校详情页**（P0–P2）；升学通道/支撑度/政策页（P3）不进首批。
3. **tabBar 形态**：✅ 已确认 —— **不用 tabBar**，按小程序风格；首页与 tabBar 布局后续统一重构。

> 范围落地：P0 共享层重构 → P1 小程序地图页 → P2 小程序详情页。Web 信息卡随 P0/P1 同步改底部抽屉。