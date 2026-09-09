# Web 应用

广州学校升学调研的 web 端应用。

## 结构

```
apps/web/
├── index.html          # 应用入口（旧版功能列表页，Vue3 重构后下线）
├── map/                # 【功能·旧版】七区中小学分布地图（Leaflet，file:// 直接打开）
│   ├── index.html      # 地图页，引用 legacy/_generated/combined.js
│   └── assets/         # Leaflet 库（本地化，不依赖 CDN）
├── support.html        # 【功能·旧版】“支撑度”说明页（小学+初中口径）
├── legacy/             # 旧版页面专用目录
│   └── _generated/     # 浏览器兼容产物（window.GZ_* 的 .js），由 scripts/ 从 data/*.json 生成，勿手改
└── README.md
```

## 当前功能（旧版，file:// 直接打开）

| 功能 | 路径 | 说明 |
| --- | --- | --- |
| 七区中小学分布地图 | `map/index.html` | 广州 7 区小学 918 点位 + 初中 310 点位，四类配色 + 筛选 + 支撑度核验，纯本地数据 |
| 口碑学校 · 支撑度说明 | `support.html` | 小学 59 所 + 初中 53 所网传名校核验：按学段给出判定规则与信号维度 |

## 数据引用约定

- **数据真源：项目根 `data/` 下的 JSON**（`data/primary/schools-gz.json` 等）。
- 旧版页面因 file:// 直开无法 fetch，引用 `legacy/_generated/` 下的 js 兼容产物
  （如 `map/index.html` → `../legacy/_generated/combined.js`；`support.html` →
  `legacy/_generated/primary/tier1.js`）。产物由 `scripts/*.py` 从 JSON 生成，勿手改。
- 新增页面一律从 `data/*.json` 读取，不再引入 `window.GZ_*` 全局变量。

## 运行

浏览器直接打开 `apps/web/index.html`（入口）或 `apps/web/map/index.html`（地图）即可，无需构建与服务。
（Vue3 重构进行中，新工程将使用 Vite dev server 与构建产物，见根 README。）
