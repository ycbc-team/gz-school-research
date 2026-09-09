# Web 应用（Vue3 + Vite）

广州学校升学调研的 web 端应用。数据全部来自项目根 `data/*.json`（唯一真源），
逻辑复用 `@gz/shared`，构建产物 `apps/web/dist` 可部署至任意静态托管（含 GitHub Pages，hash 路由）。

## 结构

```
apps/web/
├── index.html          # 应用入口（挂载 #app）
├── src/
│   ├── main.ts         # Vue 入口
│   ├── router.ts       # hash 路由：#/（入口）/ #/map（地图）/ #/support（支撑度）
│   ├── App.vue         # 应用壳（导航）
│   ├── pages/          # HomeView / MapView / SupportView
│   ├── data/           # 数据加载层：data/*.json 真源 → 类型化模块
│   └── styles.css      # 全局样式
└── vite.config.ts      # base './'，相对路径部署
```

## 功能

| 路由 | 功能 | 说明 |
| --- | --- | --- |
| `#/` | 入口 | 功能卡片跳转 |
| `#/map` | 七区中小学·高中合并地图 | 小学 918 点 + 初中 309 点 + 高中 126 点，七类配色 + 区筛选 + 信息卡 |
| `#/support` | 口碑学校 · 支撑度核验 | 小学 59 所 + 初中 53 所网传名校：判定逻辑 + 有支撑/部分支撑明细表 |

## 运行

```bash
npm run dev:web     # Vite dev server（热更新）
npm run build:web   # 构建到 apps/web/dist
```

构建产物可直接打开 `apps/web/dist/index.html`（file:// 可用），或部署到任意静态路径。

## 数据引用约定

- 数据真源：项目根 `data/` 下 JSON（`data/primary/schools-gz.json` 等），新增页面一律从
  `src/data/` 加载层读取，禁止引入 `window.GZ_*` 全局变量。
- 旧版页面（`apps/web/map`、`support.html`、`legacy/`）及 js 兼容产物已删除，历史见 git。
