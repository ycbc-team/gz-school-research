# 初中阶段数据

广州 8 区初中学校点位与梯队核验数据。

## 范围

8 区：荔湾 440103 / 越秀 440104 / 海珠 440105 / 天河 440106 / 白云 440111 / 黄埔 440112 / 番禺 440113 / 增城 440118

排除远郊：南沙 440115 / 花都 440114 / 从化 440117

## 文件

| 文件 | 用途 |
| --- | --- |
| `schools-gz.json` | 原始快照数据，可复核（schools + districts 结构） |
| `schools.js` | 浏览器端直接用 `<script>` 加载（写入 `window.GZ_MIDDLE_SCHOOLS`） |
| `tier1_schools_all.json` | 第一梯队核验源数据（名单 + 网传来源 + 客观数据 + 判定） |
| `tier1.js` | 浏览器端加载（写入 `window.GZ_MIDDLE_TIER1`），由 build_middle_tier1_js.py 生成 |

## 数据口径

- **数据源**：高德地图 Web 服务 API（place/text 初中分类 types=141201 + 关键词「初中」补充 + config/district 区边界）
- **采集方式**：分类查询 + 翻页（offset/page），无单区 100 条上限
- **保留范围**：初中 + 完全中学（初高中一体），剔除纯高中、培训机构、辅导托管类 POI
- **坐标系**：GCJ-02（与高德地图瓦片一致）

## 结构

```jsonc
{
  "updated": "2026-09-09",
  "source": "高德地图 Web 服务 API",
  "schools": [
    { "name": "校名", "lng": 113.xxx, "lat": 23.xxx, "adcode": "440103" }
  ],
  "districts": [
    { "name": "荔湾区", "adcode": "440103", "boundary": [ [[lng, lat], ...] ] }
  ]
}
```

## 更新方式

```bash
python3 scripts/fetch_middle_schools.py    # 初中点位采集
python3 scripts/build_middle_tier1_js.py   # 梯队数据构建
```
