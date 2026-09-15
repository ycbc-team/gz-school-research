# 当前架构

本文件描述可运行代码的当前状态；`docs/小程序功能补齐与Web复用重构方案.md` 是历史迁移记录，不作为实现依据。

```
data/ (JSON 真源)
  └─ scripts/data/compact.mjs (紧凑产物，git 忽略)
       ├─ apps/web/src/data/compact/
       └─ apps/miniprogram/{data,pages/school-detail/data}/

packages/shared/
  └─ 类型、数据查询 Repository、地图/详情/升学路径领域模型

apps/web/
  └─ 路由级懒加载；Home 仅加载点位统计，地图/详情/排行按进入页面加载

apps/miniprogram/
  └─ 主包地图数据 + school-detail 分包的详情/链路数据
```

构建入口：

- `npm run check`：类型检查、共享包单元测试、数据质量检查。
- `npm run build:web`：自动构建 shared、编译紧凑数据、生成 Web 静态产物。
- `npm run build:mp`：自动构建 shared、生成小程序 shared/data/图标产物。

边界约定：`data/` 是唯一可编辑的数据真源；`packages/shared` 承载跨端业务规则；应用层只做加载、路由和平台 UI 适配。新增页面应避免从 `apps/web/src/data/index.ts` 提前引入不属于该页面的数据域。
