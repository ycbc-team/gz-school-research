# Web 应用（预留）

此目录预留给未来的 web 端应用。

当前已有的 web 应用见 [`../map/`](../map/)（广州七区小学分布地图，Leaflet 实现）。

新开 web 应用时的约定：

- 共享数据从 `../../data/` 读取：`<script src="../../data/schools.js"></script>`
- 共享脚本在 `../../scripts/`
- 本地资源放各自应用的 `assets/` 下，用相对路径引用
