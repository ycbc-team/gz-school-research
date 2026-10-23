# 学校详情页字段盘点（小学 / 初中 / 高中，小程序 vs Web）

> 盘点「广州学途」三学段学校详情页各模块字段在**小程序**与**Web 端**的披露情况。
>
> 生成日期：2026-10-21
> 对比基准：
> - 小程序渲染真源：`apps/miniprogram/pages/school-detail/components/school-card/index.wxml` + `index.js`（`buildPrimaryView` / `buildMiddleView` / `buildHighView` / `buildBrandView`）
> - Web 渲染真源：`apps/web/src/pages/SchoolDetailView.vue` + `apps/web/src/components/LinkagePanel.vue`
> - 数据模型：`packages/shared/src/domain/detail/model.ts` 的 `buildDetailModel` / `buildLinkageModel`（**两端共用同一模型**，差异仅在各自渲染选取的字段）
> - 字段规范（双端）：`docs/design/school-search-prd.md`
>
> **数据加载通道**：
> - 小程序：底层 `data/*.json` → 构建编译进主包 `apps/miniprogram/utils/data.js`（shared + baseLoaders）→ `app.js` 注入 `globalData`；集团/升学/名额等分包内数据由 `school-card` 组件直接 `require` 分包内编译产物；**awards / 文明校园 / 特色校未接入小程序**。
> - Web：`data/*.json` → `scripts/data/compact.mjs` 编译为 `apps/web/src/data/compact/**/*.js` → `data/index.ts` `hydrate` 后注入 `createRepository`，页面直接消费 `model.*`。
>
> 下表「小程序数据真源」「Web 数据真源」列标注各自通道的编译产物路径；两端底层 JSON 真源一致（除 awards/文明校园/特色校小程序完全未接入）。
>
> 表头：**字段名 ｜ 小程序是否展示（是→附渲染位置）｜ 小程序数据真源 ｜ Web 是否展示 ｜ Web 数据真源 ｜ 备注**

---

## 一、小学（07）

### 模块：基本信息（小程序顶部 tags ／ Web「基本信息」卡片）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 学段 | ✅ 是（顶部 tags） | `data/registry/entity/dist/entities.json`（主包 baseLoaders） | ✅ 是（基本信息卡 `stageLabel`） | `compact/registry/entity/dist/entities.js` | 双端均有 |
| 行政区 | ✅ 是（tags「行政区」） | POI `data/poi/dist/primary_poi` + entities | ✅ 是（基本信息卡「所属区」） | `compact/poi/dist/primary_poi.js` + `entities.js` | 双端均有 |
| 办学性质 | ✅ 是（tags，缺省「公办」） | `model.nature`（enrollment / entities 推导） | ✅ 是（头部 `badges` 含性质） | `entities.js`（shared `schoolBadges`） | 双端均有 |
| 教育集团 | ✅ 是（关联校区「所属集团」分组） | 分包 `data/registry/group/src/brand_groups` + `dist/education_groups` | ✅ 是（基本信息卡「教育集团」） | `compact/registry/group/src/brand_groups.js` + `dist/education_groups.js` | 双端均有 |
| **校园荣誉（文明校园四档）** | ❌ 否 | 未接入 | ✅ 是（基本信息卡 `civilizedCampusHonors`，按 school_id 命中四档，每档独立一行） | `compact/civilized_campuses/dist/civilized_campus_school_ids.js`（源 `data/civilized_campuses/dist/civilized_campus_school_ids.json`） | **小程序缺失**。四档：全国文明校园（25）/ 广东省文明校园（9）/ 广州市文明校园（69）/ 广州市文明校园创建先进学校·储备（62） |
| **学校特色（特色校称号）** | ❌ 否 | 未接入 | ✅ 是（基本信息卡 `specialtyRows`，展开 `recognition` 池：项目名 + 传承/艺术项目 + 官方链接） | `compact/specialty_schools/dist/specialty_schools.js`（源 `data/specialty_schools/dist/specialty_schools.json`） | **小程序缺失**。26 类官方特色校称号、397 校次 |

