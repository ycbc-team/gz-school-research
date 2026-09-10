# 共享数据层

多端共用的数据快照（web 应用、微信小程序等均从此目录读取，避免各自维护）。

## 数据治理约定（重要）

- **本目录只存放 JSON，是唯一数据真源（source of truth）。** 任何端（Web / 小程序）
  都应消费这里的 JSON，不在应用内复制或二次维护数据。
- 历史教训：js/json 双份曾出现脱同步（如小学点位 js 为清洗后 915 所、json 仍为 971 所），
  已回填对齐并彻底移除 js 兼容产物；今后只改 JSON，Web / 小程序构建时按需生成产物。

按学段分子目录，小学与初中数据互不干扰：

| 目录 | 学段 | 主要文件 |
| --- | --- | --- |
| `primary/` | 小学 | `schools-gz.json`（931 所点位）、`tier1_schools_all.json`（第一梯队核验）、`enrollments/`（2026 招生数据） |
| `middle/` | 初中 | `schools-gz.json`（7 区初中点位，475 所）、`tier1_schools_all.json`（初中第一梯队核验） |
| `high/` | 高中 | `schools-gz.json`（清洗后 126 所点位）、`levels.json`（学校清单/分类/指标） |
| `registry/` | 跨学段 | `education_groups_2026.json`（招考办 2026 集团名额分配表，43 核心校/118 成员）、`brand_groups.json`（8 品牌组成员清单，含法人关系/来源 URL）、`sites.json` |

## 坐标系

所有点位均为 **GCJ-02**（高德坐标系），与高德地图瓦片一致，无需转换；微信小程序内置
`<map>` 组件同样使用 GCJ-02，可直接使用。

## 数据源

高德地图 Web 服务 API（place/text 分类查询 + 翻页采集 + config/district 区边界），快照日期见各文件 `updated` 字段。

## 更新方式

```bash
# 小学
python3 scripts/primary/fetch_schools.py          # 小学点位采集（写 data/primary/schools-gz.json）
python3 scripts/primary/backfill_schools.py       # 番禺招生未匹配点位回填（写 json 真源 + 留痕）

# 初中
python3 scripts/middle/fetch_middle_schools.py   # 初中点位采集（写 data/middle/schools-gz.json）

# 高中
python3 scripts/high/fetch_high_schools.py     # 高中原始采集
python3 scripts/high/build_high_levels_js.py   # 高中清洗点位（写回 data/high/schools-gz.json 真源）

# 招生
python3 scripts/primary/build_district_enrollment.py   # 2026 招生（写 data/primary/enrollments/*.json 真源）
```

密钥仅存于项目根 `.env`（`AMAP_WEB_KEY`），代码与页面不出现明文凭据。

## 新校核对流程（2026-09-10 起强制）

新开办学校的完整性校验**不能只依赖高德分类抓取快照**（新校高德收录滞后、九年制/完全中学分类不稳定会导致 POI 层漏抓），必须按以下流程核对并补录：

1. **强制校验源（每年开学季先取这两个基准）**
   - 广州市政府门户年度新开办中小学校清单（如 2026-08-27《广州9月新开办中小学校(校区)24所》https://www.gz.gov.cn/zwfw/zxfw/jyfw7/content/post_10979972.html ）
   - 各区教育局/区政府新校批复与发布（如番禺区政府 https://www.panyu.gov.cn/zwgk/zfxxgkml/xxgkml/zwdt/fzxw/content/post_10250808.html ）；批复链接失效时以权威媒体转引作来源
   - 补充：南方+/广州日报/信息时报/新快报等开学季"上新"盘点
2. **逐校核对**：新校名 → 开学年份 → 学段（小学/初中/九年制/完全中学）→ 在 `primary/`、`middle/` POI 层的覆盖状态；九年制/十二年制学校按实际开办学段补入对应层（未开办学段不补，如华中师大白云学校初中部 2027 才开，2026 只补小学层）
3. **坐标与事实必须有来源**：坐标一律取高德 Web 服务 API（place/text 或 geocode/geo，GCJ-02），禁止编造；道路级/配建地块级/兴趣点级精度差异在清单中注明；高德未收录的新校不强行补点，标注"待高德收录"
4. **补录口径**：补录点位写入 `schools-gz.json` 的 `schools[]`，条目加 `note: "新开办（年份）·待首届成绩"`（无成绩新校不入口碑名单，`tier1_eligible` 判定不动）
5. **留痕**：每轮核对产出 7 区清单（见 `docs/new-school-checklists/`），记录官方来源 URL/开学年份/学段/POI 状态/是否补录/品牌归属/待成绩标记

## 教育集团 Registry（registry/）

跨学段的教育集团名录与品牌组成员清单，供详情页「品牌关联」板块与覆盖核对使用。

### `education_groups_2026.json`
- 来源：广州市招考办《2026年广州市成立教育集团的示范性普通高中面向集团的直接名额分配情况》（2026-05-12，http://gzzk.gz.gov.cn/gkmlpt/content/10/10809/post_10809470.html ）
- 内容：43 个集团核心校（省市属 7 + 区属 36）、118 条集团内初中成员关系
- 局限：仅含「示范性高中 + 集团内初中」口径；小学段成员与区属非示范集团不在表内

### `brand_groups.json`
- 用途：详情页「品牌关联」板块数据源，列出 8 个重点品牌组（清华附中湾区/广铁一中/省实/广雅/执信/二中/广大附/华附）的校区与独立法人成员校
- 字段：`units[].name`（规范校名）、`role`（角色说明）、`legal`（same=同法人 / independent=独立法人 / entrusted=托管共建）、`poi_names`（POI 名别名，用于全等匹配）、`source_url`（官方来源 URL）
- P2 核实（2026-09-10）：8 品牌组经官网/招考办/区政府文件/主流媒体交叉核实，新增 25 个成员单位，全部附来源 URL + 法人关系标注

### 教育集团齐全化任务状态
- **P0（已完成）**：招考办 2026 表落盘 `education_groups_2026.json`
- **P1（已完成）**：161 校覆盖比对，产出 `docs/education-groups-coverage/集团成员覆盖清单_P1.md`（精确命中 49 / 变体命中 45 / 7 区内真实缺失 2 / 远郊不在范围 65）
- **P2（已完成）**：8 品牌组官方来源交叉核实，写回 `brand_groups.json`（新增 25 成员，单测 12/12 通过）
- **P3（未完成）**：区属非示范集团 + 小学集团全量按各区文件补录
- **P4（未完成）**：年度更新机制（每年 5 月招考办新表发布后刷新）
