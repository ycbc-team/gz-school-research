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