### 模块：招生计划（2026 年）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 计划班数 `plan_classes` | ✅ 是（模块标题右侧「计划 X 个班」） | `data/primary/enrollment/dist/2026-all.json` | ✅ 是 | `compact/primary/enrollments/2026-all.js` | 双端均有 |
| **计划人数 `plan_count`** | ❌ 否（数据已编译未取） | 同上 | ✅ 是（「计划人数」） | 同上 | **小程序缺失**。民办 51 条全部含 `plan_count` |
| 招生地段（对口）`zone` | ✅ 是（「招生地段」分组盒） | 同上 | ✅ 是 | 同上 | 双端均有 |
| **招生说明 `note`** | ❌ 否（数据已编译未取） | 同上 | ✅ 是（「招生说明」） | 同上 | **小程序缺失**。公办 79 条非空 |

### 模块：升学路线参考（2026 年）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 招生方式标签 `routeGroups[].label` | ✅ 是（机制标签） | `data/primary/transition/dist/xiaoshengchu_2026.json` | ✅ 是 | `compact/primary/xiaoshengchu_2026.js` | 双端均有 |
| 对口 / 派位初中名单 `routeGroups[].schools[].name` | ✅ 是（可跳转初中详情） | 同上 | ✅ 是 | 同上 | 双端均有 |
| **派位组名 `feedJuniors.group`** | ❌ 否（仅按机制分块，无组名标题） | 同上（已编译未取） | ✅ 是（单机制时显示，如「番禺区公办初中第 1 组电脑派位」） | 同上 | **小程序缺失** |
| 直升标注 `direct_feed` | ⚠️ 部分（对口直升校出现在名单中，但无「直升」明确标注） | 同上 | ✅ 是（缺口块「直升：X」） | 同上 | 小程序无显式标注 |
| 升学路线备注（`feedGap` / `source_note`） | ⚠️ 仅数据缺口时兜底显示（绝大多数学校为空不出现） | 同上 | ✅ 是 | 同上 | 用户已明确**不需要展示、不需要改**，不计入待补字段 |

### 模块：竞赛获奖（三学段 Web 均有，小程序全无）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 创新大赛 / 创客电视 / 科学素养 / 科技体育 / 科学实验 / 粤韵杯 获奖（按学段×年份 金/银/铜） | ❌ 否 | 未接入（`school-card` 未 require awards 数据） | ✅ 是（「竞赛获奖」卡片，分赛事跳转 `/awards`） | `compact/awards/{innovation,chuangke,science_literacy,tech_sports,science_experiment,yueyunbei}/*.js`（源 `data/awards/*`） | **小程序完全缺失（小学/初中/高中三学段均无此模块）** |

### 模块：品牌关联 / 关联校区

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 集团名 / 核心校 / 成员校 | ✅ 是（关联校区「所属集团 / 集团核心校 / 集团成员校」） | 分包 `data/registry/group/src/brand_groups` + `dist/education_groups` | ✅ 是（品牌关联「品牌 · X」+ 分组行） | `compact/registry/group/src/brand_groups.js` + `dist/education_groups.js` | 双端均有 |
| **集团说明 + 官方文件链接** `brandCard.note` + `sourceUrls` | ❌ 否（只列集团名/核心/成员） | 同上（已编译未取） | ✅ 是（`brand-note` + 「[官方文件]」链接） | 同上 | **小程序缺失** |
| **关系类型标签** `relationType`（托管/合作/品牌合作） | ❌ 否（仅「核心校/成员校」两类） | 同上（education_groups 有，未取） | ✅ 是（行内标签） | `compact/registry/group/dist/education_groups.js` | **小程序缺失** |
| 成员行明细（区 / 徽章 / 说明）`district` / `badge` / `reason` | ⚠️ 部分（小程序仅 name + 学段 badge + 当前查看） | 同上 | ✅ 是（行内区徽章 + 关系徽章 + `brand-reason`） | 同上 | **小程序缺失明细** |
| 多校区列表（无集团时） | ⚠️ 部分（`brand.multi` 已覆盖同法人多校区，含学段标签+当前标记） | 分包 `data/registry/group/dist/non_group_multi_campuses` + entities | ✅ 是（`campuses` 列表，标「校区」） | `compact/registry/group/dist/non_group_multi_campuses.js` | 小程序 multi 已覆盖主要场景 |

