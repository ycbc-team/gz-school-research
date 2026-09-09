# 共享数据层

多端共用的数据快照（web 应用、微信小程序等均从此目录读取，避免各自维护）。

## 数据治理约定（重要）

- **本目录只存放 JSON，是唯一数据真源（source of truth）。** 任何端（Web / 小程序）
  都应消费这里的 JSON，不在应用内复制或二次维护数据。
- 旧版浏览器兼容产物（`window.GZ_*` 的 `.js` 文件）已从本目录迁出，统一放
  `apps/web/legacy/_generated/`，仅供旧页面（file:// 直接打开）使用，由
  `scripts/` 下的脚本从 JSON 生成，**勿手改**；Vue3 重构完成后随旧页面一并下线。
- 历史教训：js/json 双份曾出现脱同步（如小学点位 js 为清洗后 915 所、json 仍为 971 所），
  已回填对齐；今后只改 JSON，需要 js 产物时运行对应生成脚本。

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
python3 scripts/fetch_schools.py          # 小学点位（输出 data/primary/ + legacy js 产物）
python3 scripts/build_tier1_js.py         # 小学梯队数据（json -> legacy js 产物）
python3 scripts/backfill_schools.py       # 番禺招生未匹配点位回填（写 json 真源 + legacy js 产物）

# 初中
python3 scripts/fetch_middle_schools.py   # 初中点位
python3 scripts/build_middle_tier1_js.py  # 初中梯队数据

# 高中
python3 scripts/fetch_high_schools.py     # 高中原始采集
python3 scripts/build_high_levels_js.py   # 高中清洗点位（写回 data/high/schools-gz.json 真源 + legacy js）

# 旧地图页单文件产物（消费 legacy/_generated/ 下全部 js）
python3 scripts/build_combined_data.py    # -> apps/web/legacy/_generated/combined.js

# 招生
python3 scripts/build_district_enrollment.py   # 2026 招生（json 真源 + legacy js 产物）
```

密钥仅存于项目根 `.env`（`AMAP_WEB_KEY`），代码与页面不出现明文凭据。
