# 共享数据层

多端共用的数据快照（web 应用、微信小程序等均从此目录读取，避免各自维护）。

按学段分子目录，小学与初中数据互不干扰：

| 目录 | 学段 | 主要文件 |
| --- | --- | --- |
| `primary/` | 小学 | `schools.js`（915 所点位）、`tier1.js`（第一梯队核验）、`enrollments/`（2026 招生数据） |
| `middle/` | 初中 | `schools.js`（8 区初中点位）、`tier1.js`（初中第一梯队核验） |

## 坐标系

所有点位均为 **GCJ-02**（高德坐标系），与高德地图瓦片一致，无需转换。

## 数据源

高德地图 Web 服务 API（place/text 分类查询 + 翻页采集 + config/district 区边界），快照日期见各文件 `updated` 字段。

## 更新方式

```bash
# 小学
python3 scripts/fetch_schools.py          # 小学点位（输出 data/primary/）
python3 scripts/build_tier1_js.py         # 小学梯队数据

# 初中
python3 scripts/fetch_middle_schools.py   # 初中点位（输出 data/middle/）
python3 scripts/build_middle_tier1_js.py  # 初中梯队数据
```

密钥仅存于项目根 `.env`（`AMAP_WEB_KEY`），代码与页面不出现明文凭据。