### 模块：其他（数据存在，双端均未在详情页渲染）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 学校别名 `aliases` | ❌ 否 | `data/registry/entity/dist/entities.json` | ❌ 否（仅检索匹配 `resolveSchoolIdOf`） | `compact/registry/entity/dist/entities.js` | 仅检索用途 |
| 徽章 `badges`（区/性质/学段 badge 对象） | ❌ 否（小程序用固定 tags，未用 badge 对象） | shared `schoolBadges` | ✅ 是（头部 `badges` 渲染区/性质等） | shared `schoolBadges` | 小程序以 tags 等价覆盖区/性质/学段 |
| 学校信号（学位预警/省一级/多维印证） | ❌ 否 | 未接入 | ❌ 否 | `data/reputation/primary/tier1_schools_all.json` | **已废弃**：PRD 07 注明 2026-09-30 废弃归档；小学文件仅含元信息无记录 |

---

## 二、初中（07B）

### 模块：基本信息（同小学：学段/行政区/性质/教育集团 双端均有；校园荣誉/学校特色 小程序缺失，详见小学模块表）

### 模块：招生计划（2026 年）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 总班数 `totalPlan` / `planMeta` | ✅ 是（模块标题右侧「计划 X 个班」） | `data/middle/enrollment/dist/middle_enrollment_2026.json`（经 `middleEnrollmentsOf` 聚合） | ✅ 是 | `compact/middle/enrollment/dist/middle_enrollment_2026.js` | 双端均有 |
| 招生方式（按机制聚合）`byMech` / `mechanismBlocks` | ✅ 是（机制标签 + 「招生方式一/二」） | 同上 | ✅ 是 | 同上 | 双端均有 |
| 服务范围 `scope` | ✅ 是（「服务范围」分组） | 同上 | ✅ 是 | 同上 | 双端均有 |
| 生源小学（按派位组 `group_id` 分组）`groups[].name` + `schools` | ✅ 是（派位组名 `grp-l` + 小学名单，可跳转） | 同上 + `groups` 派位组表 | ✅ 是 | 同上 | 双端均有；**小程序已显示派位组名** |
| **招生说明（按机制/派位组）`notes`** | ❌ 否 | 同上（已编译未取） | ✅ 是（每个派位组子块「招生说明」，番禺「见说明N」平铺） | 同上 | **小程序缺失** |
| **摇号 / 未中签提示 `loseText`** | ❌ 否 | 同上（已编译未取） | ✅ 是（`lottery-warning` ⚠️） | 同上 | **小程序缺失** |
| 空状态说明 `enrollNote` | ✅ 是（无计划时兜底文案） | `model.enrollNote` | ✅ 是 | 同上 | 双端均有 |

