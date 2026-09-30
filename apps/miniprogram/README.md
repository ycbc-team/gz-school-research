# 微信小程序（原生）

广州学校升学调研的微信小程序端，原生小程序（WXML/WXSS/JS），复用 `@gz/shared` 逻辑与 `data/` JSON 真源。

## 结构

```
apps/miniprogram/
├── project.config.json   # 微信开发者工具配置（appid: touristappid，可替换为你的 AppID）
├── app.json / app.js / app.wxss / sitemap.json
├── pages/
│   ├── index/            # 首页：地图首页（内置 <map>，GCJ-02 直接可用；三级筛选 + 搜索 + 学校卡）
│   └── policy/           # 使用说明 / 数据口径声明
├── utils/data.js         # 数据加载：shared cjs + data js 产物
├── shared/               # 【构建产物，git 忽略】@gz/shared 的 CommonJS 输出
└── data/                 # 【构建产物，git 忽略】data/*.json 转成的 CommonJS 模块
```

## 使用

```bash
npm run build:mp          # 生成 shared/、data/ 与首页 marker 图标（assets/markers-index/，构建产物不入库）
```

然后用微信开发者工具「导入项目」选择 `apps/miniprogram/` 目录即可预览。
`project.config.json` 中的 `appid` 为游客模式占位，发布前请替换为你的小程序 AppID。

## 数据约定

- 数据真源为项目根 `data/` 下的 JSON；`apps/miniprogram/data/` 是构建产物（由
  `scripts/miniprogram/build.mjs` 生成），不要手改。
- 共享逻辑来自 `packages/shared`（类型 + 纯函数），修改后需 `npm run build:shared` 再 `npm run build:mp`。
- 点位为 GCJ-02 坐标系，微信小程序内置 `<map>` 组件直接使用，无需转换。

## 待完善

- 地图 marker 聚类（当前为全量点位渲染）
