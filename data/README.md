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
| `primary/` | 小学 | `schools-gz.json`（915 所点位）、`tier1_schools_all.json`（第一梯队核验）、`enrollments/`（2026 招生数据） |
| `middle/` | 初中 | `schools-gz.json`（8 区初中点位）、`tier1_schools_all.json`（初中第一梯队核验） |
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