### 模块：升学通道 / 中考报考情况（名额分配 + 自招 + 录取分数）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 名额考生数 `kaosheng` | ✅ 是（中考报考情况·名额考生数） | `data/linkage/{quota_matrix,district_quota}.json`（分包） | ✅ 是（中考-第二批·名额考生数） | `compact/linkage/{quota_matrix,district_quota}.js` | 双端均有 |
| 省市属名额合计 `sheng_quota` | ✅ 是（省市属高中录取名额） | 同上 | ✅ 是（省市属名额合计） | 同上 | 双端均有 |
| 区属名额合计 `qu_quota` | ✅ 是（区属高中录取名额） | 同上 | ✅ 是（区属名额合计） | 同上 | 双端均有 |
| 共享计划校区 `campuses` | ✅ 是（「与其他初中共享计划的校区」） | 同上 | ✅ 是（「该初中校区」表） | 同上 | 双端均有 |
| 省市属高中录取明细（高中 / 名额 / 录取最低分）`batchMerged` | ✅ 是（省市属高中录取明细表） | 同上 | ✅ 是（省市属高中表） | 同上 | 双端均有 |
| 区属高中录取明细（高中 / 名额 / 录取最低分）`districtRows` | ✅ 是（区属高中录取明细表） | 同上 | ✅ 是（区属高中表） | 同上 | 双端均有 |
| 区属名额未收录逐校明细说明 | ❌ 否（小程序无此分支，仅有 districtRows 或空） | — | ✅ 是（`qu_quota` 有但逐校未收录提示） | `data/linkage/district_quota.json` | 小程序缺失该提示文案（数据等价） |
| 第三/四批不展示说明 | ✅ 是（dnote「第三批第四批无法获取」） | linkage model | ✅ 是（sub-note） | linkage model | 双端均有 |

### 模块：竞赛获奖（同小学：小程序完全缺失，Web 三学段均有，详见小学模块表）

### 模块：品牌关联 / 关联校区（同小学：集团名/核心/成员 双端均有；note/sourceUrls/relationType/明细 小程序缺失）

### 模块：其他（同小学：别名 双端仅检索；徽章；tier1 已废弃）

---

## 三、高中（07E）

### 模块：基本信息（同小学：学段/行政区/性质/教育集团 双端均有；校园荣誉/学校特色 小程序缺失）

### 模块：高考信息

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 高分段 2026 / 2025 `gaofen_*` | ✅ 是（高考信息·`label/value`） | `data/registry/entity/dist/entities.json` 的 `rec.indicators` | ✅ 是 | `compact/registry/entity/dist/entities.js` | 双端均有 |
| 特控线上线率 2026 / 2025 `tekong_*` | ✅ 是 | 同上 | ✅ 是 | 同上 | 双端均有 |
| 备注 `note` | ✅ 是 | 同上 | ✅ 是 | 同上 | 双端均有 |
| 数据来源标注（喜报/网传口径） | ✅ 是（模块 meta「信息来源各校喜报或网传，仅供参考」） | — | ✅ 是（sub-note） | — | 双端均有 |

### 模块：招生计划（录取分数线）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 录取分数线（2025/2026，户籍生/非户籍生/外区等，按校区）`admissionRows` | ✅ 是（招生计划·`label/value`） | `data/high/cutoff_score/dist/{scores_2025,scores_2026}.json`（`scoresOfSchool`） | ✅ 是 | `compact/high/cutoff_score/dist/{scores_2025,scores_2026}.js` | 双端均有 |

### 模块：第一批招生（2026，自招 / 体育 / 艺术特长）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 自主招生计划 `autonomyPlan` | ✅ 是（第一批招生·自主招生） | `buildLinkageModel`（高中） | ✅ 是 | `compact/linkage/*`（经 `buildLinkageModel`） | 双端均有 |
| 体育特长生计划 `sportsPlan` | ✅ 是 | 同上 | ✅ 是 | 同上 | 双端均有 |
| 体育项目明细 `sportsProjects` | ✅ 是（缩进子行·项目/人） | 同上 | ✅ 是 | 同上 | 双端均有 |
| 艺术特长生计划 `artsPlan` | ✅ 是 | 同上 | ✅ 是 | 同上 | 双端均有 |
| 艺术项目明细 `artsProjects` | ✅ 是 | 同上 | ✅ 是 | 同上 | 双端均有 |
| 计划备注 `planNotes`（reserve/lingjun） | ✅ 是（dnote：后备人才/领军龙） | 同上 | ✅ 是（plan-note） | 同上 | 双端均有 |
| 特殊通道说明文案 | ✅ 是（dnote「自主招生/体育/艺术…不分配到校」） | — | ✅ 是（sub-note） | — | 双端均有 |

