# 小学详情页字段盘点（小程序 vs Web，按模块对照）

> 盘点「广州学途」小学详情页各模块字段在**小程序**与**Web 端**的披露情况。
>
> 生成日期：2026-10-14
> 对比基准：
> - 小程序渲染真源：`apps/miniprogram/pages/school-detail/components/school-card/index.wxml` + `index.js`（`buildPrimaryView` / `buildBrandView`）
> - Web 渲染真源：`apps/web/src/pages/SchoolDetailView.vue`（`stage === 'primary'`）
> - 字段规范（双端）：`docs/design/school-search-prd.md`（07 小学详情卡 / 12 学校页）
>
> **数据加载通道说明**：两端底层 JSON 真源一致（`data/` 目录），仅加载通道不同——
> 小程序：`data/*.json` → 构建编译进主包 `apps/miniprogram/utils/data.js`（shared + baseLoaders）→ `app.js onLaunch` 注入 `globalData` → 分包组件运行时读取；集团/升学路线等分包内数据由组件直接 `require` 分包内编译产物。
> Web：`data/*.json` → `scripts/data/compact.mjs` 编译为 `apps/web/src/data/compact/**/*.js` → `data/index.ts` `hydrate` 后注入 `createRepository`。
>
> 下表中「小程序数据真源」「Web 数据真源」列均标注各自通道的编译产物路径；底层 JSON 真源为 `data/` 下同名文件。

---

## 一、基本信息模块

小学态顶部标签（小程序 tags / Web「基本信息」卡片）。小程序无独立基本信息卡片，学段/行政区/性质以顶部 tags 形式存在；**校园荣誉、学校特色为小程序完全缺失的新字段**。

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 学段 | ✅ 是（顶部 tags） | `data/registry/entity/dist/entities.json` → 主包 `utils/data.js` entities | ✅ 是（基本信息卡，`model.stageLabel`） | `compact/registry/entity/dist/entities.js` | 双端均有，等价 |
| 行政区 | ✅ 是（顶部 tags「行政区」） | POI adcode：`data/poi/dist/primary_poi` → 主包 baseLoaders | ✅ 是（基本信息卡，`model.district`） | `compact/poi/dist/primary_poi.js` | 双端均有，等价 |
| 办学性质 | ✅ 是（顶部 tags，缺省「公办」） | `model.nature`（entities / enrollment 推导） | ✅ 是（基本信息卡） | 同上 entities | 双端均有，等价 |
| 教育集团 | ✅ 是（关联校区「所属集团」分组，等价覆盖） | 分包 `data/registry/group/src/brand_groups` + `dist/education_groups` | ✅ 是（基本信息卡「教育集团」行，`brandCard.brand`） | `compact/registry/group/src/brand_groups.js` + `dist/education_groups.js` | 双端均有，小程序在关联校区模块呈现 |
| **校园荣誉（文明校园四档）** | ❌ 否 | 未接入（数据未编译进小程序链路） | ✅ 是（基本信息卡，`civilizedCampusSchoolIds` 按 school_id 命中四档，每档独立一行） | `compact/civilized_campuses/dist/civilized_campus_school_ids.js`（源 `data/civilized_campuses/dist/civilized_campus_school_ids.json`） | **小程序缺失**。四档：全国文明校园（25 校）/ 广东省文明校园（9）/ 广州市文明校园（69）/ 广州市文明校园创建先进学校·储备（62） |
| **学校特色（特色校称号）** | ❌ 否 | 未接入 | ✅ 是（基本信息卡，`specialtySchools` 按 school_id/校名匹配，展开 `recognition` 池：项目名 + 传承/艺术项目 + 官方链接） | `compact/specialty_schools/dist/specialty_schools.js`（源 `data/specialty_schools/dist/specialty_schools.json`） | **小程序缺失**。26 类官方特色校称号、397 校次 |

---

## 二、招生计划模块（2026 年）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 计划班数 `plan_classes` | ✅ 是（模块标题右侧小字「计划 X 个班」，`plan.meta`） | `data/primary/enrollment/dist/2026-all.json` → 主包 `utils/data.js` enrollments | ✅ 是 | `compact/primary/enrollments/2026-all.js` | 双端均有 |
| 招生地段（对口）`zone` | ✅ 是（模块内「招生地段」分组盒正文） | 同上 | ✅ 是 | 同上 | 双端均有 |
| **计划人数 `plan_count`** | ❌ 否 | 同上（数据已在编译产物内，`buildPrimaryView` 未取） | ✅ 是 | 同上 | **小程序缺失**。民办 51 条全部含 `plan_count` |
| **招生说明 `note`** | ❌ 否 | 同上（数据已在编译产物内，未取） | ✅ 是 | 同上 | **小程序缺失**。公办 79 条非空（如「人户一致」特殊条款、「大孩在读可择校」等） |
| 咨询电话 `phone` | ❌ 否 | 同上 | ❌ 否 | 同上 | **双端均未渲染**。公办 361 条非空，数据齐备 |
| 数据来源链接 `source_url` | ❌ 否 | 同上（区级 `districts[*].source_url`） | ❌ 否（招生计划卡不放链接） | 同上 | **双端均未渲染**（仅 Web 品牌关联模块有官方文件链接） |

---

