# 共享数据层

多端共用的数据快照（web 应用、微信小程序等均从此目录读取，避免各自维护）。

## 文件

| 文件 | 用途 |
| --- | --- |
| `schools-gz.json` | 原始快照数据，可复核（schools + districts 结构） |
| `schools.js` | 浏览器端直接用 `<script>` 加载（写入 `window.GZ_SCHOOLS`），内容与 JSON 一致 |
| `enrollments/2026-panyu.json` | 番禺区 2026 年小学招生计划与地段数据（官方 xls 解析，试点） |
| `enrollments/2026-panyu.js` | 同上，浏览器端加载（写入 `window.GZ_ENROLL_PANYU`） |

## 数据口径

- **数据源**：高德地图 Web 服务 API（place/text 小学分类 types=141203 + 关键词「小学」补充 + config/district 区边界），2026-09-08 快照
- **范围**：广州市 7 区——荔湾 440103 / 越秀 440104 / 海珠 440105 / 天河 440106 / 白云 440111 / 黄埔 440112 / 番禺 440113
- **采集方式**：分类查询 + 翻页（offset/page），**无单区 100 条上限**（旧版有人为截断，已修复）
- **数量**：共 700+ 所（各区以最终采集结果为准，番禺 179 所，较旧版 97 大幅补全）
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
python3 scripts/fetch_schools.py          # 基础点位，需项目根 .env 中的 AMAP_WEB_KEY
python3 scripts/build_panyu_enrollment.py # 番禺招生数据，解析官方 xls 附件
```

学校是固定长期不变的信息，默认不频繁刷新；确需更新时重跑脚本并提交对应文件。

## 招生数据（enrollments/）

**试点范围**：番禺区 2026 年（官方《招生计划、招生地段及条件》xls 解析）。

- **数据源**：番禺区教育局通知 https://www.panyu.gov.cn/gzpyjy/gkmlpt/content/10/10794/mpost_10794083.html （附件直链 `.../attachment/8/8018/8018386/10794083.xls`）
- **记录**：189 条（公办小学 150 + 民办 39）。字段：`school`（官方名）/ `district`（学区）/ `nature`（公办|民办）/ `plan_classes`（计划班数）/ `plan_count`（民办计划人数）/ `zone`（招生服务地段及条件原文）/ `note` / `school_id`（匹配到点位的基础数据校名）
- **匹配**：94 条已绑定地图点位（`school_id` + 经纬度）；95 条未匹配（官方名单 189 所 > 高德 POI 97 所，点位本身不全，后续补点位）
- **口径说明**：地段文本保留官方原文；公办小学按地段入学（"人户一致"优先，见备注与各学区说明），民办小学无地段、超计划电脑派位
- **每年留存**：地段逐年可能微调，每年追加一个 `enrollments/<year>-<区>.json`，不覆盖旧年份
