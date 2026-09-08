# 共享数据层

多端共用的数据快照（web 应用、微信小程序等均从此目录读取，避免各自维护）。

## 文件

| 文件 | 用途 |
| --- | --- |
| `schools-gz.json` | 原始快照数据，可复核（schools + districts 结构） |
| `schools.js` | 浏览器端直接用 `<script>` 加载（写入 `window.GZ_SCHOOLS`），内容与 JSON 一致 |

## 数据口径

- **数据源**：高德地图 Web 服务 API（place/text 检索「小学」POI + config/district 区边界），2026-09-08 快照
- **范围**：广州市 7 区——荔湾 440103 / 越秀 440104 / 海珠 440105 / 天河 440106 / 白云 440111 / 黄埔 440112 / 番禺 440113
- **数量**：共 619 所（荔湾 72 / 越秀 73 / 海珠 96 / 天河 93 / 白云 100 / 黄埔 88 / 番禺 97）
- **限制**：高德单区单次检索上限 100 条，白云区恰为 100 所，可能未覆盖全部
- **坐标系**：GCJ-02（与高德地图瓦片一致）

## 结构

```jsonc
{
  "updated": "2026-09-08",
  "source": "amap-webapi",
  "adcodes": { "荔湾区": "440103", ... },
  "schools": [
    { "name": "校名", "lng": 113.xxx, "lat": 23.xxx, "adcode": "440103" }
  ],
  "districts": [
    { "adcode": "440103", "boundary": [ [[lng, lat], ...] ] }
  ]
}
```

## 更新方式

```bash
python3 scripts/fetch_schools.py   # 需项目根 .env 中的 AMAP_WEB_KEY
```

学校是固定长期不变的信息，默认不频繁刷新；确需更新时重跑脚本并提交两个文件。