### 模块：第二批招生（2026，名额分配覆盖）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 省市属高中（面向全市）覆盖初中（初中 / 所在区 / 名额）`highCoverage` | ✅ 是（省市属高中（面向全市）覆盖初中表） | `buildLinkageModel`（高中） | ✅ 是 | `compact/linkage/*` | 双端均有 |
| 区属高中（面向本区）覆盖初中（初中 / 名额）`highDistrictCoverage` | ✅ 是（区属高中（面向本区）覆盖初中表） | 同上 | ✅ 是 | 同上 | 双端均有 |
| 多校区选校区（法人同名多校区）`campuses` | ✅ 是（初中名 → 校区 to 跳转） | 同上 | ✅ 是（picker 弹窗选校区） | 同上 | 双端均有 |

### 模块：竞赛获奖（同小学：小程序完全缺失，Web 三学段均有；高中含中学组 + 测向18岁合并）

### 模块：品牌关联 / 关联校区（同小学：集团名/核心/成员 双端均有；note/sourceUrls/relationType/明细 小程序缺失）

### 模块：其他（数据存在，双端均未单独渲染）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 办学等级（国家级示范/省一级/市一级等） | ❌ 否（仅 headText 含隶属，未单列等级） | `data/high/level/src/levels.json`（模型仅用于校名匹配，未展示） | ❌ 否（同） | `compact/high/level/src/levels.js` | 双端均未单独渲染等级字段 |
| 学校别名 `aliases` | ❌ 否 | `data/registry/entity/dist/entities.json` | ❌ 否（仅检索） | `compact/registry/entity/dist/entities.js` | 仅检索 |
| 徽章 `badges` | ❌ 否（固定 tags） | shared `schoolBadges` | ✅ 是（头部） | shared `schoolBadges` | 小程序以 tags 等价覆盖 |
| 学校信号 tier1 | ❌ 否 | 未接入 | ❌ 否 | `data/reputation/high/*`（如有） | 已废弃口径 |

---

## 四、小程序缺失字段汇总（三学段）

| 模块 | 缺失字段 | 影响学段 | 数据齐备度 |
|---|---|---|---|
| 基本信息 | 校园荣誉（文明校园四档） | 小/初/高 | 完整（165 个 school_id） |
| 基本信息 | 学校特色（特色校称号） | 小/初/高 | 完整（26 类 / 397 校次） |
| 招生计划 | 计划人数 `plan_count` | 小学 | 民办 51 条全有 |
| 招生计划 | 招生说明 `note` | 小学 | 公办 79 条非空 |
| 招生计划 | 招生说明（按机制/派位组）`notes` | 初中 | 数据已在编译产物 |
| 招生计划 | 摇号 / 未中签提示 `loseText` | 初中 | 数据已在编译产物 |
| 升学路线 | 派位组名 `feedJuniors.group` | 小学 | 数据已在编译产物（初中已显示） |
| 升学通道 | 区属名额未收录逐校明细提示 | 初中 | 文案级 |
| 竞赛获奖 | 6 项赛事获奖（创新/创客/科学素养/科技体育/科学实验/粤韵杯） | 小/初/高 | 完整（data/awards/*） |
| 品牌关联 | 集团说明 + 官方文件链接 `note`/`sourceUrls` | 小/初/高 | 已编译未取 |
| 品牌关联 | 关系类型标签（托管/合作/品牌合作）`relationType` | 小/初/高 | education_groups 已含 |
| 品牌关联 | 成员行明细（区/徽章/说明）`district`/`badge`/`reason` | 小/初/高 | 已编译未取 |

三学段**双端均未渲染**：办学等级（high）、别名（仅检索）、徽章对象（小程序以 tags 覆盖）、学校信号 tier1（已废弃）。

**明确不做**：升学路线备注（`feedGap` / `source_note`）—— 用户确认不需要展示、不需要改（仅小学该字段，初/高无同类）。
