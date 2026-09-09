# Web 应用

广州学校升学调研的 web 端应用。

## 结构

```
apps/web/
├── index.html          # 应用入口（功能列表，新增功能在此扩展）
├── map/                # 【功能】七区小学分布地图（Leaflet）
│   ├── index.html      # 地图页，浏览器直接打开
│   └── assets/         # Leaflet 库（本地化，不依赖 CDN）
└── README.md
```

## 当前功能

| 功能 | 路径 | 说明 |
| --- | --- | --- |
| 七区小学分布地图 | `map/index.html` | 广州 7 区 619 所小学点位 + 区边界 + 图例统计，纯本地数据 |

## 约定

- 每个功能一个独立子目录（如 `map/`），后续功能（学校详情、对比、路线规划等）按同方式扩展，并在 `index.html` 入口登记
- 共享数据统一从 `../../data/primary/`（小学）或 `../../data/middle/`（初中）读取（`<script src="../../data/primary/schools.js">`），不在应用内复制数据
- 本地资源放功能自己的 `assets/` 下，用相对路径引用
- 公共 Key / token 一律放项目根 `.env`，不写入代码

## 运行

浏览器直接打开 `apps/web/index.html`（入口）或 `apps/web/map/index.html`（地图）即可，无需构建与服务。