## 三、升学路线参考模块（2026 年）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 招生方式标签 / 序号 `routeGroups[].label` | ✅ 是（每组标题右侧标签：「招生方式一/二…」，对口直升/单校划片/多校电脑派位/电脑派位/电脑抽签/自主招生） | `data/primary/transition/dist/xiaoshengchu_2026.json` → 分包内编译数据（`buildPrimaryView` 组装） | ✅ 是 | `compact/primary/xiaoshengchu_2026.js` | 双端均有 |
| 对口 / 派位初中名单 `routeGroups[].schools[].name` | ✅ 是（分组盒内可点击跳转初中详情） | 同上 | ✅ 是 | 同上 | 双端均有 |
| **派位组名 `feedJuniors.group`** | ❌ 否（仅按机制分块，无组名标题） | 同上（数据已进分包，未取） | ✅ 是（单机制时显示，如「番禺区公办初中第 1 组电脑派位」） | 同上 | **小程序缺失** |
| **直升标注 `direct_feed`** | ⚠️ 部分（对口直升校出现在名单中，但无「直升：X」明确标注） | 同上 | ✅ 是 | 同上 | 小程序可视为等价覆盖，无显式标注 |
| 升学路线备注（`feedGap` / `source_note`） | ⚠️ 仅数据缺口时兜底显示（`primary.routes.note`，绝大多数学校为空不出现） | 同上 | ✅ 是 | 同上 | 用户已明确**不需要展示、不需要改**，不计入待补字段 |
| 派位组官方来源链接 `groups[].source_urls` | ❌ 否 | 同上 | ❌ 否 | 同上 | **双端均未渲染**链接本体（Web 仅露 `source_note` 文案） |

---

## 四、品牌关联 / 关联校区模块

各学段共用（小程序 `buildBrandView`，置卡片末尾；Web `brandCard`）。

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 品牌 / 教育集团名 | ✅ 是（「所属集团」分组标题） | 分包 `data/registry/group/src/brand_groups` + `dist/education_groups` | ✅ 是 | `compact/registry/group/src/brand_groups.js` + `dist/education_groups.js` | 双端均有 |
| 集团核心校 / 成员校列表 | ✅ 是（「集团核心校」「集团成员校」分组；当前校排首位） | 同上 | ✅ 是 | 同上 | 双端均有 |
| **集团说明 + 官方文件链接** | ❌ 否（只列集团名/核心/成员） | 同上（数据已进分包，未取） | ✅ 是（`brandCard.note` + `brandCard.sourceUrls`「[官方文件]」链接） | 同上 | **小程序缺失** |
| **关系类型标签**（托管办学 / 合作办学 / 品牌合作） | ❌ 否（仅「核心校/成员校」两类） | 同上（education_groups 有 `relationType`，未取） | ✅ 是（`brandCard.groups[].rows[].relationType`） | `compact/registry/group/dist/education_groups.js` | **小程序缺失**。注意：`education_groups` member 无 legal 字段，法人维度仅 `brand_groups` 有 |
| 多校区列表（无集团时） | ⚠️ 部分（`brand.multi`「多校区」分组已覆盖同法人多校区，含学段标签+当前标记） | 分包 `data/registry/group/dist/non_group_multi_campuses` + entities 推导 | ✅ 是（`campuses` 同法人推导，标「校区」） | `compact/registry/group/dist/non_group_multi_campuses.js` | 小程序 multi 已覆盖主要场景，无集团时纯校区列表逻辑略不同 |

---

## 五、其他字段（模型/数据存在，双端均未在详情页渲染）

| 字段名 | 小程序是否展示（渲染位置） | 小程序数据真源 | Web 是否展示 | Web 数据真源 | 备注 |
|---|---|---|---|---|---|
| 学校别名 `aliases` | ❌ 否 | `data/registry/entity/dist/entities.json` → 主包 entities | ❌ 否（仅用于检索匹配 `resolveSchoolIdOf`） | `compact/registry/entity/dist/entities.js` | 仅检索用途，非展示字段 |
| 徽章 `badges` | ❌ 否（模型已算、小学态未用） | `repo.schoolBadges`（主包 shared） | ❌ 否（小学态未用） | 同上 shared | 内容（区/性质）与 tags 重复，属冗余 |
| 学校信号（学位预警 / 省一级 / 多维印证） | ❌ 否 | 未接入 | ❌ 否 | `data/reputation/primary/tier1_schools_all.json` | **已废弃**：PRD 07 注明 2026-09-30 废弃归档；该小学文件现仅含元信息，无学校记录，属遗留数据 |

---

## 六、汇总：小程序缺失字段清单（按模块）

| 模块 | 缺失字段 | 数据齐备度 |
|---|---|---|
| 基本信息 | 校园荣誉（文明校园四档） | 完整（165 个 school_id） |
| 基本信息 | 学校特色（特色校称号） | 完整（26 类 / 397 校次） |
| 招生计划 | 计划人数 `plan_count` | 民办 51 条全有 |
| 招生计划 | 招生说明 `note` | 公办 79 条非空 |
| 升学路线 | 派位组名 `group` | 已进分包，直接可取 |
| 品牌关联 | 集团说明 + 官方文件链接 | 已进分包，直接可取 |
| 品牌关联 | 关系类型标签（托管/合作/品牌合作） | education_groups 已含 |

双端均未渲染（数据存在但无端展示）：咨询电话 `phone`（361 条）、招生计划/升学路线的来源链接 `source_url`、学校别名 `aliases`、学校信号 tier1（已废弃）。

明确不做：升学路线备注（用户确认不需要展示、不需要改）。
